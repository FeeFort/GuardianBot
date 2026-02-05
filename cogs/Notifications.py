import datetime

import disnake
from disnake.ext import commands, tasks

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

class Notifications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        print("Notification loaded!")
        self.notification.start()

    async def cog_unload(self):
        print("Notification unloaded!")
        self.notification.cancel()

    @commands.slash_command(name="test")
    async def test(self, inter):
        await inter.response.defer()

        embed = disnake.Embed(title="🕷️ Сообщить о проблеме", description="Здесь вы можете оставить заявку, если у вас возникли технические трудности с Guardian Challenge.\n\nЕсли бот сломался, не засчитал отчет или выдал ошибку, вам необходимо нажать кнопку ниже и подробно описать проблему.\n\n⚠️ Важно: Этот канал только для багов и ошибок. Вопросы \"какую сенсу ставить\" или \"как играть\" задавайте в <#1467651392209682432>", colour=disnake.Colour.red())

        await inter.followup.send("sended!")
        await inter.channel.send(embed = embed, components=[disnake.ui.Button(label="Сообщить о проблеме",style=disnake.ButtonStyle.danger, emoji="🕷️", custom_id="report")])

    @tasks.loop(minutes=1)
    async def notification(self):
        guild = await self.bot.fetch_guild(1467650949731582220)
        channel = await guild.fetch_channel(1468553741211795537)
        role = await guild.fetch_role(1469043883282399345)

        now = datetime.datetime.now() + datetime.timedelta(hours=3)
        time_now = datetime.time(now.hour, now.minute)
        time = datetime.time(18)

        if time_now == time:
            embed = disnake.Embed(title="🕕 До конца дня осталось 6 часов!", description="Проверь, сдал ли ты ДМы сегодня.\n🔗 Сдать отчет: </отчет:1468317200740909077>\n📊 Таблица: [Нажми](https://twir.app/s/B2wK6)", colour=disnake.Colour.red())
            embed.set_footer(text="#PA1KA GUARDIAN CHALLENGE")
            
            await channel.send(content=f"📢 {role.mention}", embed=embed)


def setup(bot):
    bot.add_cog(Notifications(bot))
