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
    FSInputFile
)
from aiogram.filters import CommandStart, Command
from openpyxl import Workbook
from openpyxl.styles import Font

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
CHANNELS = [c.strip() for c in os.getenv("CHANNELS", "").split(",") if c.strip()]
ADMIN_ID = int(os.getenv("ADMIN_ID", "6140962854"))

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

# ================= VOTING =================

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


# ================= DATABASE =================

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

    text = f"\n🏫 {sinf} sinf:\n"

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
                ws.append([f"{sinf} sinf", student, count, round(percent, 2)])

        ws.append([])
        ws.append(["Fan jami:", get_fan_total(fan)])

    filename = "natijalar.xlsx"
    wb.save(filename)
    return filename


# ================= SUBSCRIPTION =================

async def check_subscription(user_id):
    for channel in CHANNELS:
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

    if CHANNELS and not await check_subscription(message.from_user.id):

        buttons = []
        for channel in CHANNELS:
            buttons.append(
                [InlineKeyboardButton(
                    text=f"📢 {channel}",
                    url=f"https://t.me/{channel.replace('@','')}"
                )]
            )

        buttons.append(
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
        )

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            "❗ Iltimos kanallarga obuna bo‘ling:",
            reply_markup=kb
        )
        return

    if not get_start_time():
        start_voting()

    if voting_active():
        await message.answer(f"⏳ Qolgan vaqt: {get_remaining_time()}")
    else:
        await message.answer("❌ Ovoz berish yakunlangan.")

    await show_menu(message)


@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    await call.answer()
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await show_menu(call.message)
    else:
        await call.answer("❌ Hali obuna bo‘lmagansiz!", show_alert=True)


# ================= MENU =================

async def show_menu(message):
    buttons = []

    if voting_active():
        for fan in DATA:
            buttons.append(
                [InlineKeyboardButton(text=fan, callback_data=f"fan|{fan}")]
            )

    buttons.append(
        [InlineKeyboardButton(text="📊 Natijalar", callback_data="results")]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📚 Fan tanlang:", reply_markup=kb)


# ================= FAN =================

@dp.callback_query(F.data.startswith("fan|"))
async def fan_handler(call: CallbackQuery):
    await call.answer()

    fan = call.data.split("|")[1]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{sinf} sinf", callback_data=f"sinf|{fan}|{sinf}")]
            for sinf in DATA[fan]
        ]
    )

    await call.message.edit_text("🏫 Sinf tanlang:", reply_markup=kb)


# ================= SINF =================

@dp.callback_query(F.data.startswith("sinf|"))
async def sinf_handler(call: CallbackQuery):
    await call.answer()

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
    await call.answer()

    _, fan, sinf, student = call.data.split("|")

    if not voting_active():
        await call.message.answer("❌ Ovoz berish yakunlandi.")
        return

    success = add_vote(call.from_user.id, fan, sinf, student)
    result_text = get_results_text(fan, sinf)

    if not success:
        await call.message.answer("❌ Siz allaqachon ovoz bergansiz!\n" + result_text)
        return

    await call.message.answer("✅ Ovozingiz qabul qilindi!\n" + result_text)


# ================= RESULTS =================

@dp.callback_query(F.data == "results")
async def results_handler(call: CallbackQuery):
    await call.answer()

    text = "📊 NATIJALAR\n"

    for fan in DATA:
        text += f"\n{fan}:\n"
        for sinf in DATA[fan]:
            text += get_results_text(fan, sinf)

    text += f"\n🗳 Umumiy ovoz: {get_total_votes_all()}"

    await call.message.answer(text)


# ================= EXCEL =================

@dp.message(Command("excel"))
async def send_excel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz admin emassiz.")
        return

    filename = generate_excel()
    file = FSInputFile(filename)

    await message.answer_document(file, caption="📊 Excel natijalar")


# ================= RUN =================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
