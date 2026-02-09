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
ws = sheet.worksheet("LEADERBOARDTEST")

class ConfirmKickView(disnake.ui.View):
    def __init__(self, ws, kick_list, left_server, *, timeout=600):
        super().__init__(timeout=timeout)
        self.ws = ws
        self.kick_list = kick_list              # [(member, row), ...]
        self.left_server = left_server          # [row, ...]
        self.confirm_mode = False

        # На старте кнопки подтверждения скрыты/выключены
        self.btn_yes.disabled = True
        self.btn_no.disabled = True

    def is_empty(self) -> bool:
        return not self.kick_list and not self.left_server

    @disnake.ui.button(label="Кикнуть всех", style=disnake.ButtonStyle.danger, custom_id="afk_kick_all")
    async def kick_all(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if self.is_empty():
            return await inter.response.send_message("Список пуст — кикать некого.", ephemeral=True)

        self.confirm_mode = True
        button.disabled = True

        # включаем подтверждение
        self.btn_yes.disabled = False
        self.btn_no.disabled = False

        await inter.response.edit_message(
            content="⚠️ Ты точно хочешь кикнуть всех из списка AFK и удалить их строки из таблицы?",
            view=self
        )

    @disnake.ui.button(label="Да, кикнуть", style=disnake.ButtonStyle.danger, custom_id="afk_confirm_yes")
    async def btn_yes(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # можно ещё раз проверить права
        if not inter.guild_permissions.kick_members:
            return await inter.response.send_message("Недостаточно прав.", ephemeral=True)

        await inter.response.send_message("Ок, выполняю кик и чистку таблицы…", ephemeral=True)

        stats = await apply_policy_kick_and_delete(
            self.ws,
            inter.guild,
            self.kick_list,
            self.left_server
        )

        # отключаем все кнопки
        for item in self.children:
            if isinstance(item, disnake.ui.Button):
                item.disabled = True

        await inter.message.edit(
            content=(
                "✅ Готово.\n\n"
                f"Роль снята успешно: {stats['roles_removed']}\n"
                f"Самостоятельно вышли: {stats['left_server']}\n"
                f"Не удалось снять роль: {stats['failed_roles']}\n"
                f"Удалено из таблицы: {stats['rows_deleted']}\n"
                f"Не удалось удалить строки: {stats['failed_rows']}"
            ),
            view=self
        )

    @disnake.ui.button(label="Отмена", style=disnake.ButtonStyle.secondary, custom_id="afk_confirm_no")
    async def btn_no(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # отключаем все кнопки
        for item in self.children:
            if isinstance(item, disnake.ui.Button):
                item.disabled = True

        await inter.response.edit_message(content="❎ Отменено.", view=self)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, disnake.ui.Button):
                item.disabled = True

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

    AFK_WHITELIST_IDS = {
        359586978234368003,  # etnaa
        246313643900141568,  # pa1ka
        435463855250866176,  # dreammaker
        368672308065337345,  # astedoto
    }

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
    left_server: list[str] = []

    c1, c2, c3 = cols

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

        member = None

        for m in members:
            if m.name == name or m.display_name == name:
                member = m
                break

        if member is None:
            left_server.append(sheet_row)
            continue

        if member.id in AFK_WHITELIST_IDS:
            continue

        if (not has1) and (not has2) and (not has3):
            kick.append((member, sheet_row))
        elif (not has1) and (not has2) and has3:
            warn.append(member)

    return warn, kick, left_server

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

async def apply_policy_kick_and_delete(
    ws,
    guild: disnake.Guild,
    kick_list: list[tuple[disnake.Member, int]],
    left_server_rows: list[int],
):
    """
    kick_list: [(member, row)] — участники на сервере (снимаем роль + удаляем строку)
    left_server_rows: [row, ...] — участники, которые уже вышли (только удаляем строку)

    ВАЖНО: строки всегда удаляются СНИЗУ ВВЕРХ.
    """

    roles_removed = 0
    failed_roles = 0

    rows_deleted = 0
    failed_rows = 0

    role_id = 1467651039695081562

    role = guild.get_role(role_id)
    if role is None:
        role = await guild.fetch_role(role_id)

    # 1) Снимаем роль у тех, кто ещё на сервере
    for member, _row in kick_list:
        try:
            #await member.remove_roles(role, reason="AFK 3 дня подряд")
            roles_removed += 1
        except Exception as e:
            failed_roles += 1
            print(f"[AFK] remove_roles failed for {member} ({member.id}): {e!r}")

    # 2) Удаляем строки (kick + left_server) снизу вверх
    rows_to_delete = (
        [row for _, row in kick_list] +
        left_server_rows
    )

    for row in sorted(set(rows_to_delete), reverse=True):
        try:
            ws.delete_rows(row)
            rows_deleted += 1
        except Exception as e:
            failed_rows += 1
            print(f"[AFK] delete_rows failed for row={row}: {e!r}")

    return {
        "roles_removed": roles_removed,
        "left_server": len(left_server_rows),
        "failed_roles": failed_roles,
        "rows_deleted": rows_deleted,
        "failed_rows": failed_rows,
    }

def build_afk_embeds(
    kick_list: list[tuple[disnake.Member, int]],
    left_server_rows: list[int],
    *,
    title: str = "AFK-кандидаты (3 дня без отчётов)",
    per_embed: int = 30
) -> list[disnake.Embed]:
    """
    kick_list: [(member, row), ...] — участники на сервере (AFK)
    left_server_rows: [row, ...] — участники, уже вышедшие с сервера
    """

    embeds: list[disnake.Embed] = []

    # =========================
    # 1) AFK (kick_list)
    # =========================
    if kick_list:
        total = len(kick_list)
        pages = (total + per_embed - 1) // per_embed

        for start in range(0, total, per_embed):
            chunk = kick_list[start:start + per_embed]
            page = (start // per_embed) + 1

            lines = [f"• {member} — строка {row}" for member, row in chunk]

            e = disnake.Embed(
                title=title,
                description=f"Страница **{page}/{pages}** • Всего AFK: **{total}**"
            )
            e.add_field(name="AFK-участники", value="\n".join(lines), inline=False)
            embeds.append(e)
    else:
        embeds.append(
            disnake.Embed(
                title=title,
                description="AFK-участников нет "
            )
        )

    # =========================
    # 2) Left server
    # =========================
    if left_server_rows:
        total = len(left_server_rows)
        pages = (total + per_embed - 1) // per_embed

        for start in range(0, total, per_embed):
            chunk = left_server_rows[start:start + per_embed]
            page = (start // per_embed) + 1

            lines = [f"• строка {row}" for row in chunk]

            e = disnake.Embed(
                title="Участники, вышедшие с сервера",
                description=f"Страница **{page}/{pages}** • Всего: **{total}**"
            )
            e.add_field(
                name="Будут удалены из таблицы",
                value="\n".join(lines),
                inline=False
            )
            embeds.append(e)

    return embeds

async def send_afk_report(admin_channel: disnake.TextChannel, ws, kick_list, left_server):
    embeds = build_afk_embeds(kick_list, left_server, per_embed=30)

    view = ConfirmKickView(ws, kick_list, left_server)  # твоя View: "Кикнуть всех" -> подтверждение -> apply_policy

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

            headers = ws.row_values(1)
            dates = get_last_3_dates_msk()
            cols = [headers.index(d) + 1 for d in dates]
            members = []
            async for m in guild.fetch_members(limit=None): members.append(m)

            warn1, kick1, left_server1 = get_afk_candidates(ws, guild, members, wave1, cols, name_col=3)
            warn2, kick2, left_server2 = get_afk_candidates(ws, guild, members, wave2, cols, name_col=3, start_date="09.02.")

            kick_all = kick1 + kick2

            admin_channel = await guild.fetch_channel(1470128018294050818)
            await send_afk_report(admin_channel, ws, kick_all, left_server1 + left_server2)
            #await apply_policy(ws, warn1 + warn2, None)

            self.update_date = datetime.date(now.year, now.month, now.day + 1)
            print(f"(AFK) UPDATE DATE: {self.update_date}")

def setup(bot):
    bot.add_cog(AFK(bot))