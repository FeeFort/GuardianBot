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
    disnake.SelectOption(label="Железо", value="iron"),
    disnake.SelectOption(label="Бронза", value="bronze"),
    disnake.SelectOption(label="Серебро", value="silver"),
    disnake.SelectOption(label="Золото", value="gold"),
    disnake.SelectOption(label="Платина", value="platinum"),
    disnake.SelectOption(label="Алмаз", value="diamond"),
    disnake.SelectOption(label="Рассвет", value="ascendant"),
    disnake.SelectOption(label="Бессмертный", value="immortal"),
    disnake.SelectOption(label="Радиант", value="radiant"),
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