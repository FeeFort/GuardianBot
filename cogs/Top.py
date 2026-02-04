import datetime
from datetime import timezone

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

async def get_participants_and_day(ws, day_header: str, header_row: int = 1):
    headers = ws.row_values(1)

    if day_header not in headers:
        raise ValueError("Столбец с таким днём не найден")

    day_col = headers.index(day_header) + 1

    participants = ws.col_values(3)[1:]
    day_values   = ws.col_values(day_col)[1:]

    n = min(len(participants), len(day_values))

    result = []
    for i in range(n):
        name = participants[i].strip()
        raw = day_values[i].strip()

        if not name:
            continue

        games = int(raw) if raw.isdigit() else 0
        result.append((name, games))

    return result

class Top(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_date = datetime.date(2026, 2, 5)

    async def cog_load(self):
        print("Top loaded!")
        self.update_top.start()
        self.update_daily_top.start()

    async def cog_unload(self):
        print("Top unloaded!")
        self.update_top.cancel()
        self.update_daily_top.cancel()

    @commands.slash_command(name="send_top", description="Send top.")
    async def send_top(self, inter):
        await inter.response.defer()

        members = ws.get("C2:AG138")
        summ = 0
        results = {}
        embed = disnake.Embed(title="🏆 Топ участников по кол-ву ДМов.", description="", colour=disnake.Colour.dark_gold())

        for member in members:
            for i in member:
                try:
                    summ += int(i)
                except:
                    continue

            results[member[0].replace(" ", "").lower()] = summ

            summ = 0

        top10 = sorted(
            results.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        for place, (key, value) in enumerate(top10, start=1):
            member = inter.guild.get_member_named(key)
            if place == 1:
                embed.description += f"🥇 {place}. {member.mention} - {value} сыгранных ДМов.\n\n"
            elif place == 2:
                embed.description += f"🥈 {place}. {member.mention} - {value} сыгранных ДМов.\n\n"
            elif place == 3:
                embed.description += f"🥉 {place}. {member.mention} - {value} сыгранных ДМов.\n\n"
            else:
                embed.description += f"{place}. {member.mention} - {value} сыгранных ДМов.\n\n"

        await inter.followup.send("sended!")
        await inter.channel.send(embed=embed)

    @tasks.loop(minutes=3)
    async def update_top(self):
        guild = await self.bot.fetch_guild(1467650949731582220)
        channel = await guild.fetch_channel(1468554041368907904)
        msg = await channel.fetch_message(1468632737459077317)

        members = ws.get("C2:AG138")
        summ = 0
        results = {}
        embed = disnake.Embed(title="🏆 Топ участников по кол-ву ДМов.", description="", colour=disnake.Colour.dark_gold())

        for member in members:
            for i in member:
                try:
                    summ += int(i)
                except:
                    continue

            results[member[0].replace(" ", "").lower()] = summ

            summ = 0

        top10 = sorted(
            results.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        for place, (key, value) in enumerate(top10, start=1):
            async for m in guild.fetch_members(limit=None):
                if m.name == key or m.display_name == key:
                    member = m
                    break
                else:
                    member = None

            if place == 1:
                embed.description += f"🥇 {member.mention} - {value} сыгранных ДМов.\n\n"
                ws.update(f"AH{place+1}", [[f"🥇 {member} - {value} сыгранных ДМов."]], value_input_option="USER_ENTERED")
            elif place == 2:
                embed.description += f"🥈 {member.mention} - {value} сыгранных ДМов.\n\n"
                ws.update(f"AH{place+1}", [[f"🥈 {member} - {value} сыгранных ДМов."]], value_input_option="USER_ENTERED")
            elif place == 3:
                embed.description += f"🥉 {member.mention} - {value} сыгранных ДМов.\n\n"
                ws.update(f"AH{place+1}", [[f"🥉 {member} - {value} сыгранных ДМов."]], value_input_option="USER_ENTERED")
            else:
                embed.description += f"{place}. {member.mention} - {value} сыгранных ДМов.\n"
                ws.update(f"AH{place+1}", [[f"{place}. {member} - {value} сыгранных ДМов."]], value_input_option="USER_ENTERED")

        dt = datetime.datetime.now()
        dt_next = datetime.datetime.now() + datetime.timedelta(minutes=3)
        unix_ts = int(dt.timestamp())
        unix_ts_next = int(dt_next.timestamp())
        embed.description += (f"\n⏱️ Обновлено: <t:{unix_ts}:f>\n📅 Следующее обновление: <t:{unix_ts_next}:f>")

        await msg.edit(embed=embed)

    @tasks.loop(minutes=1)
    async def update_daily_top(self):
        guild = await self.bot.fetch_guild(1467650949731582220)
        channel = await guild.fetch_channel(1468554176194936863)
        now = datetime.datetime.now() + datetime.timedelta(hours=3)
        now_date = datetime.date(now.year, now.month, now.day)

        if now_date == self.update_date:
            results = {}
            date = datetime.datetime.strftime(datetime.datetime.now(), "%d.%m.")
            members = await get_participants_and_day(ws, date)
            dt = datetime.datetime.now()
            unix_ts = int(dt.timestamp())
            embed = disnake.Embed(title="🏆 Топ участников по кол-ву ДМов за день.", description=f"День: <t:{unix_ts}:D>\n\n", colour=disnake.Colour.dark_gold())

            for member in members:
                results[member[0].replace(" ", "").lower()] = member[1]
            
            top10 = sorted(
                results.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            print(f"TOP 10: {top10}")

            for place, (key, value) in enumerate(top10, start=1):
                async for m in guild.fetch_members(limit=None):
                    if m.name == key or m.display_name == key:
                        member = m
                        break
                    else:
                        member = guild.get_member_named(key)

                if place == 1:
                    embed.description += f"🥇 {member.mention} - {value} сыгранных ДМов.\n\n"
                elif place == 2:
                    embed.description += f"🥈 {member.mention} - {value} сыгранных ДМов.\n\n"
                elif place == 3:
                    embed.description += f"🥉 {member.mention} - {value} сыгранных ДМов.\n\n"
                else:
                    embed.description += f"{place}. {member.mention} - {value} сыгранных ДМов.\n"
                    

            await channel.send(embed=embed)
            
            self.update_date = datetime.date(now.year, now.month, now.day)
            print(f"UPDATE DATE: {self.update_date}")

def setup(bot):
    bot.add_cog(Top(bot))
