import logging

from context_builder import build_system_prompt
from skill_loader import SkillLoader
from memory_store import Memory
from logging_utils import compact_json

MAX_TOOL_ROUNDS = 5
logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(self, provider, skills: SkillLoader, memory: Memory):
        self.provider = provider
        self.skills = skills
        self.memory = memory

    async def run(self, history, session_id, callbacks):
        # callback to send the final response to the user (defined in ./telegram_channel.py)
        on_token = callbacks.get("on_token")

        # callback to modify the user when a tool is being used (defined in ./telegram_channel.py)
        on_tool_use = callbacks.get("on_tool_use")

        # callback to report a final per-turn tool summary
        on_tool_summary = callbacks.get("on_tool_summary")

        # build system prompt
        system_prompt = build_system_prompt(
            self.skills.get_active_skills(), self.memory
        )

        # convert session history to API message format
        messages = [{"role": m["role"], "content": m["content"]} for m in history]

        # tool definitions from all loaded skills
        tools = self.skills.get_tools()
        logger.info(
            "Starting agent run for session '%s' with %s history messages and tools: %s",
            session_id,
            len(messages),
            ", ".join(tool["name"] for tool in tools) or "none",
        )

        response = ""
        rounds = 0
        tool_calls = []

        # ReAct loop that keeps going until LLM returns an answer or hits the limit
        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            logger.info("Agent round %s/%s for session '%s'", rounds, MAX_TOOL_ROUNDS, session_id)

            # send context to LLM and get a result
            result = await self.provider.complete(
                system_prompt=system_prompt,
                messages=messages,
                tools=tools if tools else None,
            )
            logger.info(
                "Model response for session '%s': text_chars=%s tool_calls=%s",
                session_id,
                len(result.text or ""),
                len(result.tool_calls or []),
            )

            # if the LLM wants to use tools execute them and loop back
            if result.tool_calls:
                # Add the LLM's tool request to the conversation
                messages.append(self.provider.assistant_message(result))

                # run each tool and feed results back
                for tool_call in result.tool_calls:
                    tool_calls.append(
                        {"name": tool_call["name"], "input": tool_call["input"]}
                    )
                    logger.info(
                        "Model requested tool '%s' with input: %s",
                        tool_call["name"],
                        compact_json(tool_call["input"]),
                    )
                    if on_tool_use:
                        await on_tool_use(tool_call["name"], tool_call["input"])

                    # execute the tool through the skill loader
                    tool_result = await self.skills.execute_tool(
                        tool_call["name"],
                        tool_call["input"],
                        {"session_id": session_id, "memory": self.memory},
                    )

                    # add tool result to conversation history so the LLM can see it in the next round
                    messages.append(
                        self.provider.tool_result_message(tool_call, tool_result)
                    )

                continue

            # if no tools needed send the final response to the user
            if result.text:
                if on_token:
                    await on_token(result.text)
                response = result.text

            # exit we have final non-tool response
            break
        else:
            logger.warning(
                "Agent run for session '%s' reached max tool rounds (%s)",
                session_id,
                MAX_TOOL_ROUNDS,
            )

        called_tools = [tool_call["name"] for tool_call in tool_calls]
        if called_tools:
            logger.info(
                "Tool usage summary for session '%s': called tools: %s",
                session_id,
                ", ".join(called_tools),
            )
        else:
            logger.info(
                "Tool usage summary for session '%s': no tools called",
                session_id,
            )

        if on_tool_summary:
            await on_tool_summary(tool_calls)

        logger.info(
            "Finished agent run for session '%s' with response_chars=%s",
            session_id,
            len(response),
        )
        return response
