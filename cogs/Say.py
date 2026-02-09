import datetime
import logging

import disnake
from disnake.ext import commands
from disnake import TextInputStyle

logger = logging.getLogger(__name__)

COLOURS = {
    "Синий": disnake.Colour.blue(),
    "Блёрпл": disnake.Colour.blurple(),
    "Зелёный": disnake.Colour.green(),
    "Красный": disnake.Colour.red(),
    "Жёлтый": disnake.Colour.yellow(),
    "Оранжевый": disnake.Colour.orange(),
    "Фиолетовый": disnake.Colour.purple(),
    "Бирюзовый": disnake.Colour.teal(),
    "Фуксия": disnake.Colour.fuchsia(),
    "Золотой": disnake.Colour.gold(),

    "Фирменный зелёный": disnake.Colour.brand_green(),
    "Фирменный красный": disnake.Colour.brand_red(),
    "Серо-фиолетовый (Greyple)": disnake.Colour.greyple(),
    "Оригинальный blurple": disnake.Colour.og_blurple(),
    "Старый blurple": disnake.Colour.old_blurple(),

    "Тёмно-синий": disnake.Colour.dark_blue(),
    "Тёмно-зелёный": disnake.Colour.dark_green(),
    "Тёмно-красный": disnake.Colour.dark_red(),
    "Тёмно-пурпурный": disnake.Colour.dark_purple(),
    "Тёмно-оранжевый": disnake.Colour.dark_orange(),

    "Тёмная тема Discord": disnake.Colour.dark_theme(),
    "Тёмный embed": disnake.Colour.dark_embed(),
    "Светлый embed": disnake.Colour.light_embed(),
    "Цвет по умолчанию": disnake.Colour.default(),
}

COLOUR_NAMES = list(COLOURS.keys())

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        logger.info("Say loaded!")
    
    def cog_unload(self):
        logger.info("Say unloaded!")

    @commands.slash_command(name="say", description="Отправить сообщение от имени бота.")
    async def say(self, inter, *, content: str = commands.Param(default="", description="Текст сообщения"), 
                  title: str = commands.Param(default=None, description="Заголовок Embed"), 
                  description: str = commands.Param(default=None, description="Описание Embed. Для переноса строки используй \\n."),
                  colour: str = commands.Param(default=None, description="Цвет Embed", choices=COLOUR_NAMES),
                  image: str = commands.Param(default=None, description="Ссылка на изображение Embed"),
                  reply_to: int = commands.Param(default=None, description="Ответить на сообщение пользователя. Нужен ID сообщения.")):
        await inter.response.defer(ephemeral=True)

        embed = disnake.Embed()
        if title is not None:
            embed.title = title
        
        if description is not None:
            description = description.replace("\\n", "\n")
            embed.description = description
        
        if colour is not None:
            embed.colour = COLOURS[colour]
        
        if image is not None:
            embed.set_image(url=image)

        await inter.followup.send("Sended!")
        if title is None and description is None and image is None and reply_to is None:
            await inter.channel.send(content=content)
        elif title is None and description is None and image is None and reply_to is not None:
            message = await inter.channel.fetch_message(reply_to)
            await message.reply(content=content)
        elif reply_to is not None:
            message = await inter.channel.fetch_message(reply_to)
            await message.reply(content=content, embed=embed)
        else:
            await inter.channel.send(content=content, embed=embed)
        

def setup(bot):
    bot.add_cog(Say(bot))
