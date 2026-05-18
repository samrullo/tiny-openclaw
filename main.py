import asyncio
import os
from dotenv import load_dotenv

from memory_store import Memory
from session_manager import SessionManager
from skill_loader import SkillLoader
from agent_runtime import AgentRuntime
from telegram_channel import TelegramChannel

load_dotenv()

async def main():
    print("Tiny OpenClaw starting up...")

    # create the memory store
    memory = Memory()

    # create the session manager
    sessions = SessionManager()

    # load all skills
    skills = SkillLoader()
    skills.load_from_directory(os.path.join(os.path.dirname(__file__),"skills"))

    # create the agent runtime
    agent = AgentRuntime(provider=os.getenv("MODEL_PROVIDER"),
                         model = os.getenv("MODEL_NAME"), 
                         api_key=os.getenv("ANTHROPIC_API_KEY"),
                         skills=SkillLoader(),
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