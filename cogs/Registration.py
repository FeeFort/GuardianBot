import datetime

import disnake
from disnake.ext import commands
from disnake import TextInputStyle

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
ws_reg = sheet.worksheet("REG_DATA")

RANK_OPTIONS = [
    disnake.SelectOption(emoji="<:Iron_1_Rank:1469278406373015607>", label="Железо 1", value="Iron 1"),
    disnake.SelectOption(emoji="<:Iron_2_Rank:1469278419316637907>", label="Железо 2", value="Iron 2"),
    disnake.SelectOption(emoji="<:Iron_3_Rank:1469278440812445859>", label="Железо 3", value="Iron 3"),
    disnake.SelectOption(emoji="<:Bronze_1_Rank:1469278226428854312>", label="Бронза 1", value="Bronze 1"),
    disnake.SelectOption(emoji="<:Bronze_2_Rank:1469278239393448120>", label="Бронза 2", value="Bronze 2"),
    disnake.SelectOption(emoji="<:Bronze_3_Rank:1469278252173496441>", label="Бронза 3", value="Bronze 3"),
    disnake.SelectOption(emoji="<:Silver_1_Rank:1469278527567433802>", label="Серебро 1", value="Silver 1"),
    disnake.SelectOption(emoji="<:Silver_2_Rank:1469278575436759117>", label="Серебро 2", value="Silver 2"),
    disnake.SelectOption(emoji="<:Silver_3_Rank:1469278587495645238>", label="Серебро 3", value="Silver 3"),
    disnake.SelectOption(emoji="<:Gold_1_Rank:1469278307542503504>", label="Золото 1", value="Gold 1"),
    disnake.SelectOption(emoji="<:Gold_2_Rank:1469278322340003840>", label="Золото 2", value="Gold 2"),
    disnake.SelectOption(emoji="<:Gold_3_Rank:1469278338768961587>", label="Золото 3", value="Gold 3"),
    disnake.SelectOption(emoji="<:Platinum_1_Rank:1469278467534225532>", label="Платина 1", value="Platinum 1"),
    disnake.SelectOption(emoji="<:Platinum_2_Rank:1469278484231618733>", label="Платина 2", value="Platinum 2"),
    disnake.SelectOption(emoji="<:Platinum_3_Rank:1469278499058618443>", label="Платина 3", value="Platinum 3"),
    disnake.SelectOption(emoji="<:Diamond_1_Rank:1469278266513686670>", label="Алмаз 1", value="Diamond 1"),
    disnake.SelectOption(emoji="<:Diamond_2_Rank:1469278278962647246>", label="Алмаз 2", value="Diamond 2"),
    disnake.SelectOption(emoji="<:Diamond_3_Rank:1469278292707246221>", label="Алмаз 3", value="Diamond 3"),
    disnake.SelectOption(emoji="<:Ascendant_1_Rank:1469278184188153857>", label="Рассвет 1", value="Ascendant 1"),
    disnake.SelectOption(emoji="<:Ascendant_2_Rank:1469278198901510300>", label="Рассвет 2", value="Ascendant 2"),
    disnake.SelectOption(emoji="<:Ascendant_3_Rank:1469278211656646833>", label="Рассвет 3", value="Ascendant 3"),
    disnake.SelectOption(emoji="<:Immortal_1_Rank:1469278353159618631>", label="Бессмертный 1", value="Immortal 1"),
    disnake.SelectOption(emoji="<:Immortal_2_Rank:1469278368246796289>", label="Бессмертный 2", value="Immortal 2"),
    disnake.SelectOption(emoji="<:Immortal_3_Rank:1469278389268381812>", label="Бессмертный 3", value="Immortal 3"),
    disnake.SelectOption(emoji="<:Radiant_Rank:1469278514082615390>", label="Радиант", value="Radiant"),
]

