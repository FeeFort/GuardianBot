import disnake
from disnake.ext import commands
from disnake import TextInputStyle

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
        embed = disnake.Embed(title="🕷️ Новый репорт", colour=disnake.Colour.red())
        embed.set_author(name=f"{inter.author.nick} ({inter.author.name})", icon_url=inter.author.avatar)
        for key, value in inter.text_values.items():
            embed.description = value
    
        await inter.response.send_message("✅ Репорт отправлен!", ephemeral=True)
        channel = await inter.guild.fetch_channel(1468311758816153726)
        await channel.send(embed=embed)

class Report(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        print("Report loaded!")

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        if inter.component.custom_id == "report":
            await inter.response.send_modal(modal=MyModal())


def setup(bot):
    bot.add_cog(Report(bot))
