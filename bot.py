import os
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ==============================
# CONFIG (Railway ENV dan olinadi)
# ==============================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNELS = os.getenv("CHANNELS").split(",")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ==============================
# DATABASE
# ==============================

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

# ==============================
# DATA
# ==============================

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

# ==============================
# FUNKSIYALAR
# ==============================

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
    """, (fan, sinf))
    return cursor.fetchall()

async def check_subscription(user_id):
    for channel in CHANNELS:
        member = await bot.get_chat_member(channel.strip(), user_id)
        if member.status in ["left", "kicked"]:
            return False
    return True

# ==============================
# KEYBOARDS
# ==============================

def fan_keyboard():
    kb = InlineKeyboardMarkup()
    for fan in DATA:
        kb.add(InlineKeyboardButton(fan, callback_data=f"fan_{fan}"))
    kb.add(InlineKeyboardButton("📊 Natijalar", callback_data="results"))
    return kb

def sinf_keyboard(fan):
    kb = InlineKeyboardMarkup()
    for sinf in DATA[fan]:
        kb.add(InlineKeyboardButton(sinf, callback_data=f"sinf_{fan}_{sinf}"))
    return kb

def student_keyboard(fan, sinf):
    kb = InlineKeyboardMarkup()
    for student in DATA[fan][sinf]:
        kb.add(InlineKeyboardButton(student,
            callback_data=f"vote_{fan}_{sinf}_{student}"))
    return kb

# ==============================
# HANDLERS
# ==============================

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer(
            "❗ Iltimos 2 ta kanalga obuna bo‘ling va qayta /start bosing."
        )
        return

    if not voting_active():
        await message.answer(
            "❌ Ovoz berish yakunlandi.\n📊 Natijalarni ko‘rish uchun 'Natijalar' tugmasini bosing.",
            reply_markup=fan_keyboard()
        )
        return

    await message.answer("Fan tanlang:", reply_markup=fan_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("fan_"))
async def fan_selected(call: types.CallbackQuery):
    fan = call.data.split("_")[1]
    await call.message.edit_text("Sinf tanlang:",
                                 reply_markup=sinf_keyboard(fan))

@dp.callback_query_handler(lambda c: c.data.startswith("sinf_"))
async def sinf_selected(call: types.CallbackQuery):
    _, fan, sinf = call.data.split("_")
    await call.message.edit_text("O‘quvchini tanlang:",
                                 reply_markup=student_keyboard(fan, sinf))

@dp.callback_query_handler(lambda c: c.data.startswith("vote_"))
async def vote_handler(call: types.CallbackQuery):
    _, fan, sinf, student = call.data.split("_")

    if not voting_active():
        await call.message.answer("❌ Ovoz berish yakunlandi.")
        return

    success = add_vote(call.from_user.id, fan, sinf, student)

    if not success:
        await call.message.answer("❌ Siz bu bo‘limda allaqachon ovoz bergansiz!")
        return

    results = get_results(fan, sinf)

    text = "✅ Ovozingiz qabul qilindi!\n\n📊 Natijalar:\n"
    for s, count in results:
        text += f"{s} — {count} ta\n"

    await call.message.answer(text)

@dp.callback_query_handler(lambda c: c.data == "results")
async def results_handler(call: types.CallbackQuery):
    text = "📊 Natijalar:\n\n"
    for fan in DATA:
        for sinf in DATA[fan]:
            text += f"\n{fan} ({sinf})\n"
            results = get_results(fan, sinf)
            for s, count in results:
                text += f"{s} — {count} ta\n"
    await call.message.answer(text)

@dp.message_handler(commands=['start_voting'])
async def admin_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        start_voting()
        await message.answer("✅ Ovoz berish boshlandi (1 kun)")

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
