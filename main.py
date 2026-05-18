import asyncio
import logging
import os
from dotenv import load_dotenv

from memory_store import Memory
from session_manager import SessionManager
from skill_loader import SkillLoader
from agent_runtime import AgentRuntime
from model_providers import create_provider_from_env
from telegram_channel import TelegramChannel

load_dotenv()

def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

async def main():
    configure_logging()
    logger = logging.getLogger(__name__)
    print("Tiny OpenClaw starting up...")
    logger.info("Tiny OpenClaw starting up")

    # create the memory store
    memory = Memory()

    # create the session manager
    sessions = SessionManager()

    # load all skills
    skills = SkillLoader()
    skills.load_from_directory(os.path.join(os.path.dirname(__file__),"skills"))

    # create the configured model provider and agent runtime
    provider = create_provider_from_env()
    print(f"Using model: {provider.display_name}")
    logger.info("Using model: %s", provider.display_name)

    agent = AgentRuntime(provider=provider,
                         skills=skills,
                         memory=memory)
    
    # create the Telegram channel and connect it to the LLM agent and sessions
    telegram = TelegramChannel(token = os.getenv("TELEGRAM_BOT_TOKEN"),
                               agent=agent,
                               sessions=sessions)
    print("\nTiny OpenClaw is running on Telegram")
    print("\nGo Claw!!🦞")

    # start the telegram bot
    await telegram.start()

if __name__ == "__main__":
    asyncio.run(main())
