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
            disnake.ui.StringSelect(
                placeholder="Выбери свой текущий ранг.",
                options=[
                    disnake.ui.SelectOption(
                        label="Железо",
                        value="iron"
                    ),
                    disnake.ui.SelectOption(
                        label="Бронза",
                        value="bronze"
                    ),
                    disnake.ui.SelectOption(
                        label="Серебро",
                        value="silver"
                    ),
                    disnake.ui.SelectOption(
                        label="Золото",
                        value="gold"
                    ),
                    disnake.ui.SelectOption(
                        label="Платина",
                        value="platinum"
                    ),
                    disnake.ui.SelectOption(
                        label="Алмаз",
                        value="diamond"
                    ),
                    disnake.ui.SelectOption(
                        label="Рассвет",
                        value="ascedant"
                    ),
                    disnake.ui.SelectOption(
                        label="Бессмертный",
                        value="immortal"
                    ),
                    disnake.ui.SelectOption(
                        label="Радиант",
                        value="radiant"
                    )
                ]
            ),

            disnake.ui.StringSelect(
                placeholder="Выбери свой ранг в пике.",
                options=[
                    disnake.ui.SelectOption(
                        label="Железо",
                        value="iron"
                    ),
                    disnake.ui.SelectOption(
                        label="Бронза",
                        value="bronze"
                    ),
                    disnake.ui.SelectOption(
                        label="Серебро",
                        value="silver"
                    ),
                    disnake.ui.SelectOption(
                        label="Золото",
                        value="gold"
                    ),
                    disnake.ui.SelectOption(
                        label="Платина",
                        value="platinum"
                    ),
                    disnake.ui.SelectOption(
                        label="Алмаз",
                        value="diamond"
                    ),
                    disnake.ui.SelectOption(
                        label="Рассвет",
                        value="ascedant"
                    ),
                    disnake.ui.SelectOption(
                        label="Бессмертный",
                        value="immortal"
                    ),
                    disnake.ui.SelectOption(
                        label="Радиант",
                        value="radiant"
                    )
                ]
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
        await inter.response.send_message("✅ Регистрация успешно завершена!", ephemeral=True)


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