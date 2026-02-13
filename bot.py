import os
import asyncio
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNELS = os.getenv("CHANNELS", "").split(",")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= DATABASE =================

conn = sqlite3.connect("votes.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    user_id INTEGER,
    fan TEXT,
    sinf TEXT,
    student TEXT,
    UNIQUE(user_id, fan, sinf)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    start_time TEXT
)
""")

conn.commit()

# ================= DATA =================
# BU YERGA O'ZINGNI RO'YXATNI YOZASAN

DATA = {
    "Matematika": {
        "1-6": ["Ali", "Vali", "Hasan"],
        "7-11": ["Sardor", "Jamshid", "Bekzod"]
    },
    "English": {
        "1-6": ["Anna", "Madina"],
        "7-11": ["Aziza", "Shahzod"]
    }
}

# ================= FUNCTIONS =================

def start_voting():
    cursor.execute("DELETE FROM settings")
    cursor.execute("INSERT INTO settings (start_time) VALUES (?)",
                   (datetime.now().isoformat(),))
    conn.commit()

def get_start_time():
    cursor.execute("SELECT start_time FROM settings LIMIT 1")
    row = cursor.fetchone()
    return datetime.fromisoformat(row[0]) if row else None

def voting_active():
    start = get_start_time()
    if not start:
        return False
    return datetime.now() < start + timedelta(days=1)

def add_vote(user_id, fan, sinf, student):
    try:
        cursor.execute("INSERT INTO votes VALUES (?, ?, ?, ?)",
                       (user_id, fan, sinf, student))
        conn.commit()
        return True
    except:
        return False

def get_results(fan, sinf):
    cursor.execute("""
    SELECT student, COUNT(*) FROM votes
    WHERE fan=? AND sinf=?
    GROUP BY student
    ORDER BY COUNT(*) DESC
    """, (fan, sinf))
    return cursor.fetchall()

async def check_subscription(user_id):
    for channel in CHANNELS:
        channel = channel.strip()
        if channel == "":
            continue
        member = await bot.get_chat_member(channel, user_id)
        if member.status in ["left", "kicked"]:
            return False
    return True

# ================= START =================

@dp.message(CommandStart())
async def start_handler(message: Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("❗ Iltimos 2 ta kanalga obuna bo‘ling va qayta /start bosing.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=fan, callback_data=f"fan|{fan}")]
            for fan in DATA.keys()
        ] + [[InlineKeyboardButton(text="📊 Natijalar", callback_data="results")]]
    )

    if not voting_active():
        await message.answer(
            "❌ Ovoz berish yakunlandi.\n📊 Natijalarni ko‘rishingiz mumkin:",
            reply_markup=kb
        )
        return

    await message.answer("Fan tanlang:", reply_markup=kb)

# ================= FAN =================

@dp.callback_query(F.data.startswith("fan|"))
async def fan_handler(call: CallbackQuery):
    fan = call.data.split("|")[1]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=sinf, callback_data=f"sinf|{fan}|{sinf}")]
            for sinf in DATA[fan].keys()
        ]
    )

    await call.message.edit_text("Sinf tanlang:", reply_markup=kb)

# ================= SINF =================

@dp.callback_query(F.data.startswith("sinf|"))
async def sinf_handler(call: CallbackQuery):
    _, fan, sinf = call.data.split("|")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=st, callback_data=f"vote|{fan}|{sinf}|{st}")]
            for st in DATA[fan][sinf]
        ]
    )

    await call.message.edit_text("O‘quvchini tanlang:", reply_markup=kb)

# ================= VOTE =================

@dp.callback_query(F.data.startswith("vote|"))
async def vote_handler(call: CallbackQuery):
    _, fan, sinf, student = call.data.split("|")

    if not voting_active():
        await call.message.answer("❌ Ovoz berish yakunlandi.")
        return

    success = add_vote(call.from_user.id, fan, sinf, student)

    if not success:
        await call.message.answer("❌ Siz bu bo‘limda allaqachon ovoz bergansiz!")
        return

    results = get_results(fan, sinf)
    total_votes = sum(count for _, count in results)

    text = "✅ Ovozingiz muvaffaqiyatli qabul qilindi!\n\n📊 Joriy natijalar:\n"

    for i, (s, count) in enumerate(results, 1):
        percent = (count / total_votes) * 100 if total_votes > 0 else 0
        text += f"{i}. {s} — {count} ta ({percent:.1f}%)\n"

    await call.message.answer(text)

# ================= RESULTS =================

@dp.callback_query(F.data == "results")
async def results_handler(call: CallbackQuery):
    text = "📊 NATIJALAR:\n"

    for fan in DATA:
        for sinf in DATA[fan]:
            text += f"\n🏫 {fan} ({sinf})\n"

            results = get_results(fan, sinf)
            total_votes = sum(count for _, count in results)

            if not results:
                text += "Ovozlar yo‘q.\n"
                continue

            for i, (s, count) in enumerate(results, 1):
                percent = (count / total_votes) * 100 if total_votes > 0 else 0
                text += f"{i}. {s} — {count} ta ({percent:.1f}%)\n"

    await call.message.answer(text)

# ================= ADMIN =================

@dp.message(Command("start_voting"))
async def admin_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        start_voting()
        await message.answer("✅ Ovoz berish boshlandi (1 kun)")

# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
