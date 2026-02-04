import os

import disnake
from disnake.ext import commands, tasks

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

bot.run("MTQ2ODI1MDcwNjU5NDIzODY0Mw.GHKcSQ.s31YVN5kUSrpT7Rj9hbpF63dbfqCPXYBYn9LZA")