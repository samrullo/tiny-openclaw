import logging
import time
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

# Translates between Telegram BOT API and Tiny OpenClaw
logger = logging.getLogger(__name__)

class TelegramChannel:
    def __init__(self, token, agent, sessions):
        self.token = token # Telegram bot token from BotFather
        self.agent = agent # Agentruntime instance
        self.sessions = sessions # SessionManager instance
    
    # start polling Telegram for new messages
    async def start(self):
        # build the Telegram bot app using bot token
        app = Application.builder().token(self.token).build()

        # listen for messages and route them to _on_message
        app.add_handler(MessageHandler(filters.TEXT, self._on_message))

        # initialize the bot and start checking new messages
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram polling started")

        # keep the bot running forever
        await asyncio.Future()
    
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
            
            # run the ReAct loop
            await self.agent.run(history, session_id, {"on_token":on_token,"on_tool_use":on_tool_use})

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
