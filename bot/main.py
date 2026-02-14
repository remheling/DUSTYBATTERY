import asyncio
import os
import datetime
import aiosqlite
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest

# ================= CONFIG =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

DB = "database.db"
scheduler = AsyncIOScheduler()

# ================= INIT BOT =================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY,
            auto_delete INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS selected_group (
            owner_id INTEGER PRIMARY KEY,
            group_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            username TEXT,
            start_time TEXT,
            end_time TEXT
        );
        CREATE TABLE IF NOT EXISTS vip (
            user_id INTEGER,
            group_id INTEGER,
            level TEXT,
            end_time TEXT
        );
        CREATE TABLE IF NOT EXISTS mutes (
            user_id INTEGER,
            group_id INTEGER,
            end_time TEXT
        );
        CREATE TABLE IF NOT EXISTS warnings (
            user_id INTEGER,
            group_id INTEGER,
            count INTEGER DEFAULT 0
        );
        """)
        await db.commit()

# ================= UTILS =================
def now():
    return datetime.datetime.now()

def format_dt(dt: datetime.datetime):
    return dt.strftime("%d.%m.%Y %H:%M:%S")

def parse_duration(text: str):
    try:
        if text.endswith("h"):
            return int(text[:-1]) * 3600
        if text.endswith("d"):
            return int(text[:-1]) * 86400
        if text.endswith("m"):
            return int(text[:-1]) * 60
        if text.endswith("s"):
            return int(text[:-1])
        return int(text)
    except:
        return None

async def get_selected_group(owner_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT group_id FROM selected_group WHERE owner_id=?",
            (owner_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def is_admin(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except TelegramBadRequest:
        return False

# ================= SUBSCRIPTION =================
async def check_subscription(user_id: int, channel: str):
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status not in ("left", "kicked")
    except TelegramBadRequest:
        return False
# ================= VIP =================
async def add_vip(user_id, group_id, level, seconds=None):
    end_time = None
    if seconds:
        end_time = (datetime.datetime.now() + datetime.timedelta(seconds=seconds)).isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO vip(user_id, group_id, level, end_time) VALUES(?,?,?,?)",
            (user_id, group_id, level, end_time)
        )
        await db.commit()

async def is_vip(user_id, group_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT level, end_time FROM vip WHERE user_id=? AND (group_id=? OR group_id=0)",
            (user_id, group_id)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        level, end_time = row
        if end_time:
            if datetime.datetime.now() > datetime.datetime.fromisoformat(end_time):
                return None
        return level
# ================= MUTES =================
async def apply_mute(chat_id, user_id, seconds):
    until = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    await bot.restrict_chat_member(
        chat_id,
        user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until
    )
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO mutes(user_id, group_id, end_time) VALUES(?,?,?)",
            (user_id, chat_id, until.isoformat())
        )
        await db.commit()
    return until

async def get_mute_status(user_id, group_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT end_time FROM mutes WHERE user_id=? AND group_id=?",
            (user_id, group_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else None
# ================= WARNINGS =================
async def increase_warning(user_id, group_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT count FROM warnings WHERE user_id=? AND group_id=?",
            (user_id, group_id)
        )
        row = await cursor.fetchone()
        if row:
            count = row[0] + 1
            await db.execute(
                "UPDATE warnings SET count=? WHERE user_id=? AND group_id=?",
                (count, user_id, group_id)
            )
        else:
            count = 1
            await db.execute(
                "INSERT INTO warnings(user_id, group_id, count) VALUES(?,?,?)",
                (user_id, group_id, count)
            )
        await db.commit()
        return count
# ================= AUTO DELETE =================
async def auto_delete_message(chat_id, message_id, seconds):
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass
# ================= SCHEDULER =================
async def scheduler_job():
    now_time = datetime.datetime.now()
    async with aiosqlite.connect(DB) as db:

        # ===== CHANNELS EXPIRATION =====
        cursor = await db.execute(
            "SELECT id, group_id, username, start_time, end_time FROM channels"
        )
        rows = await cursor.fetchall()
        for row in rows:
            cid, group_id, username, start_time, end_time = row
            if end_time:
                end_dt = datetime.datetime.fromisoformat(end_time)
                if now_time > end_dt:
                    await db.execute("DELETE FROM channels WHERE id=?", (cid,))
                    try:
                        await bot.send_message(
                            group_id,
                            f"Канал {username} снят с проверки.\nСтоял с {start_time}"
                        )
                    except:
                        pass

        # ===== VIP EXPIRATION =====
        cursor = await db.execute(
            "SELECT user_id, group_id, level, end_time FROM vip WHERE end_time IS NOT NULL"
        )
        rows = await cursor.fetchall()
        for user_id, group_id, level, end_time in rows:
            if now_time > datetime.datetime.fromisoformat(end_time):
                await db.execute(
                    "DELETE FROM vip WHERE user_id=? AND group_id=?",
                    (user_id, group_id)
                )
                try:
                    await bot.send_message(
                        group_id,
                        f"VIP {level} пользователя {user_id} истёк."
                    )
                except:
                    pass

        # ===== MUTES EXPIRATION =====
        cursor = await db.execute(
            "SELECT user_id, group_id, end_time FROM mutes"
        )
        rows = await cursor.fetchall()
        for user_id, group_id, end_time in rows:
            if now_time > datetime.datetime.fromisoformat(end_time):
                try:
                    await bot.restrict_chat_member(
                        group_id,
                        user_id,
                        permissions=None
                    )
                except:
                    pass
                await db.execute(
                    "DELETE FROM mutes WHERE user_id=? AND group_id=?",
                    (user_id, group_id)
                )

        await db.commit()

def start_scheduler():
    scheduler.add_job(lambda: asyncio.create_task(scheduler_job()), "interval", seconds=30)
    scheduler.start()
# ================= GROUP HANDLER =================
BLACKLIST_COMMANDS = [
    "/group", "/add_one", "/add_channels", "/add_time",
    "/del_one", "/del_all", "/auto_del",
    "/add_VIP", "/add_VIP_local", "/add_VIP_global",
    "/add_VIPPLUS", "/add_VIPPLUS_local", "/add_VIPPLUS_global",
    "/del_VIP", "/del_all_VIP",
    "/del_VIPPLUS", "/del_all_VIPPLUS",
    "/mute_status", "/off_mute", "/del_all_mute",
    "/status"
]

@dp.message(F.chat.type.in_(["group","supergroup"]))
async def group_handler(message: Message):
    user = message.from_user
    chat_id = message.chat.id

    # BLACKLIST COMMANDS
    if message.text:
        for cmd in BLACKLIST_COMMANDS:
            if message.text.startswith(cmd):
                if user.id != OWNER_ID:
                    await message.delete()
                    count = await increase_warning(user.id, chat_id)
                    if count == 1:
                        await message.answer(f"{user.mention_html()}, команда доступна только админ.")
                    elif count == 2:
                        await apply_mute(chat_id, user.id, 600)
                        await message.answer("Мут 10 минут.")
                    elif count == 3:
                        await apply_mute(chat_id, user.id, 3600)
                        await message.answer("Мут 1 час.")
                    elif count >= 4:
                        await apply_mute(chat_id, user.id, 86400)
                        await message.answer("Мут 24 часа.")
                return

    # OWNER SKIP
    if user.id == OWNER_ID:
        return

    # ADMIN SKIP
    member = await bot.get_chat_member(chat_id, user.id)
    if member.status in ("administrator","creator"):
        return

    # VIP SKIP
    vip_level = await is_vip(user.id, chat_id)
    if vip_level:
        return

    # CHECK CHANNELS
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT username FROM channels WHERE group_id=?",
            (chat_id,)
        )
        channels = await cursor.fetchall()

    if not channels:
        return

    for ch in channels:
        ok = await check_subscription(user.id, ch[0])
        if not ok:
            await message.delete()

            buttons = [[InlineKeyboardButton(text=f"Подписаться {c[0]}", url=f"https://t.me/{c[0].replace('@','')}")] for c in channels]
            buttons.append([InlineKeyboardButton(text="VIP подписка", callback_data="vip_info")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)

            warn_msg = await message.answer(
                f"{user.mention_html()}, подпишись на каналы.",
                reply_markup=markup
            )

            async with aiosqlite.connect(DB) as db:
                cursor = await db.execute(
                    "SELECT auto_delete FROM groups WHERE group_id=?",
                    (chat_id,)
                )
                row = await cursor.fetchone()

            if row and row[0] > 0:
                await auto_delete_message(chat_id, warn_msg.message_id, row[0])

            break
# ================= PRIVATE /start =================
@dp.message(F.chat.type=="private")
async def private_start(message: Message):
    if message.text == "/start":
        await message.answer(
            "Привет.\nЯ админ-бот.\n"
            "Удаляю сообщения тех, кто не подписан.\n"
            "Контролирую VIP и mute.\n"
            "Все команды доступны через OWNER_ID."
        )
# ================= OWNER COMMANDS =================
@dp.message(lambda m: m.text.startswith("/add_one"))
async def cmd_add_one(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts)<2:
        await message.answer("Использование: /add_one @username")
        return
    username = parts[1]
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM channels WHERE group_id=?", (message.chat.id,))
        count = (await cursor.fetchone())[0]
        if count>=3:
            await message.answer("Максимум 3 канала одновременно.")
            return
        await db.execute(
            "INSERT INTO channels(group_id, username, start_time) VALUES(?,?,?)",
            (message.chat.id, username, datetime.datetime.now().isoformat())
        )
        await db.commit()
    await message.answer(f"Канал {username} добавлен на проверку.")

@dp.message(lambda m: m.text.startswith("/auto_del"))
async def cmd_auto_del(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    seconds = parse_duration(parts[1])
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO groups(group_id, auto_delete) VALUES(?,?)", (message.chat.id, seconds))
        await db.commit()
    await message.answer(f"Автоудаление сообщений установлено на {seconds} секунд.")

@dp.message(lambda m: m.text.startswith("/status"))
async def cmd_status(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT username, start_time, end_time FROM channels WHERE group_id=?", (message.chat.id,))
        rows = await cursor.fetchall()
    if not rows:
        await message.answer("Никаких каналов на проверке.")
        return
    text = "Каналы на проверке:\n"
    for r in rows:
        text += f"{r[0]} | {r[1]} - {r[2] or '∞'}\n"
    await message.answer(text)
# ================= MAIN =================
async def main():
    await init_db()
    start_scheduler()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
# ================= VIP / VIP PLUS =================
@dp.message(lambda m: m.text.startswith("/add_VIP_global"))
async def cmd_add_vip_global(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts)<2:
        await message.answer("Использование: /add_VIP_global @username [7d/30d]")
        return
    user_id = int(parts[1].replace("@",""))
    seconds = parse_duration(parts[2]) if len(parts)>2 else None
    await add_vip(user_id, 0, "VIP_GLOBAL", seconds)
    await message.answer(f"VIP GLOBAL добавлен пользователю {user_id}")

@dp.message(lambda m: m.text.startswith("/add_VIP_local"))
async def cmd_add_vip_local(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts)<3:
        await message.answer("Использование: /add_VIP_local @group @username [7d/30d]")
        return
    # group и user
    group_id = int(parts[1].replace("@",""))
    user_id = int(parts[2].replace("@",""))
    seconds = parse_duration(parts[3]) if len(parts)>3 else None
    await add_vip(user_id, group_id, "VIP_LOCAL", seconds)
    await message.answer(f"VIP LOCAL добавлен пользователю {user_id} в группе {group_id}")

@dp.message(lambda m: m.text.startswith("/add_VIPPLUS_global"))
async def cmd_add_vipplus_global(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts)<2:
        await message.answer("Использование: /add_VIPPLUS_global @username [7d/30d]")
        return
    user_id = int(parts[1].replace("@",""))
    seconds = parse_duration(parts[2]) if len(parts)>2 else None
    await add_vip(user_id, 0, "VIPPLUS_GLOBAL", seconds)
    await message.answer(f"VIP PLUS GLOBAL добавлен пользователю {user_id}")

@dp.message(lambda m: m.text.startswith("/add_VIPPLUS_local"))
async def cmd_add_vipplus_local(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts)<3:
        await message.answer("Использование: /add_VIPPLUS_local @group @username [7d/30d]")
        return
    group_id = int(parts[1].replace("@",""))
    user_id = int(parts[2].replace("@",""))
    seconds = parse_duration(parts[3]) if len(parts)>3 else None
    await add_vip(user_id, group_id, "VIPPLUS_LOCAL", seconds)
    await message.answer(f"VIP PLUS LOCAL добавлен пользователю {user_id} в группе {group_id}")

@dp.message(lambda m: m.text.startswith("/del_VIP"))
async def cmd_del_vip(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts)<2:
        await message.answer("Использование: /del_VIP @username")
        return
    user_id = int(parts[1].replace("@",""))
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM vip WHERE user_id=? AND level LIKE 'VIP%'", (user_id,))
        await db.commit()
    await message.answer(f"VIP пользователь {user_id} удалён")

@dp.message(lambda m: m.text.startswith("/del_VIPPLUS"))
async def cmd_del_vipplus(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts)<2:
        await message.answer("Использование: /del_VIPPLUS @username")
        return
    user_id = int(parts[1].replace("@",""))
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM vip WHERE user_id=? AND level LIKE 'VIPPLUS%'", (user_id,))
        await db.commit()
    await message.answer(f"VIP PLUS пользователь {user_id} удалён")
# ================= MUTE MANAGEMENT =================
@dp.message(lambda m: m.text.startswith("/mute_status"))
async def cmd_mute_status(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id, end_time FROM mutes WHERE group_id=?", (message.chat.id,))
        rows = await cursor.fetchall()
    if not rows:
        await message.answer("В этой группе нет активных мутов.")
        return
    text = "Список мутов:\n"
    now_time = datetime.datetime.now()
    for user_id, end_time in rows:
        end_dt = datetime.datetime.fromisoformat(end_time)
        remaining = end_dt - now_time
        text += f"Пользователь {user_id} | до {format_dt(end_dt)} | осталось: {str(remaining).split('.')[0]}\n"
    await message.answer(text)

@dp.message(lambda m: m.text.startswith("/off_mute"))
async def cmd_off_mute(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts)<2:
        await message.answer("Использование: /off_mute @username")
        return
    user_id = int(parts[1].replace("@",""))
    chat_id = message.chat.id
    try:
        await bot.restrict_chat_member(chat_id, user_id, permissions=None)
    except:
        pass
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM mutes WHERE user_id=? AND group_id=?", (user_id, chat_id))
        await db.commit()
    await message.answer(f"Мут снят с пользователя {user_id}")

@dp.message(lambda m: m.text.startswith("/del_all_mute"))
async def cmd_del_all_mute(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    chat_id = message.chat.id
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id FROM mutes WHERE group_id=?", (chat_id,))
        rows = await cursor.fetchall()
        for (user_id,) in rows:
            try:
                await bot.restrict_chat_member(chat_id, user_id, permissions=None)
            except:
                pass
        await db.execute("DELETE FROM mutes WHERE group_id=?", (chat_id,))
        await db.commit()
    await message.answer("Все мюты сняты в этой группе.")
# ================= SCHEDULER MUTE CHECK =================
async def scheduler_mute_check():
    now_time = datetime.datetime.now()
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id, group_id, end_time FROM mutes")
        rows = await cursor.fetchall()
        for user_id, group_id, end_time in rows:
            end_dt = datetime.datetime.fromisoformat(end_time)
            if now_time > end_dt:
                try:
                    await bot.restrict_chat_member(group_id, user_id, permissions=None)
                except:
                    pass
                await db.execute("DELETE FROM mutes WHERE user_id=? AND group_id=?", (user_id, group_id))
        await db.commit()

# Добавляем в основной Scheduler
scheduler.add_job(lambda: asyncio.create_task(scheduler_mute_check()), "interval", seconds=30)

# ================= STATUS FULL =================
@dp.message(lambda m: m.text.startswith("/status"))
async def cmd_status_full(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    chat_id = message.chat.id
    text = f"<b>Статус группы {chat_id}</b>\n\n"

    async with aiosqlite.connect(DB) as db:
        # Каналы на проверке
        cursor = await db.execute("SELECT username, start_time, end_time FROM channels WHERE group_id=?", (chat_id,))
        channels = await cursor.fetchall()
        if channels:
            text += "<b>Каналы на проверке:</b>\n"
            for c in channels:
                text += f"{c[0]} | {c[1]} - {c[2] or '∞'}\n"
        else:
            text += "Нет каналов на проверке.\n"

        # VIP / VIP PLUS
        cursor = await db.execute("SELECT user_id, level, end_time FROM vip WHERE group_id=? OR group_id=0", (chat_id,))
        vips = await cursor.fetchall()
        if vips:
            text += "\n<b>VIP / VIP PLUS пользователи:</b>\n"
            for user_id, level, end_time in vips:
                text += f"{user_id} | {level} | до {end_time or '∞'}\n"
        else:
            text += "\nНет VIP пользователей.\n"

        # Активные мюты
        cursor = await db.execute("SELECT user_id, end_time FROM mutes WHERE group_id=?", (chat_id,))
        mutes = await cursor.fetchall()
        if mutes:
            text += "\n<b>Мюты:</b>\n"
            now_time = datetime.datetime.now()
            for user_id, end_time in mutes:
                end_dt = datetime.datetime.fromisoformat(end_time)
                remaining = end_dt - now_time
                text += f"{user_id} | до {format_dt(end_dt)} | осталось: {str(remaining).split('.')[0]}\n"
        else:
            text += "\nНет активных мутов.\n"

    # Кнопки для подписки на каналы (до 3)
    buttons = []
    for c in channels:
        buttons.append([InlineKeyboardButton(text=f"Подписаться {c[0]}", url=f"https://t.me/{c[0].replace('@','')}")])
    buttons.append([InlineKeyboardButton(text="VIP подписка", callback_data="vip_info")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(text, reply_markup=markup)
# ================= CHANNEL MANAGEMENT =================

# Добавление нескольких каналов сразу
@dp.message(lambda m: m.text.startswith("/add_channels"))
async def cmd_add_channels(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /add_channels @channel1 @channel2 ...")
        return
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM channels WHERE group_id=?", (message.chat.id,))
        count = (await cursor.fetchone())[0]
        for username in parts[1:]:
            if count >= 3:
                await message.answer("Максимум 3 канала одновременно.")
                break
            await db.execute(
                "INSERT INTO channels(group_id, username, start_time) VALUES(?,?,?)",
                (message.chat.id, username, datetime.datetime.now().isoformat())
            )
            count += 1
            await message.answer(f"Канал {username} добавлен на проверку.")
        await db.commit()

# Установка времени проверки для канала (например 6h/12h/1d)
@dp.message(lambda m: m.text.startswith("/add_time"))
async def cmd_add_time(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /add_time @channel 6h/12h/1d или конкретные даты")
        return
    username = parts[1]
    time_part = parts[2]

    # Проверка формата
    if "-" in time_part:  # например: 01.01.2026 12:00-02.01.2026 12:00
        try:
            start_str, end_str = time_part.split("-")
            start_dt = datetime.datetime.strptime(start_str.strip(), "%d.%m.%Y %H:%M")
            end_dt = datetime.datetime.strptime(end_str.strip(), "%d.%m.%Y %H:%M")
        except:
            await message.answer("Неверный формат даты. Пример: 01.01.2026 12:00-02.01.2026 12:00")
            return
    else:
        seconds = parse_duration(time_part)
        if not seconds:
            await message.answer("Неверный формат времени. Пример: 6h/12h/1d")
            return
        start_dt = datetime.datetime.now()
        end_dt = start_dt + datetime.timedelta(seconds=seconds)

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE channels SET start_time=?, end_time=? WHERE group_id=? AND username=?",
            (start_dt.isoformat(), end_dt.isoformat(), message.chat.id, username)
        )
        await db.commit()
    await message.answer(f"Канал {username} на проверке до {format_dt(end_dt)}")

# Удаление одного канала с проверки
@dp.message(lambda m: m.text.startswith("/del_one"))
async def cmd_del_one(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /del_one @channel")
        return
    username = parts[1]
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "DELETE FROM channels WHERE group_id=? AND username=?",
            (message.chat.id, username)
        )
        await db.commit()
    await message.answer(f"Канал {username} удалён с проверки.")

# Удаление всех каналов
@dp.message(lambda m: m.text.startswith("/del_all"))
async def cmd_del_all(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM channels WHERE group_id=?", (message.chat.id,))
        await db.commit()
    await message.answer("Все каналы сняты с проверки.")

# Выбор активной группы для OWNER
@dp.message(lambda m: m.text.startswith("/group"))
async def cmd_select_group(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /group @groupid")
        return
    group_id = int(parts[1].replace("@",""))
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO selected_group(owner_id, group_id) VALUES(?,?)", (OWNER_ID, group_id))
        await db.commit()
    await message.answer(f"Выбрана группа {group_id} для управления.")

# Уведомление OWNER при добавлении бота в группу
@dp.chat_member()
async def on_bot_added(event):
    if event.new_chat_member.user.id == (await bot.get_me()).id:
        try:
            await bot.send_message(OWNER_ID, f"Бот добавлен в группу: {event.chat.id} ({event.chat.title})")
        except:
            pass
# ================= CALLBACK BUTTONS =================
from aiogram.types import CallbackQuery

@dp.callback_query(lambda c: c.data == "vip_info")
async def callback_vip_info(call: CallbackQuery):
    # Преимущества VIP и VIP PLUS
    text = (
        "<b>VIP подписка</b>\n"
        "- Полное освобождение от проверки каналов\n"
        "- Доступ к закрытым функциям группы\n"
        "- Срок 7d или 30d (по выбору)\n\n"
        "<b>VIP PLUS подписка</b>\n"
        "- Все преимущества VIP\n"
        "- Глобальное действие во всех группах\n"
        "- Возможность участия в конкурсах и активностях\n"
        "- Срок 7d или 30d"
    )
    await call.message.edit_text(text, parse_mode="HTML")
    await call.answer()

# Функция для генерации кнопок подписки на каналы
def generate_channel_buttons(channels):
    buttons = []
    for c in channels:
        buttons.append([InlineKeyboardButton(
            text=f"Подписаться {c[0]}",
            url=f"https://t.me/{c[0].replace('@','')}"
        )])
    buttons.append([InlineKeyboardButton(text="VIP подписка", callback_data="vip_info")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Пример использования в group_handler и /status
# Когда сообщение удаляется или выводится статус:
# markup = generate_channel_buttons(channels)
# await message.answer("Подпишись на каналы:", reply_markup=markup)
