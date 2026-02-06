import datetime
from urllib.parse import urlparse

import disnake
from disnake.ext import commands

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDS_FILE = "guardianchallenge-0e281d644000.json"

creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1G6FT2CrUIGBVJaNUKOZ6Me3l7Ey2iM-0X1f7SqvPBoQ/edit?gid=1654540911#gid=1654540911")
ws = sheet.worksheet("LEADERBOARD")

service = build("sheets", "v4", credentials=creds)

spreadsheet_id = sheet.id
sheet_id = ws.id

def findCell(ws, key_value, key_col, target_col_name):
    col_values = ws.col_values(key_col)
    if key_value not in col_values:
        return None

    row = col_values.index(key_value) + 1

    headers = ws.row_values(1)
    if target_col_name not in headers:
        return None

    col = headers.index(target_col_name) + 1
    return ws.cell(row, col)

class Submit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        print("Submit loaded!")

    @commands.slash_command(name="отчет", description="Отправить отчет о тренировке.")
    async def submit(self, inter, count: int = commands.Param(description="Кол-во сыгранных ДМов"),
                     screenshot: str = commands.Param(description="Ссылка на скриншот. Залей скрин на imgur/yapx и вставь ссылку сюда.")):
        await inter.response.defer(ephemeral=True)

        if count < 10 or count > 60:
            await inter.followup.send("🚫 Число ДМов не может быть меньше 10 или больше 60!")
            return

        try:
            result = urlparse(screenshot)
            if all([result.scheme, result.netloc]):
                if screenshot.startswith("https://yapx.ru/album/") or screenshot.startswith("https://imgur.com/a/") or screenshot.startswith("https://www.imgur.la/image/") or screenshot.startswith("https://yapx.ru/image/"):
                    role = await inter.guild.fetch_role(1469043883282399345)
                    
                    date = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(hours=3), "%d.%m.")
                    key_value = inter.author.name
                    key_cell = ws.find(key_value)
                    row = key_cell.row

                    column_header = date
                    header_cell = ws.find(column_header)
                    col = header_cell.col

                    a1 = gspread.utils.rowcol_to_a1(row, col)
                    range_a1 = f"{ws.title}!{a1}"

                    resp = service.spreadsheets().values().get(
                        spreadsheetId=spreadsheet_id,
                        range=range_a1
                    ).execute()

                    values = resp.get("values", [])
                    has_value = bool(values) and bool(values[0]) and str(values[0][0]).strip() != ""
                    
                    if not has_value:
                        requests = [{
                            "updateCells": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": row - 1,
                                    "endRowIndex": row,
                                    "startColumnIndex": col - 1,
                                    "endColumnIndex": col
                                },
                                "rows": [{
                                    "values": [{
                                        "userEnteredValue": {"numberValue": count},
                                        "userEnteredFormat": {
                                            "textFormat": {
                                                "link": {"uri": screenshot}
                                            }
                                        }
                                    }]
                                }],
                                "fields": "userEnteredValue,userEnteredFormat.textFormat.link"
                            }
                        }]

                        service.spreadsheets().batchUpdate(
                            spreadsheetId=spreadsheet_id,
                            body={"requests": requests}
                        ).execute()

                        await inter.followup.send("✅ Твой отчет принят! +Respect")

                        if role in inter.author.roles:
                            await inter.author.remove_roles(role)

                        channel = await inter.guild.fetch_channel(1468632013807419425)
                        embed = disnake.Embed(title="Guardian Grind #PA1KA", description=f"10 ДМов закрыто. +Respect.\n\n**[Пруф]({screenshot})**\n", colour=disnake.Colour.dark_gold())
                        await channel.send(content=f"🎯 {inter.author.mention} сдал отчет!", embed = embed)
                    else:
                        await inter.followup.send("🚫 Ты не можешь отправлять больше одного отчета в день!")
                else:
                    await inter.followup.send("🚫 Указана неправильная ссылка на скриншот!")
            else:
                await inter.followup.send("🚫 Ссылка на скриншот указана в неправильном формате!")
        except Exception as e:
            channel = await inter.guild.fetch_channel(1468311758816153726)
            embed = disnake.Embed(title="🚫 Возникла непредвиденная ошибка!", description=f"```{e}```\n\nАвтор: {inter.author.mention}")

            await inter.followup.send(f"🚫 Возникла непредвиденная ошибка!")
            await channel.send(embed = embed)

        
        

def setup(bot):
    bot.add_cog(Submit(bot))
