import json
import os
from dataclasses import dataclass

import httpx
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, OpenAIError


@dataclass
class ModelResponse:
    text: str
    tool_calls: list
    raw_content: object


class ModelProvider:
    @property
    def display_name(self):
        raise NotImplementedError

    async def complete(self, system_prompt, messages, tools=None):
        raise NotImplementedError

    def assistant_message(self, response):
        raise NotImplementedError

    def tool_result_message(self, tool_call, tool_result):
        raise NotImplementedError


class AnthropicProvider(ModelProvider):
    def __init__(self, model, api_key, base_url="https://api.anthropic.com/v1"):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def display_name(self):
        return f"Anthropic / {self.model}"

    async def complete(self, system_prompt, messages, tools=None):
        body = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages,
        }

        if tools:
            body["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["parameters"],
                }
                for tool in tools
            ]

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                res = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json=body,
                )
        except httpx.ConnectError as e:
            raise Exception(f"Could not connect to Anthropic API: {e}")
        except httpx.TimeoutException as e:
            raise Exception(f"Anthropic API timed out: {e}")

        if res.status_code != 200:
            raise Exception(f"Anthropic API error ({res.status_code}): {res.text}")

        data = res.json()
        text_parts = []
        tool_calls = []

        for block in data["content"]:
            if block["type"] == "text":
                text_parts.append(block["text"])
            elif block["type"] == "tool_use":
                tool_calls.append(
                    {"id": block["id"], "name": block["name"], "input": block["input"]}
                )

        return ModelResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            raw_content=data["content"],
        )

    def assistant_message(self, response):
        return {"role": "assistant", "content": response.raw_content}

    def tool_result_message(self, tool_call, tool_result):
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call["id"],
                    "content": json.dumps(tool_result),
                }
            ],
        }


class LMStudioProvider(ModelProvider):
    def __init__(self, model, base_url="http://localhost:1234/v1", api_key=None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "not-needed"
        self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    @property
    def display_name(self):
        return f"LM Studio / {self.model} ({self.base_url})"

    async def complete(self, system_prompt, messages, tools=None):
        request = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "temperature": 0.7,
        }

        if tools:
            request["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["parameters"],
                    },
                }
                for tool in tools
            ]
            request["tool_choice"] = "auto"

        try:
            completion = await self.client.chat.completions.create(**request)
        except APIConnectionError as e:
            raise Exception(f"Could not connect to LM Studio API: {e}")
        except APITimeoutError as e:
            raise Exception(f"LM Studio API timed out: {e}")
        except OpenAIError as e:
            raise Exception(f"LM Studio API error: {e}")

        message = completion.choices[0].message
        tool_calls = []

        for call in message.tool_calls or []:
            arguments = call.function.arguments or "{}"
            if isinstance(arguments, dict):
                tool_input = arguments
            else:
                try:
                    tool_input = json.loads(arguments)
                except json.JSONDecodeError:
                    tool_input = {"raw_arguments": arguments}

            tool_calls.append(
                {
                    "id": call.id,
                    "name": call.function.name,
                    "input": tool_input,
                }
            )

        return ModelResponse(
            text=message.content or "",
            tool_calls=tool_calls,
            raw_content=message,
        )

    def assistant_message(self, response):
        message = response.raw_content.model_dump(exclude_none=True)
        if message.get("content") is None:
            message["content"] = ""
        return message

    def tool_result_message(self, tool_call, tool_result):
        return {
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": json.dumps(tool_result),
        }


def create_provider_from_env():
    provider = (os.getenv("MODEL_PROVIDER") or "anthropic").lower()
    model = os.getenv("MODEL_NAME")

    if provider == "anthropic":
        if not model:
            raise ValueError("MODEL_NAME is required for Anthropic")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic")
        return AnthropicProvider(model=model, api_key=api_key)

    if provider in {"lmstudio", "lm_studio", "local"}:
        if not model:
            raise ValueError("MODEL_NAME is required for LM Studio")
        return LMStudioProvider(
            model=model,
            base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
            api_key=os.getenv("LMSTUDIO_API_KEY"),
        )

    raise ValueError(
        "MODEL_PROVIDER must be 'anthropic' or 'lmstudio' "
        f"(got {provider!r})"
    )
