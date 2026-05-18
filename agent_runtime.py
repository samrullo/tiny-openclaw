import json
import httpx
from context_builder import build_system_prompt
from skill_loader import SkillLoader
from memory_store import Memory

MAX_TOOL_ROUNDS = 5


class AgentRuntime:
    def __init__(self, provider, model, api_key, skills: SkillLoader, memory: Memory):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.skills = skills
        self.memory = memory

    async def run(self, history, session_id, callbacks):
        # callback to send the final response to the user (defined in ./telegram_channel.py)
        on_token = callbacks.get("on_token")

        # callback to modify the user when a tool is being used (defined in ./telegram_channel.py)
        on_tool_use = callbacks.get("on_tool_use")

        # build system prompt
        system_prompt = build_system_prompt(
            self.skills.get_active_skills(), self.memory
        )

        # convert session history to API message format
        messages = [{"role": m["role"], "content": m["content"]} for m in history]

        # tool definitions from all loaded skills
        tools = self.skills.get_tools()

        response = ""
        rounds = 0

        # ReAct loop that keeps going until LLM returns an answer or hits the limit
        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1

            # send context to LLM and get a result
            result = await self._call_anthropic(
                system_prompt=system_prompt,
                messages=messages,
                tools=tools if tools else None,
            )

            # if the LLM wants to use tools execute them and loop back
            if result["tool_calls"]:
                # Add the LLM's tool request to the conversation
                messages.append({"role": "assistant", "content": result["raw_content"]})

                # run each tool and feed results back
                for tool_call in result["tool_calls"]:
                    if on_tool_use:
                        await on_tool_use(tool_call["name"], tool_call["input"])

                        # execute the tool through the skill loader
                        tool_result = self.skills.execute_tool(
                            tool_call["name"],
                            tool_call["input"],
                            {"session_id": session_id, "memory": self.memory},
                        )

                        # add tool result to conversation history so the LLM can see it in the next round
                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_call["id"],
                                        "content": json.dumps(tool_result),
                                    }
                                ],
                            }
                        )

                        continue

            # if no tools needed send the final response to the user
            if result["text"]:
                if on_token:
                    await on_token(result["text"])
                response = result["text"]

            # exit we have final non-tool response
            break
        return response

    async def _call_anthropic(self, system_prompt, messages, tools):
        # request payload (Anthropic separates system prompt from messages)
        body = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages,
        }

        # add tool definitions for the loaded skills
        if tools:
            body["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ]

        # make async http request to Anthropic API
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json=body,
                )
        except httpx.ConnectError as e:
            raise Exception(f"Could not connect to Anthropic API : {e}")
        except httpx.TimeoutException as e:
            raise Exception(f"Anthropic API timed out : {e}")

        if res.status_code != 200:
            raise Exception(f"Anthropic API error ({res.status_code}) : {res.text}")

        data = res.json()
        text_parts = []
        tool_calls = []

        # Response can contain text blocks, tool_use blocks or both
        for block in data["content"]:
            if block["type"] == "text":
                text_parts.append(block["text"])
            elif block["type"] == "tool_use":
                tool_calls.append(
                    {"id": block["id"], "name": block["name"], "input": block["input"]}
                )

        # return normalized output
        return {
            "text": "".join(text_parts),
            "tool_calls": tool_calls or None,
            "raw_content": data["content"],
        }
