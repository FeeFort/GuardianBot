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

RANK_OPTIONS = [
    disnake.SelectOption(emoji="<:Iron_1_Rank:1469278406373015607>", label="Железо 1", value="iron"),
    disnake.SelectOption(emoji="<:Iron_2_Rank:1469278419316637907>", label="Железо 2", value="iron2"),
    disnake.SelectOption(emoji="<:Iron_3_Rank:1469278440812445859>", label="Железо 3", value="iron3"),
    disnake.SelectOption(emoji="<:Bronze_1_Rank:1469278226428854312>", label="Бронза 1", value="bronze"),
    disnake.SelectOption(emoji="<:Bronze_2_Rank:1469278239393448120>", label="Бронза 2", value="bronze2"),
    disnake.SelectOption(emoji="<:Bronze_3_Rank:1469278252173496441>", label="Бронза 3", value="bronze3"),
    disnake.SelectOption(emoji="<:Silver_1_Rank:1469278527567433802>", label="Серебро 1", value="silver"),
    disnake.SelectOption(emoji="<:Silver_2_Rank:1469278575436759117>", label="Серебро 2", value="silver2"),
    disnake.SelectOption(emoji="<:Silver_3_Rank:1469278587495645238>", label="Серебро 3", value="silver3"),
    disnake.SelectOption(emoji="<:Gold_1_Rank:1469278307542503504>", label="Золото 1", value="gold"),
    disnake.SelectOption(emoji="<:Gold_2_Rank:1469278322340003840>", label="Золото 2", value="gold2"),
    disnake.SelectOption(emoji="<:Gold_3_Rank:1469278338768961587>", label="Золото 3", value="gold3"),
    disnake.SelectOption(emoji="<:Platinum_1_Rank:1469278467534225532>", label="Платина 1", value="platinum"),
    disnake.SelectOption(emoji="<:Platinum_2_Rank:1469278484231618733>", label="Платина 2", value="platinum2"),
    disnake.SelectOption(emoji="<:Platinum_3_Rank:1469278499058618443>", label="Платина 3", value="platinum3"),
    disnake.SelectOption(emoji="<:Diamond_1_Rank:1469278266513686670>", label="Алмаз 1", value="diamond"),
    disnake.SelectOption(emoji="<:Diamond_2_Rank:1469278278962647246>", label="Алмаз 2", value="diamond2"),
    disnake.SelectOption(emoji="<:Diamond_3_Rank:1469278292707246221>", label="Алмаз 3", value="diamond3"),
    disnake.SelectOption(emoji="<:Ascendant_1_Rank:1469278184188153857>", label="Рассвет 1", value="ascendant"),
    disnake.SelectOption(emoji="<:Ascendant_2_Rank:1469278198901510300>", label="Рассвет 2", value="ascendant2"),
    disnake.SelectOption(emoji="<:Ascendant_3_Rank:1469278211656646833>", label="Рассвет 3", value="ascendant3"),
    disnake.SelectOption(emoji="<:Immortal_1_Rank:1469278353159618631>", label="Бессмертный 1", value="immortal"),
    disnake.SelectOption(emoji="<:Immortal_2_Rank:1469278368246796289>", label="Бессмертный 2", value="immortal2"),
    disnake.SelectOption(emoji="<:Immortal_3_Rank:1469278389268381812>", label="Бессмертный 3", value="immortal3"),
    disnake.SelectOption(emoji="<:Radiant_Rank:1469278514082615390>", label="Радиант", value="radiant"),
]

class RankView(disnake.ui.View):
    def __init__(self, nickname: str, goal: str):
        super().__init__(timeout=300)
        self.nickname = nickname
        self.goal = goal
        self.current_rank = None
        self.peak_rank = None

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

        # тут сохраняй в БД/Sheets
        await inter.response.edit_message(
            content=(
                " Регистрация завершена!\n"
                f"Ник: **{self.nickname}**\n"
                f"Текущий ранг: **{self.current_rank}**\n"
                f"Пик: **{self.peak_rank}**\n"
                f"Цель: **{self.goal}**"
            ),
            view=None
        )

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
            )
        ]
        super().__init__(title="Регистрация", components=components)

    # The callback received when the user input is completed.
    async def callback(self, inter: disnake.ModalInteraction):
        nickname = inter.text_values["nickname"].strip()
        goal = inter.text_values["goal"].strip()

        view = RankView(nickname=nickname, goal=goal)
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
        await inter.followup.send("Registration", components=[disnake.ui.Button(label="Зарегестрироваться", custom_id="register")])

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        if inter.component.custom_id == "register":
            await inter.response.send_modal(modal=RegisterModal()) 


def setup(bot):
    bot.add_cog(Registration(bot))