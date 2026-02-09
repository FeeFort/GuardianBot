import os
import logging
from rich.logging import RichHandler
from dotenv import load_dotenv

import disnake
from disnake.ext import commands, tasks
from colorlog import ColoredFormatter

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[RichHandler(rich_tracebacks=True, markup=True, show_time=True)]
)

bot = commands.InteractionBot(intents=disnake.Intents.all())

@bot.event
async def on_ready():
    print("im ready")

@bot.slash_command(name="load", description="Загружает модуль.")
async def load(inter, cog: str):
    await inter.response.defer()

    try:
        bot.load_extension(f"cogs.{cog}")
        await inter.followup.send(f"✅ Модуль `{cog}` успешно загружен!")
    except Exception as e:
        print(e)
        await inter.followup.send(f"❌ При загрузке модуля `{cog}` произошла ошибка!")

@bot.slash_command(name="reload", description="Перезагружает модуль.")
async def load(inter, cog: str):
    await inter.response.defer()

    try:
        bot.unload_extension(f"cogs.{cog}")
        bot.load_extension(f"cogs.{cog}")
        await inter.followup.send(f"✅ Модуль `{cog}` успешно перезагружен!")
    except:
        await inter.followup.send(f"❌ При перезагрузке модуля `{cog}` произошла ошибка!")

@bot.slash_command(name="unload", description="Отгружает модуль.")
async def load(inter, cog: str):
    await inter.response.defer()

    try:
        bot.unload_extension(f"cogs.{cog}")
        await inter.followup.send(f"✅ Модуль `{cog}` успешно отгружен!")
    except:
        await inter.followup.send(f"❌ При отгрузке модуля `{cog}` произошла ошибка!")

    
for i in os.listdir("./cogs"):
    if i.endswith(".py") and not i.startswith("_"):
        bot.load_extension(f"cogs.{i[:-3]}")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

bot.run(TOKEN)