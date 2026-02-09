import datetime
import logging

import disnake
from disnake.ext import commands
from disnake import TextInputStyle

logger = logging.getLogger(__name__)

COLOURS = {
    "Синий": disnake.Colour.blue(),
    "Блёрпл (Discord-синий)": disnake.Colour.blurple(),
    "Фирменный зелёный": disnake.Colour.brand_green(),
    "Фирменный красный": disnake.Colour.brand_red(),

    "Тёмно-синий": disnake.Colour.dark_blue(),
    "Тёмный embed": disnake.Colour.dark_embed(),
    "Тёмно-золотой": disnake.Colour.dark_gold(),
    "Тёмно-серый": disnake.Colour.dark_gray(),
    "Тёмно-зелёный": disnake.Colour.dark_green(),
    "Тёмно-серый (grey)": disnake.Colour.dark_grey(),
    "Тёмно-пурпурный": disnake.Colour.dark_magenta(),
    "Тёмно-оранжевый": disnake.Colour.dark_orange(),
    "Тёмно-фиолетовый": disnake.Colour.dark_purple(),
    "Тёмно-красный": disnake.Colour.dark_red(),
    "Тёмно-бирюзовый": disnake.Colour.dark_teal(),
    "Тёмная тема Discord": disnake.Colour.dark_theme(),

    "Очень тёмно-серый": disnake.Colour.darker_gray(),
    "Очень тёмно-серый (grey)": disnake.Colour.darker_grey(),
    "Цвет по умолчанию": disnake.Colour.default(),

    "Фуксия": disnake.Colour.fuchsia(),
    "Золотой": disnake.Colour.gold(),
    "Зелёный": disnake.Colour.green(),
    "Серо-фиолетовый (Greyple)": disnake.Colour.greyple(),

    "Светлый embed": disnake.Colour.light_embed(),
    "Светло-серый": disnake.Colour.light_gray(),
    "Светло-серый (grey)": disnake.Colour.light_grey(),
    "Очень светло-серый": disnake.Colour.lighter_gray(),
    "Очень светло-серый (grey)": disnake.Colour.lighter_grey(),

    "Пурпурный": disnake.Colour.magenta(),
    "Оригинальный blurple": disnake.Colour.og_blurple(),
    "Старый blurple": disnake.Colour.old_blurple(),

    "Оранжевый": disnake.Colour.orange(),
    "Фиолетовый": disnake.Colour.purple(),
    "Красный": disnake.Colour.red(),
    "Бирюзовый": disnake.Colour.teal(),
    "Жёлтый": disnake.Colour.yellow(),
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
                  description: str = commands.Param(default=None, description="Описание Embed. Для переноса строки используй \\n"),
                  colour: str = commands.Param(default=None, description="Цвет Embed", choices=COLOUR_NAMES),
                  image: str = commands.Param(default=None, description="Ссылка на изображение Embed")):
        await inter.response.defer()

        embed = disnake.Embed()
        if title is not None:
            embed.title = title
        
        if description is not None:
            embed.description = description
        
        if colour is not None:
            embed.colour = colour
        
        if image is not None:
            embed.set_image(url=image)

        await inter.followup.send("Sended!")
        if title is None and description is None and image is None:
            await inter.channel.send(content=content)
        else:
            await inter.channel.send(content=content, embed=embed)

    @commands.slash_command(name="test1111")
    async def test(self, inter):
        await inter.response.defer()
        await inter.followup.send("pashel nahuy")
        

def setup(bot):
    bot.add_cog(Say(bot))
