import disnake
from disnake.ext import commands

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDS_FILE = "guardianchallenge-0e281d644000.json"

creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1G6FT2CrUIGBVJaNUKOZ6Me3l7Ey2iM-0X1f7SqvPBoQ/edit?gid=1654540911#gid=1654540911")
ws = sheet.worksheet("LEADERBOARD")

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        print("Verification loaded!")

    @commands.slash_command(description="Responds with 'World'")
    async def hello(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer()
        await inter.followup.send("1111World")
        await inter.channel.send(embed=
            disnake.Embed(
                title="Добро пожаловать в Guardian Challenge! 🛡️",
                description="Чтобы получить доступ к чатам и материалам челленджа, вам необходимо пройти автоматическую верификацию.\n\n**⚠️ ВАЖНО ПЕРЕД НАЖАТИЕМ:** Пожалуйста, убедитесь, что ваш никнейм на этом сервере написан точь-в-точь так же, как вы указывали его в таблице регистрации. Бот сверяет данные автоматически — если ники будут отличаться, система вас не пропустит.\n\nКак только никнейм синхронизирован, жмите на кнопку ниже. Бот проверит наличие вашего Discord ID в базе участников.",
                color=disnake.Colour.dark_gold()
            ),
            components=[
                disnake.ui.Button(label="Пройти верификацию",style=disnake.ButtonStyle.primary, emoji="🔐", custom_id="verification"),
                disnake.ui.Button(label="Сообщить о проблеме",style=disnake.ButtonStyle.danger, emoji="🕷️", custom_id="report")
            ]
        )

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        if inter.component.custom_id == "verification":
            await inter.response.defer()
            values = ws.get("C140:С827")
            l = [inter.author.name]

            for i in values:
                values[values.index(i)] = [i[0].replace(" ", "").lower()]

            print(f"{inter.author.name} - {l in values}")
            if l in values:
                role = await inter.guild.fetch_role(1467651039695081562)
                role_ver = await inter.guild.fetch_role(1469314317471056044)
                await inter.author.remove_roles(role_ver)
                await inter.author.add_roles(role)
                await inter.followup.send(embed=disnake.Embed(
                    title="✅ Верификация пройдена",
                    description="Добро пожаловать в наш «бойцовский клуб».\n\nТы в системе. Теперь ты официально часть Guardian Challenge. Здесь мы работаем на результат, и с этого момента для тебя открыты двери в закрытые каналы.\n\nВпитывай информацию, делись прогрессом и готовься — этот месяц изменит твою игру. Твой путь начинается прямо сейчас.",
                    colour=disnake.Colour.green()
                ), ephemeral=True)
            else:
                await inter.followup.send(embed=disnake.Embed(
                    title="🚫 Ошибка верификации",
                    description="К сожалению, вы не прошли проверку. Ваш Discord ID не был найден в базе данных таблицы участников.\n\nВозможные причины:\n• Вы регистрировались с другого аккаунта Discord.\n• Ваши данные еще не внесены в таблицу (если вы зарегистрировались только что).\n• Вы не являетесь участником текущего потока.\n\nЕсли вы уверены, что это ошибка, пожалуйста, свяжитесь с администрацией.",
                    colour=disnake.Colour.red()
                ), ephemeral=True)


def setup(bot):
    bot.add_cog(Verification(bot))
