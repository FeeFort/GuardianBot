import datetime

import disnake
from disnake.ext import commands, tasks
from typing import List, Tuple, Optional

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDS_FILE = "guardianchallenge-0e281d644000.json"

creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1G6FT2CrUIGBVJaNUKOZ6Me3l7Ey2iM-0X1f7SqvPBoQ/edit?gid=1654540911#gid=1654540911")
ws = sheet.worksheet("LEADERBOARD")

class ConfirmKickView(disnake.ui.View):
    def __init__(self, ws, kick_list: list[tuple[disnake.Member, int]], *, timeout=600):
        super().__init__(timeout=timeout)
        self.ws = ws
        self.kick_list = kick_list  # [(member, row), ...]
        self.confirming = False

    def is_empty(self) -> bool:
        return not self.kick_list

    @disnake.ui.button(label="Кикнуть всех", style=disnake.ButtonStyle.danger)
    async def kick_all(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if self.is_empty():
            return await inter.response.send_message("Список пуст — кикать некого.", ephemeral=True)

        # Переключаемся в режим подтверждения
        self.confirming = True
        button.disabled = True

        # Добавляем кнопки подтверждения
        self.add_item(disnake.ui.Button(label="Да, кикнуть", style=disnake.ButtonStyle.danger, custom_id="afk_confirm_yes"))
        self.add_item(disnake.ui.Button(label="Отмена", style=disnake.ButtonStyle.secondary, custom_id="afk_confirm_no"))

        await inter.response.edit_message(
            content=" Ты точно хочешь кикнуть всех из списка AFK и удалить их строки из таблицы?",
            view=self
        )

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        # Тут можешь ограничить по ролям/правам (очень рекомендую)
        # Например: только админы
        if inter.guild_permissions.kick_members:
            return True
        await inter.response.send_message("Недостаточно прав.", ephemeral=True)
        return False

    @disnake.ui.button(label="(internal)", style=disnake.ButtonStyle.secondary, custom_id="afk_confirm_yes", disabled=True)
    async def _hidden_yes(self, *_):  # Заглушка, реальную кнопку добавляем динамически
        pass

    @disnake.ui.button(label="(internal)", style=disnake.ButtonStyle.secondary, custom_id="afk_confirm_no", disabled=True)
    async def _hidden_no(self, *_):
        pass

    async def on_timeout(self):
        # По таймауту просто дизейблим кнопки
        for item in self.children:
            if isinstance(item, disnake.ui.Button):
                item.disabled = True

    async def on_button_click(self, inter: disnake.MessageInteraction):
        # disnake сам вызывает колбэки декораторов, но динамически добавленные кнопки удобнее ловить так
        cid = inter.data.get("custom_id")

        if cid == "afk_confirm_no":
            # Отменяем
            for item in self.children:
                if isinstance(item, disnake.ui.Button):
                    item.disabled = True
            await inter.response.edit_message(content=" Отменено.", view=self)
            return

        if cid == "afk_confirm_yes":
            # Применяем политику (кик + удаление строк)
            await inter.response.send_message("Ок, выполняю кик и чистку таблицы…", ephemeral=True)

            kicked, failed = await apply_policy_kick_and_delete(self.ws, self.kick_list)

            # Блокируем кнопки
            for item in self.children:
                if isinstance(item, disnake.ui.Button):
                    item.disabled = True

            await inter.message.edit(
                content=f" Готово. Кикнуто: {kicked}. Ошибок: {failed}.",
                view=self
            )

def is_empty(value: str | None) -> bool:
    return value is None or str(value).strip() == ""

def get_last_3_dates_msk():
    now = datetime.datetime.now() + datetime.timedelta(hours=3)  # МСК
    return [
        (now - datetime.timedelta(days=1)).strftime("%d.%m."),
        (now - datetime.timedelta(days=2)).strftime("%d.%m."),
        (now - datetime.timedelta(days=3)).strftime("%d.%m."),
    ]

def get_wave_ranges(ws):
    try:
        divider_cell = ws.find("Вторая волна приглашений")
    except gspread.exceptions.CellNotFound:
        raise RuntimeError("Не найдена строка 'Вторая волна приглашений'")

    divider_row = divider_cell.row

    participants_col = ws.col_values(3)  # колонка C (Discord.name)
    last_row = max(i for i, v in enumerate(participants_col, start=1) if v.strip())

    wave1 = (2, divider_row - 1)
    wave2 = (divider_row + 1, last_row)

    # защитка от кривых диапазонов
    if wave1[1] < wave1[0]:
        wave1 = (2, 1)  # пустой диапазон
    if wave2[1] < wave2[0]:
        wave2 = (divider_row + 1, divider_row)  # пустой диапазон

    return wave1, wave2

def cell_value(row_list):
    # row_list это либо ['10'], либо []
    return row_list[0] if row_list else ""

def get_afk_candidates(
    ws,
    guild: disnake.Guild,
    members: List[disnake.Member],
    row_range: tuple[int, int],
    cols: list[int],
    name_col: int = 3,                 # C = discord.name
    start_date: str | None = None,     # "09.02" for wave2, None for wave1
) -> tuple[list[disnake.Member], list[tuple[disnake.Member, int]], list[str]]:
    """
    Возвращает:
      warn:   список Member (2 дня подряд пусто, а 3-й день был непустой)
      kick:   список (Member, row) для кика и удаления строки
      manual: список discord.name, которых не нашли в гильдии

    ВАЖНО:
      - cols должен быть списком из 3 номеров колонок (1-based), соответствующих проверяемым дням
      - row_range = (start_row, end_row) — диапазон строк волны (включительно)
      - читаем одним прямоугольным диапазоном, чтобы не было рассинхрона длин
    """

    start_row, end_row = row_range
    if end_row < start_row:
        return [], [], []

    if start_date:
        try:
            start_dt = datetime.datetime.strptime(start_date, "%d.%m.")
        except ValueError:
            raise ValueError(f"start_date must be DD.MM, got: {start_date!r}")

        if "get_last_3_dates_msk" in globals():
            dates = get_last_3_dates_msk()
            for d in dates:
                if datetime.datetime.strptime(d, "%d.%m.") < start_dt:
                    return [], [], []

    min_col = min([name_col, *cols])
    max_col = max([name_col, *cols])

    a1_start = rowcol_to_a1(start_row, min_col)
    a1_end = rowcol_to_a1(end_row, max_col)

    grid = ws.get(f"{a1_start}:{a1_end}")

    def safe_get(row: list, absolute_col: int) -> str:
        """Достаёт значение из строки grid по абсолютному номеру колонки (1-based)."""
        idx = absolute_col - min_col
        if idx < 0:
            return ""
        if idx >= len(row):
            return ""
        v = row[idx]
        return "" if v is None else str(v)

    def is_empty(v: str) -> bool:
        return v.strip() == ""

    warn: list[disnake.Member] = []
    kick: list[tuple[disnake.Member, int]] = []
    manual: list[str] = []

    c1, c2, c3 = cols

    print(f"GRID: {grid}")

    for offset, row in enumerate(grid):
        sheet_row = start_row + offset

        name = safe_get(row, name_col).strip()
        if is_empty(name):
            continue

        v1 = safe_get(row, c1)
        v2 = safe_get(row, c2)
        v3 = safe_get(row, c3)

        has1 = not is_empty(v1)
        has2 = not is_empty(v2)
        has3 = not is_empty(v3)
        print(f"HAS1: {has1}, HAS2: {has2}, HAS3: {has3}")

        for m in members:
            if m.name == name or m.display_name == name:
                member = m
                break
            else:
                member = None
                manual.append(name)

        if (not has1) and (not has2) and (not has3):
            kick.append((member, sheet_row))
        elif (not has1) and (not has2) and has3:
            warn.append(member)

    return warn, kick, manual

async def apply_policy(ws, warn, kick):
    for member in warn:
        try:
            await member.send(
                " Ты не отправлял отчёты 2 дня подряд. "
                "Если сегодня не будет отчёта — ты будешь удалён из челленджа."
            )
        except:
            pass

    """for member, row in sorted(kick, key=lambda x: x[1], reverse=True):
        try:
            await member.kick(reason="AFK 3 дня подряд")
        except:
            pass

        ws.delete_rows(row)"""

async def apply_policy_kick_and_delete(ws, kick_list: list[tuple[disnake.Member, int]]):
    """
    kick_list: [(member, row_index_in_sheet), ...]
    Важно: удаляем строки СНИЗУ ВВЕРХ.
    """
    kicked = 0
    failed = 0

    for member, _row in kick_list:
        try:
            #await member.remove_roles(role)
            #await member.kick(reason="AFK 3 дня подряд")
            kicked += 1
        except:
            failed += 1

    for _member, row in sorted(kick_list, key=lambda x: x[1], reverse=True):
        try:
            ws.delete_rows(row)
        except:
            failed += 1

    return kicked, failed

def build_afk_embeds(
    kick_list: list[tuple[disnake.Member, int]],
    *,
    title: str = "AFK-кандидаты (3 дня без отчётов)",
    per_embed: int = 30
) -> list[disnake.Embed]:
    """
    kick_list: [(member, row), ...]
    per_embed: сколько строк с участниками класть в один embed (30 обычно безопасно по лимитам).
    """
    if not kick_list:
        e = disnake.Embed(title=title, description="Никого кикать не надо ")
        return [e]

    embeds: list[disnake.Embed] = []
    total = len(kick_list)

    for start in range(0, total, per_embed):
        chunk = kick_list[start:start + per_embed]

        # Важно: не пихаем тысячи символов в одно поле — держим аккуратно
        lines = [f"• {m} — строка {row}" for (m, row) in chunk]
        page = (start // per_embed) + 1
        pages = (total + per_embed - 1) // per_embed

        e = disnake.Embed(
            title=title,
            description=f"Страница **{page}/{pages}** • Всего: **{total}**"
        )
        e.add_field(name="Список", value="\n".join(lines), inline=False)
        embeds.append(e)

    return embeds

async def send_afk_report(admin_channel: disnake.TextChannel, ws, kick_list):
    embeds = build_afk_embeds(kick_list, per_embed=30)

    view = ConfirmKickView(ws, kick_list)  # твоя View: "Кикнуть всех" -> подтверждение -> apply_policy

    # 1) Первая страница с кнопкой
    await admin_channel.send(embed=embeds[0], view=view)

    # 2) Остальные страницы без кнопок
    for e in embeds[1:]:
        await admin_channel.send(embed=e)

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_date = datetime.date(2026, 2, 9)
    
    async def cog_load(self):
        print("AFK loaded!")
        self.afk.start()

    def cog_unload(self):
        print("AFK unloaded!")
        self.afk.cancel()

    @tasks.loop(minutes=1)
    async def afk(self):
        guild = await self.bot.fetch_guild(1467650949731582220)
        now = datetime.datetime.now() + datetime.timedelta(hours=3)
        now_date = datetime.date(now.year, now.month, now.day)

        if now_date == self.update_date:
            wave1, wave2 = get_wave_ranges(ws)
            print(f"WAVE 1: {wave1}")
            print(f"WAVE 2: {wave2}")

            headers = ws.row_values(1)
            dates = get_last_3_dates_msk()
            cols = [headers.index(d) + 1 for d in dates]
            members = []
            async for m in guild.fetch_members(limit=None): members.append(m)

            warn1, kick1, manual1 = get_afk_candidates(ws, guild, members, wave1, cols, name_col=3)
            warn2, kick2, manual2 = get_afk_candidates(ws, guild, members, wave2, cols, name_col=3, start_date="09.02.")

            print(f"KICK1: {kick1}")
            print(f"WARN1: {warn1}")
            print(f"MANUAL1: {manual1}")

            kick_all = kick1 + kick2

            admin_channel = await guild.fetch_channel(1470128018294050818)
            await send_afk_report(admin_channel, ws, kick_all)
            await apply_policy(ws, warn1 + warn2, None)

            self.update_date = datetime.date(now.year, now.month, now.day + 1)
            print(f"(AFK) UPDATE DATE: {self.update_date}")

def setup(bot):
    bot.add_cog(AFK(bot))