import os
import asyncio
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from openpyxl import Workbook
from openpyxl.styles import Font

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
CHANNELS = os.getenv("CHANNELS", "").split(",")
ADMIN_ID = 6140962854

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

VOTING_DURATION_MINUTES = 3


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
    return datetime.now() < start + timedelta(minutes=VOTING_DURATION_MINUTES)


def get_remaining_time():
    start = get_start_time()
    if not start:
        return None

    end_time = start + timedelta(minutes=VOTING_DURATION_MINUTES)
    remaining = end_time - datetime.now()

    if remaining.total_seconds() <= 0:
        return None

    minutes, seconds = divmod(int(remaining.total_seconds()), 60)
    return f"{minutes} minut {seconds} sekund"

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

    for student in DATA[fan][sinf]:
        count = result_dict.get(student, 0)
        percent = (count / total_votes) * 100 if total_votes else 0
        text += f"{student} — {count} ta ({percent:.1f}%)\n"

    text += f"🗳 Jami: {total_votes}\n"
    return text

# ================= EXCEL =================

def generate_excel():
    wb = Workbook()
    wb.remove(wb.active)

    for fan in DATA:
        ws = wb.create_sheet(title=fan)

        ws.append(["Sinf", "O‘quvchi", "Ovoz", "Foiz (%)"])
        for cell in ws[1]:
            cell.font = Font(bold=True)

        for sinf in DATA[fan]:
            results = get_results(fan, sinf)
            result_dict = {student: count for student, count in results}
            total = sum(result_dict.values())

            for student in DATA[fan][sinf]:
                count = result_dict.get(student, 0)
                percent = (count / total * 100) if total else 0

                ws.append([sinf, student, count, round(percent, 2)])

        ws.append([])
        ws.append(["Fan jami:", get_fan_total(fan)])

    filename = "natijalar.xlsx"
    wb.save(filename)
    return filename

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

    if not await check_subscription(message.from_user.id):
        await message.answer("❗ Kanallarga obuna bo‘ling.")
        return

    start_time = get_start_time()

    if not start_time:
        start_voting()
        remaining = get_remaining_time()
        await message.answer(f"✅ Ovoz berish boshlandi!\n⏳ {remaining}")
    else:
        if voting_active():
            await message.answer(f"⏳ Qolgan vaqt: {get_remaining_time()}")
        else:
            await message.answer("❌ Ovoz berish yakunlangan.")

    await show_menu(message)

# ================= MENU =================

async def show_menu(message):
    buttons = []

    if voting_active():
        for fan in DATA:
            buttons.append([InlineKeyboardButton(text=fan, callback_data=f"fan|{fan}")])

    buttons.append([InlineKeyboardButton(text="📊 Natijalar", callback_data="results")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Tanlang:", reply_markup=kb)

# ================= EXCEL COMMAND =================

@dp.message(F.text == "/excel")
async def send_excel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz admin emassiz.")
        return

    file = generate_excel()
    await message.answer_document(file, caption="📊 Excel natijalar")

# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
