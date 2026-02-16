import os
import json
import datetime
import logging
import requests
import traceback
from urllib.parse import urlparse

import disnake
from disnake.ext import commands

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import OCR

logger = logging.getLogger(__name__)

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

class Submit2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        logger.info("Submit2.0 loaded!")

    def cog_unload(self):
        logger.info("Submit2.0 unloaded!")

    @commands.slash_command(name="отчет2-0", description="Отправить отчет о тренировке.")
    async def submit(self, inter, screenshot: str = commands.Param(description="Ссылка на скриншот. Залей скрин на voicechat.site и вставь ссылку сюда.")):
        await inter.response.defer(ephemeral=True)

        try:
            result = urlparse(screenshot)
            if all([result.scheme, result.netloc]):
                if screenshot.startswith("https://voicechat.site/image"):
                    if inter.guild is None:
                        await inter.followup.send("Команда /отчет не работает в ЛС бота. Пропиши команду в <#1467651392209682432>", ephemeral=True)
                        return

                    role = await inter.guild.fetch_role(1469043883282399345)
                    chuspan = await inter.guild.fetch_role(1471254421500334151)
                    message = await inter.original_message()

                    req = requests.post(screenshot)
                    url = req.json()["rawUrl"]

                    DEBUG_DIR = "debug_out"
                    os.makedirs(DEBUG_DIR, exist_ok=True)
                    res = OCR.process_one(path=None, url=url, debug_dir=DEBUG_DIR)
                    d = json.loads(json.dumps(res, ensure_ascii=False, indent=2))
                    month = d["ocr"]["best"]["month"]
                    day = d["ocr"]["best"]["day"]
                    matches = d["ocr"]["best"]["badge"]
                    try:
                        date = datetime.datetime.strptime(f"{month} {day} 2026", "%b %d %Y")
                        now = datetime.datetime.now()

                        if date.date() >= datetime.date(now.year, now.month, now.day + 2):
                            await inter.author.add_roles(chuspan)
                            await inter.followup.send("Ты решил переписать будущее в браузере.\nПоменял цифры и почувствовал контроль.\nНо контроль не у тебя.\nТы просто показал, что готов ломать декорации.\nРоль выдана.\nБез обсуждений.")
                            return
                        elif date.date() < datetime.date(now.year, now.month, now.day - 1):
                            await inter.followup.send("Ты пытаешься сдать отчёт за прошлое.\nВремя уже ушло.\nСистема живёт по датам, а не по оправданиям.")
                            return
                    except ValueError as e:
                        await inter.author.add_roles(chuspan)
                        await inter.followup.send("Ты решил переписать будущее в браузере.\nПоменял цифры и почувствовал контроль.\nНо контроль не у тебя.\nТы просто показал, что готов ломать декорации.\nРоль выдана.\nБез обсуждений.")
                        
                        return
                    
                    if matches is None:
                        channel = await inter.guild.fetch_channel(1472757147254263992)
                        await channel.send(f"Распознавание завершилось с ошибкой. Проверьте отчет: {screenshot}", components=[disnake.ui.Button(label="Отчет проверен", emoji="✅", style=disnake.ButtonStyle.grey, custom_id="check_screenshot")])
                        await inter.followup.send(f"Распознавание сорвалось.\nСкриншот не читается или данные на нём искажены.\nСделай новый скрин и отправь снова.\nТекущий скриншот был отправлен разработчику.")
                        return

                    await inter.followup.send(f"Я вижу: {matches} матчей <t:{int(date.timestamp())}:D>.\nЕсли всё верно - нажми «Отправить отчет».\nЕсли нет - просто ничего не делай.\nЧерез 30 секунд скриншот уйдет напрямую разработчику на проверку.\nИногда попытка промолчать говорит больше, чем кнопка.",
                                              components=[disnake.ui.Button(label="Отправить отчет", emoji="🚀", style=disnake.ButtonStyle.green, custom_id="submit_2")])
                    
                    def check(inter: disnake.MessageInteraction):
                        return (
                            inter.component.custom_id == "submit_2"
                        )

                    try:
                        await self.bot.wait_for("button_click", check=check, timeout=30)

                        if int(matches) > 60:
                            await inter.author.add_roles(chuspan)
                            await message.edit("Лезешь править код элемента в браузере?\nТы не хакер. Ты просто человек, который дергает декорации и думает, что меняет систему.\nТебе выдали новую роль.\nТы её заслужил.", view=None)
                            
                            return
                        elif int(matches) < 10:
                            await message.edit(f"Зафиксировано: {matches} матчей <t:{int(date.timestamp())}:D>.\nЭтого недостаточно.\nПравила были понятны заранее.\nОтчет отклонен.\nПопробуй снова, когда цифры будут соответствовать требованиям.", view=None)
                            return

                        date = datetime.datetime.strftime(date, "%d.%m.")
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
                            request = [{
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
                                            "userEnteredValue": {"numberValue": matches},
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
                                body={"requests": request}
                            ).execute()

                            await message.edit("✅ Твой отчет принят! +Respect", view=None)

                            if role in inter.author.roles:
                                await inter.author.remove_roles(role)

                            channel = await inter.guild.fetch_channel(1468632013807419425)
                            embed = disnake.Embed(title="Guardian Grind #PA1KA", description=f"{matches} ДМов закрыто. +Respect.\n\n**[Пруф]({screenshot})**\n", colour=disnake.Colour.dark_gold())
                            await channel.send(content=f"🎯 {inter.author.mention} сдал отчет!", embed = embed)
                        else:
                            await message.edit("🚫 У тебя уже сдан отчет в эту дату!", view=None)
                    
                    except TimeoutError:
                        await message.edit("Ты ничего не нажал.\nИногда молчание - это тоже решение.\nОтчет ушел на ручную проверку.\nСистема запоминает всё.", view=None)
                        
                        channel = await inter.guild.fetch_channel(1472757147254263992)
                        await channel.send(f"Участник не нажал кнопку. Проверьте отчет: {screenshot}", components=[disnake.ui.Button(label="Отчет проверен", emoji="✅", style=disnake.ButtonStyle.grey, custom_id="check_screenshot")])
                else:
                    await inter.followup.send("🚫 Указана неправильная ссылка на скриншот!")
            else:
                await inter.followup.send("🚫 Ссылка на скриншот указана в неправильном формате!")
        except Exception as e:
            traceback.print_exc()

            channel = await inter.guild.fetch_channel(1468311758816153726)
            embed = disnake.Embed(title="🚫 Возникла непредвиденная ошибка!", description=f"```{e}```\n\nАвтор: {inter.author.mention}")

            await inter.followup.send(f"🚫 Возникла непредвиденная ошибка!")
            await channel.send(embed = embed)

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        if inter.component.custom_id == "check_screenshot":
            unix_dt = int(datetime.datetime.now().timestamp())
            new = inter.message.content + f"\n\nСкриншот был проверен <t:{unix_dt}:f> пользователем {inter.author.mention}"
            await inter.response.edit_message(content=new, view=None)
        
        

def setup(bot):
    bot.add_cog(Submit2(bot))
