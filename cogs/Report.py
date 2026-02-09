import datetime
import logging

import disnake
from disnake.ext import commands
from disnake import TextInputStyle

logger = logging.getLogger(__name__)

# Subclassing the modal.
class MyModal(disnake.ui.Modal):
    def __init__(self):
        # The details of the modal, and its components
        components = [
            disnake.ui.TextInput(
                label="Проблема:",
                placeholder="Опишите проблему подробнее...",
                custom_id="description",
                style=TextInputStyle.paragraph,
            ),
        ]
        super().__init__(title="Сообщить о проблеме", components=components)

    # The callback received when the user input is completed.
    async def callback(self, inter: disnake.ModalInteraction):
        embed = disnake.Embed(title="🕷️ Новый репорт", description=f"Автор репорта: {inter.author.mention}\nОписание:\n\n", colour=disnake.Colour.red())
        for key, value in inter.text_values.items():
            embed.description += value
    
        await inter.response.send_message("✅ Репорт отправлен!", ephemeral=True)
        channel = await inter.guild.fetch_channel(1468311758816153726)
        await channel.send(embed=embed, components=[
            disnake.ui.Button(label="Закрыть репорт",style=disnake.ButtonStyle.secondary, emoji="✅", custom_id="success_report"),
            disnake.ui.Button(label="Отклонить репорт",style=disnake.ButtonStyle.secondary, emoji="🚫", custom_id="cancel_report")
        ])

class Report(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        logger.info("Report loaded!")
    
    def cog_unload(self):
        logger.info("Report unloaded!")

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        if inter.component.custom_id == "report":
            await inter.response.send_modal(modal=MyModal())
        elif inter.component.custom_id == "success_report":
            unix_dt = int(datetime.datetime.now().timestamp())

            embed = inter.message.embeds[0]
            embed.description += f"\n\nРепорт закрыт <t:{unix_dt}:f> пользователем {inter.author.mention}"
            await inter.response.edit_message(embed=embed, view=None)
        elif inter.component.custom_id == "cancel_report":
            unix_dt = int(datetime.datetime.now().timestamp())

            embed = inter.message.embeds[0]
            embed.description += f"\n\nРепорт отклонен <t:{unix_dt}:f> пользователем {inter.author.mention}"
            await inter.response.edit_message(embed=embed, view=None)


def setup(bot):
    bot.add_cog(Report(bot))
