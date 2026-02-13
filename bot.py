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
from aiogram.filters import CommandStart

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
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

# ================= VOTING TIME =================

VOTING_DURATION_DAYS = 1


def start_voting():
    cursor.execute("DELETE FROM settings")
    cursor.execute(
        "INSERT INTO settings (start_time) VALUES (?)",
        (datetime.now().isoformat(),)
    )
    conn.commit()


def get_start_time():
    cursor.execute("SELECT start_time FROM settings LIMIT 1")
    row = cursor.fetchone()
    return datetime.fromisoformat(row[0]) if row else None


def voting_active():
    start = get_start_time()
    if not start:
        return False
    return datetime.now() < start + timedelta(days=VOTING_DURATION_DAYS)


def get_remaining_time():
    start = get_start_time()
    if not start:
        return None

    end_time = start + timedelta(days=VOTING_DURATION_DAYS)
    remaining = end_time - datetime.now()

    if remaining.total_seconds() <= 0:
        return None

    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes = remainder // 60

    return f"{days} kun {hours} soat {minutes} minut"


# ================= DATABASE FUNCTIONS =================

def add_vote(user_id, fan, sinf, student):
    try:
        cursor.execute(
            "INSERT INTO votes VALUES (?, ?, ?, ?)",
            (user_id, fan, sinf, student)
        )
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


def get_total_votes_all():
    cursor.execute("SELECT COUNT(*) FROM votes")
    return cursor.fetchone()[0]


def get_fan_total(fan):
    cursor.execute("SELECT COUNT(*) FROM votes WHERE fan=?", (fan,))
    return cursor.fetchone()[0]


def get_results_text(fan, sinf):
    results = get_results(fan, sinf)
    result_dict = {student: count for student, count in results}
    total_votes = sum(result_dict.values())

    text = f"\n🏫 {sinf}:\n"

    for i, student in enumerate(DATA[fan][sinf], 1):
        count = result_dict.get(student, 0)
        percent = (count / total_votes) * 100 if total_votes else 0
        text += f"{i}. {student} — {count} ta ({percent:.1f}%)\n"

    text += f"🗳 Jami ovoz: {total_votes}\n"
    return text


# ================= SUBSCRIPTION =================

async def check_subscription(user_id):
    for channel in CHANNELS:
        channel = channel.strip()
        if not channel:
            continue
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True


# ================= START =================

@dp.message(CommandStart())
async def start_handler(message: Message):

    # Kanal tekshirish
    if not await check_subscription(message.from_user.id):

        buttons = []

        for channel in CHANNELS:
            channel = channel.strip()
            if channel:
                buttons.append(
                    [InlineKeyboardButton(
                        text="📢 Kanalga obuna bo‘lish",
                        url=f"https://t.me/{channel.replace('@','')}"
                    )]
                )

        buttons.append([
            InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")
        ])

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            "❗ Iltimos quyidagi kanallarga obuna bo‘ling:",
            reply_markup=kb
        )
        return

    start_time = get_start_time()

    if not start_time:
        start_voting()
        remaining = get_remaining_time()
        await message.answer(
            f"✅ Ovoz berish boshlandi!\n\n⏳ Qolgan vaqt: {remaining}"
        )
    else:
        if voting_active():
            remaining = get_remaining_time()
            await message.answer(
                f"ℹ️ Ovoz berish allaqachon boshlangan.\n\n⏳ Qolgan vaqt: {remaining}"
            )
        else:
            await message.answer("❌ Ovoz berish yakunlangan.")

    await show_menu(message)


# ================= CHECK BUTTON =================

@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await show_menu(call.message)
    else:
        await call.answer("❌ Hali obuna bo‘lmagansiz!", show_alert=True)


# ================= MAIN MENU =================

async def show_menu(message):

    if voting_active():
        buttons = [
            [InlineKeyboardButton(text=fan, callback_data=f"fan|{fan}")]
            for fan in DATA.keys()
        ]
    else:
        buttons = []

    buttons.append(
        [InlineKeyboardButton(text="📊 Natijalar", callback_data="results")]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if voting_active():
        await message.answer("📚 Fan tanlang:", reply_markup=kb)
    else:
        await message.answer(
            "❌ Ovoz berish yakunlangan.\n📊 Natijalarni ko‘rishingiz mumkin:",
            reply_markup=kb
        )


# ================= FAN =================

@dp.callback_query(F.data.startswith("fan|"))
async def fan_handler(call: CallbackQuery):
    if not voting_active():
        await call.answer("❌ Ovoz berish tugagan!", show_alert=True)
        return

    fan = call.data.split("|")[1]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=sinf,
                callback_data=f"sinf|{fan}|{sinf}"
            )]
            for sinf in DATA[fan].keys()
        ]
    )

    await call.message.edit_text("🏫 Sinf tanlang:", reply_markup=kb)


# ================= SINF =================

@dp.callback_query(F.data.startswith("sinf|"))
async def sinf_handler(call: CallbackQuery):
    _, fan, sinf = call.data.split("|")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=student,
                callback_data=f"vote|{fan}|{sinf}|{student}"
            )]
            for student in DATA[fan][sinf]
        ]
    )

    await call.message.edit_text("👨‍🎓 O‘quvchini tanlang:", reply_markup=kb)


# ================= VOTE =================

@dp.callback_query(F.data.startswith("vote|"))
async def vote_handler(call: CallbackQuery):
    _, fan, sinf, student = call.data.split("|")

    if not voting_active():
        await call.message.answer("❌ Ovoz berish yakunlandi.")
        return

    success = add_vote(call.from_user.id, fan, sinf, student)
    result_text = get_results_text(fan, sinf)

    if not success:
        await call.message.answer(
            "❌ Siz allaqachon ovoz bergansiz!\n" + result_text
        )
        return

    await call.message.answer(
        "✅ Ovozingiz qabul qilindi!\n" + result_text
    )


# ================= RESULTS MENU =================

@dp.callback_query(F.data == "results")
async def results_menu(call: CallbackQuery):

    total = get_total_votes_all()

    buttons = [
        [InlineKeyboardButton(text=fan, callback_data=f"show_result|{fan}")]
        for fan in DATA.keys()
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await call.message.answer(
        f"📊 NATIJALAR BO‘LIMI\n\n🗳 Barcha fanlardan jami ovoz: {total}\n\nFanni tanlang:",
        reply_markup=kb
    )


# ================= FAN RESULTS =================

@dp.callback_query(F.data.startswith("show_result|"))
async def show_fan_results(call: CallbackQuery):

    fan = call.data.split("|")[1]

    text = f"📊 {fan} fanidan natijalar:\n"

    for sinf in DATA[fan]:
        text += get_results_text(fan, sinf)

    fan_total = get_fan_total(fan)
    text += f"\n🗳 {fan} fanidan jami ovoz: {fan_total}"

    await call.message.answer(text)


# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
