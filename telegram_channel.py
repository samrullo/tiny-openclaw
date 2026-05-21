import logging
import time
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from logging_utils import compact_json

# Translates between Telegram BOT API and Tiny OpenClaw
logger = logging.getLogger(__name__)
TOOL_USAGE_SETTING = "show_tool_usage"

class TelegramChannel:
    def __init__(self, token, agent, sessions):
        self.token = token # Telegram bot token from BotFather
        self.agent = agent # Agentruntime instance
        self.sessions = sessions # SessionManager instance
    
    # start polling Telegram for new messages
    async def start(self):
        # build the Telegram bot app using bot token
        app = Application.builder().token(self.token).build()

        # listen for session reset commands before routing normal text to the LLM
        app.add_handler(CommandHandler(["reset", "reset_session", "wipe_session"], self._reset_session))
        app.add_handler(
            CommandHandler(["tool_usage_on", "tools_on"], self._enable_tool_usage)
        )
        app.add_handler(
            CommandHandler(["tool_usage_off", "tools_off"], self._disable_tool_usage)
        )
        app.add_handler(
            CommandHandler(["tool_usage_status", "tools_status"], self._tool_usage_status)
        )

        # listen for messages and route them to _on_message
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))

        # initialize the bot and start checking new messages
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram polling started")

        # keep the bot running forever
        await asyncio.Future()

    # called when a user asks to clear their Telegram session history
    async def _reset_session(self, update: Update, context):
        chat_id = str(update.effective_chat.id)
        session_id = self.sessions.get_or_create_session(chat_id, "telegram")

        cleared = self.sessions.clear_history(session_id)
        if cleared:
            logger.info("Cleared Telegram session history for session '%s'", session_id)
            await update.message.reply_text(
                "Session reset. I will not include the previous chat history in future replies."
            )
        else:
            logger.warning("Could not clear missing Telegram session '%s'", session_id)
            await update.message.reply_text("No existing session history was found.")

    async def _enable_tool_usage(self, update: Update, context):
        session_id = self._session_id_for_update(update)
        self.sessions.set_setting(session_id, TOOL_USAGE_SETTING, True)
        logger.info("Enabled Telegram tool usage summary for session '%s'", session_id)
        await update.message.reply_text("Tool usage summaries are on.")

    async def _disable_tool_usage(self, update: Update, context):
        session_id = self._session_id_for_update(update)
        self.sessions.set_setting(session_id, TOOL_USAGE_SETTING, False)
        logger.info("Disabled Telegram tool usage summary for session '%s'", session_id)
        await update.message.reply_text("Tool usage summaries are off.")

    async def _tool_usage_status(self, update: Update, context):
        session_id = self._session_id_for_update(update)
        enabled = self._is_tool_usage_enabled(session_id)
        state = "on" if enabled else "off"
        await update.message.reply_text(f"Tool usage summaries are {state}.")

    def _session_id_for_update(self, update: Update):
        chat_id = str(update.effective_chat.id)
        return self.sessions.get_or_create_session(chat_id, "telegram")

    def _is_tool_usage_enabled(self, session_id):
        return self.sessions.get_setting(session_id, TOOL_USAGE_SETTING, True)

    def _format_tool_usage_summary(self, tool_calls):
        if not tool_calls:
            return "Tool usage : 0, Tools used : none"

        tool_names = [tool_call["name"] for tool_call in tool_calls]
        lines = [
            f"Tool usage : {len(tool_calls)}, Tools used : {', '.join(tool_names)}",
            "Parameters:",
        ]
        for index, tool_call in enumerate(tool_calls, start=1):
            params = compact_json(tool_call["input"], max_chars=700)
            lines.append(f"{index}. {tool_call['name']} : {params}")

        return "\n".join(lines)
    
    # called every time a user sends a message to the bot
    async def _on_message(self, update:Update, context):
        # get the sender's unique chat_id
        chat_id = str(update.effective_chat.id)

        # get the text the user sent
        user_text = update.message.text

        # ignore empty messages
        if not user_text:
            return 
        
        # get or create one session per Telegram chat using chat_id as the user identifier
        session_id = self.sessions.get_or_create_session(chat_id, "telegram")
        logger.info(
            "Received Telegram message for session '%s' chars=%s",
            session_id,
            len(user_text),
        )

        # save the user message to session history
        self.sessions.add_message(session_id, {"role":"user","content":user_text, "timestamp":time.time()})

        # show "typing..." indicator in Telegram chat
        await update.effective_chat.send_action("typing")

        try:
            # Get full conversation history for this user
            history = self.sessions.get_history(session_id)

            full_response = ""

            # callback that the LLM calls for each word it generates
            async def on_token(token):
                nonlocal full_response
                full_response += token
            
            # Refresh typing indicator when the agent uses a tool
            async def on_tool_use(name, input):
                logger.info("Telegram session '%s' is using tool '%s'", session_id, name)
                await update.effective_chat.send_action("typing")

            # Log a clear per-turn summary after the agent finishes
            async def on_tool_summary(tool_calls):
                tool_names = [tool_call["name"] for tool_call in tool_calls]
                if tool_names:
                    logger.info(
                        "Telegram session '%s' tool summary: called tools: %s",
                        session_id,
                        ", ".join(tool_names),
                    )
                else:
                    logger.info(
                        "Telegram session '%s' tool summary: no tools called",
                        session_id,
                    )

                if self._is_tool_usage_enabled(session_id):
                    await update.message.reply_text(
                        self._format_tool_usage_summary(tool_calls)
                    )
            
            # run the ReAct loop
            await self.agent.run(
                history,
                session_id,
                {
                    "on_token": on_token,
                    "on_tool_use": on_tool_use,
                    "on_tool_summary": on_tool_summary,
                },
            )

            # Send reply back to Telegram (split over 4096 chars due to Telegram's limit)
            if full_response:
                for i in range(0, len(full_response), 4096):
                    await update.message.reply_text(full_response[i:i+4096])
                logger.info(
                    "Sent Telegram response for session '%s' chars=%s",
                    session_id,
                    len(full_response),
                )
                
                # save LLM response to session history
                self.sessions.add_message(session_id, {"role":"assistant","content":full_response,"timestamp":time.time()})
        # send error message if something goes wrong
        except Exception as e:
            logger.exception("Error while handling Telegram session '%s': %s", session_id, e)
            await update.message.reply_text(f"Error : {e}")