class RankView(disnake.ui.View):
    def __init__(self, nickname: str, goal: str, results_now: str):
        super().__init__(timeout=300)
        self.nickname = nickname
        self.goal = goal
        self.current_rank = None
        self.peak_rank = None
        self.results_now = results_now

    @disnake.ui.string_select(
        placeholder="Выбери свой текущий ранг",
        options=RANK_OPTIONS,
        custom_id="current_rank",
        min_values=1,
        max_values=1,
    )
    async def current_rank_select(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        self.current_rank = select.values[0]
        await inter.response.defer(ephemeral=True)

    @disnake.ui.string_select(
        placeholder="Выбери свой ранг в пике",
        options=RANK_OPTIONS,
        custom_id="peak_rank",
        min_values=1,
        max_values=1,
    )
    async def peak_rank_select(self, select: disnake.ui.StringSelect, inter: disnake.MessageInteraction):
        self.peak_rank = select.values[0]
        await inter.response.defer(ephemeral=True)

    @disnake.ui.button(label="Сохранить", style=disnake.ButtonStyle.green)
    async def save(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if not self.current_rank or not self.peak_rank:
            return await inter.response.send_message("Выбери оба ранга.", ephemeral=True)
        
        ws_reg.append_row(
            [
                datetime.datetime.strftime(datetime.datetime.now(), "%d.%m.%Y %H:%M:%S"),
                self.nickname,
                self.current_rank,
                self.peak_rank,
                self.goal,
                inter.author.name,
                "-"
            ],
            value_input_option="USER_ENTERED"
        )

        await inter.response.edit_message(
            content=(
                "✅ Регистрация завершена!\n"
                f"**Ник:** {self.nickname}\n"
                f"**Текущий ранг:** {self.current_rank}\n"
                f"**Пик:** {self.peak_rank}\n"
                f"**Цель:** {self.goal}\n"
                f"**Игровые ощущения сейчас:** {self.results_now}"
            ),
            view=None
        )

        channel = await inter.guild.fetch_channel(1469283626565894235)
        await channel.send(content=f"{inter.author.mention}", embed=disnake.Embed(title="🎯 Новый челленджер!", description=f"**Ник:** {self.nickname}\n**Текущий ранг:** {self.current_rank}\n**Пик:** {self.peak_rank}\n**Цель:** {self.goal}\n**Игровые ощущения сейчас:** {self.results_now}"))

class RegisterModal(disnake.ui.Modal):
    def __init__(self):
        # The details of the modal, and its components
        components = [
            disnake.ui.TextInput(
                label="Твой никнейм в игре:",
                placeholder="pa1ka#name",
                custom_id="nickname",
                style=TextInputStyle.short
            ),
            disnake.ui.TextInput(
                label="К чему хочешь придти за этот месяц?",
                placeholder="Хочу апнуться в скилле.",
                custom_id="goal",
                style=TextInputStyle.paragraph
            ),
            disnake.ui.TextInput(
                label="Запись результатов",
                placeholder="Опишите свои текущие игровые ощущения и сохраните скрин трекера с K/D и HS% для итогового сравнения.",
                custom_id="results_now",
                style=TextInputStyle.paragraph
            )
        ]
        super().__init__(title="Регистрация", components=components)

    # The callback received when the user input is completed.
    async def callback(self, inter: disnake.ModalInteraction):
        nickname = inter.text_values["nickname"].strip()
        goal = inter.text_values["goal"].strip()
        results_now = inter.text_values["results_now"].strip()

        view = RankView(nickname=nickname, goal=goal, results_now=results_now)
        await inter.response.send_message(
            "Теперь выбери ранги и нажми кнопку ниже:",
            view=view,
            ephemeral=True
        )


class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        print("Registration loaded!")

    @commands.slash_command(name="register")
    async def register(self, inter):
        await inter.response.defer()
        await inter.followup.send("Registration")
        await inter.channel.send(embed=disnake.Embed(title="🏆 #PA1KA GUARDIAN CHALLENGE", description="Добро пожаловать.\nЭто не обычный сервер. Здесь **не ищут лёгких путей и быстрых оправданий.**\n\nGuardian Challenge — место, где **ты ломаешь себя в VALORANT**, играя Deathmatch **только с Guardian.**\n**Каждый день. 10 матчей. Без исключений.**\nХочешь прогресс — **плати временем, концентрацией и дисциплиной.**\n\nЗдесь не важно, **кто ты был.**\nВажно, **кем станешь после сотен матчей и тысяч выстрелов.**\n\nЕсли готов войти в игру и начать прокачку — **нажми кнопку ниже и зарегистрируйся.**", colour=disnake.Colour.dark_gold()), components=[disnake.ui.Button(label="Зарегестрироваться", custom_id="register")])

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        if inter.component.custom_id == "register":
            await inter.response.send_modal(modal=RegisterModal()) 


def setup(bot):
    bot.add_cog(Registration(bot))