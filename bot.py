import os
import sys
import logging

import disnake
from disnake.ext import commands, tasks
from colorlog import ColoredFormatter
from dotenv import load_dotenv

load_dotenv()

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)s] %(name)s:%(reset)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
)

logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
logger = logging.getLogger(__name__)

bot = commands.InteractionBot(intents=disnake.Intents.all())

@bot.event
async def on_ready():
    logger.info("im ready")

@bot.slash_command(name="load", description="Загружает модуль.")
async def load(inter, cog: str):
    await inter.response.defer()

    try:
        bot.load_extension(f"cogs.{cog}")
        await inter.followup.send(f"✅ Модуль `{cog}` успешно загружен!")
    except Exception as e:
        logger.error(e)
        await inter.followup.send(f"❌ При загрузке модуля `{cog}` произошла ошибка!")

@bot.slash_command(name="reload", description="Перезагружает модуль.")
async def load(inter, cog: str):
    await inter.response.defer()

    try:
        bot.unload_extension(f"cogs.{cog}")
        bot.load_extension(f"cogs.{cog}")
        await inter.followup.send(f"✅ Модуль `{cog}` успешно перезагружен!")
    except Exception as e:
        logger.error(e)
        await inter.followup.send(f"❌ При перезагрузке модуля `{cog}` произошла ошибка!")

@bot.slash_command(name="unload", description="Отгружает модуль.")
async def load(inter, cog: str):
    await inter.response.defer()

    try:
        bot.unload_extension(f"cogs.{cog}")
        await inter.followup.send(f"✅ Модуль `{cog}` успешно отгружен!")
    except Exception as e:
        logger.error(e)
        await inter.followup.send(f"❌ При отгрузке модуля `{cog}` произошла ошибка!")

    
for i in os.listdir("./cogs"):
    if i.endswith(".py") and not i.startswith("_"):
        bot.load_extension(f"cogs.{i[:-3]}")

TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)