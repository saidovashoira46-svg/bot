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

conn.commit()

# ================= DATA (NAMUNA) =================
# Qolgan fanlaringni shu formatda qo‘shib ketaverasan

DATA = {
    "ENGLISH": {
        "1-6 SINF": [
            {"name": "RAZMATOV ABDULLOX", "filial": "Kids 2", "maktab": 3, "sinf": 7},
            {"name": "UMARALIYEV AXAD", "filial": "Dostobod", "maktab": 11, "sinf": 5},
            {"name": "Tolibjonov Jamshid", "filial": "Kids 1"},
            {"name": "Yo'ldosheva Hadicha", "filial": "Chinoz", "maktab": 6, "sinf": 4},
            {"name": "Muhammadiev Jamoliddin", "filial": "Xalqabod", "maktab": 56, "sinf": 4},
            {"name": "RAIMOV SHAXBOZ", "filial": "Olmazor", "maktab": 29, "sinf": 5},
            {"name": "ABDUJALLOV BUNYOD", "filial": "Gulbahor", "maktab": 1, "sinf": 5},
            {"name": "ZAKIRBAYEV SHAXBOZBEK", "filial": "Kasblar", "maktab": 6, "sinf": 4},
            {"name": "XASANOVA DIYORA", "filial": "Paxtazor", "maktab": 32, "sinf": 6},
            {"name": "EGAMBERDIYEVA GO'ZAL", "filial": "Niyazbosh", "maktab": 10, "sinf": 7},
            {"name": "TAGIROV DIYORBEK", "filial": "Mevazor", "maktab": 51, "sinf": 5},
        ],

        "7-11 SINF": [
            {"name": "ABDUQODIROVA ASAL", "filial": "Kids 2", "maktab": 3, "sinf": 8},
            {"name": "KOSIMBEKOV SULTONBEK", "filial": "Dostobod", "maktab": 11, "sinf": 10},
            {"name": "Tolibjonov Davron", "filial": "Kids 1"},
            {"name": "Murodov Azimjon", "filial": "Chinoz", "sinf": 8},
            {"name": "Davudjanova Shahzoda", "filial": "Xalqabod", "maktab": 28, "sinf": 10},
            {"name": "OCHILOVA DILNURA", "filial": "Olmazor", "maktab": 9, "sinf": 11},
            {"name": "NURIDINOV ASADBEK", "filial": "Gulbahor", "maktab": 45, "sinf": 9},
            {"name": "ABDUSATTOROV ABDUMALIK", "filial": "Kasblar", "maktab": 6, "sinf": 9},
            {"name": "HUSNIDDINOV JO'RABEK", "filial": "Paxtazor", "maktab": 5, "sinf": 11},
            {"name": "MUXIDDINOVA MUQADDAS", "filial": "Niyazbosh", "maktab": 0, "sinf": 9},
            {"name": "RASULJONOV SHOXRUX", "filial": "Mevazor", "maktab": 51, "sinf": 6},
        ]
    },
    "RUS TILI": {
        "1-6 SINF": [
            {"name": "ABDURAXMONOV UMIDJON", "filial": "Kids 2", "maktab": 5, "sinf": 3},
            {"name": "AKBARALIYEV SHOXJAHON", "filial": "Dostobod", "maktab": 24, "sinf": 6},
            {"name": "Abdurashidova Asal", "filial": "Kids 1"},
            {"name": "Qurolova Xonzoda", "filial": "Chinoz", "maktab": 18, "sinf": 6},
            {"name": "Azatov Ahmadali", "filial": "Xalqabod", "maktab": 28, "sinf": 8},
            {"name": "ARIKULOVA MUXSINA", "filial": "Olmazor", "maktab": 10, "sinf": 3},
            {"name": "MAMADIYOROV SALOXIDIN", "filial": "Gulbahor", "maktab": 40, "sinf": 6},
            {"name": "NISHANALIYEVA KUMUSHBIBI", "filial": "Kasblar", "maktab": 6, "sinf": 3},
            {"name": "XUDOYBERGANOVA ZAXRO", "filial": "Niyazbosh", "maktab": 27, "sinf": 8},
            {"name": "TURDIBOYEVA MADENA", "filial": "Mevazor", "maktab": 51, "sinf": 5},
        ],
        "7-11 SINF": [
            {"name": "RUSTAMJONOVA MUSLIMA", "filial": "Kids 2", "maktab": 42, "sinf": 8},
            {"name": "UMIRKULOVA FOTIMA", "filial": "Dostobod", "maktab": 40, "sinf": 11},
            {"name": "Asrolxonova Iroda", "filial": "Chinoz", "maktab": 26, "sinf": 10},
            {"name": "Ergashov Behrzu", "filial": "Xalqabod", "maktab": 28, "sinf": 10},
            {"name": "SOYIBJONOV JASUR", "filial": "Olmazor", "maktab": 9, "sinf": 11},
            {"name": "ERNAZOROVA MUSLIMA", "filial": "Gulbahor", "maktab": 1, "sinf": 8},
            {"name": "QODIRJONOV MUXAMMADORIF", "filial": "Kasblar", "maktab": 6, "sinf": 7},
            {"name": "SARBAYEV SUNNAT", "filial": "Paxtazor", "maktab": 50, "sinf": 7},
            {"name": "BAXTIYOROVA MUSHTARIY", "filial": "Niyazbosh", "maktab": 16, "sinf": 7},
            {"name": "TURSUNBOYEVA BAXTIGUL", "filial": "Mevazor", "maktab": 6, "sinf": 8},
        ]
    },
}


# ================= VOTING =================

VOTING_DURATION_HOURS = 24
START_TIME = datetime.now()

def voting_active():
    return datetime.now() < START_TIME + timedelta(hours=VOTING_DURATION_HOURS)

def get_remaining_time():
    remaining = (START_TIME + timedelta(hours=VOTING_DURATION_HOURS)) - datetime.now()
    if remaining.total_seconds() <= 0:
        return "0 soat"
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    return f"{hours} soat {minutes} minut"



# ================= DATABASE FUNCS =================

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
        SELECT student, COUNT(*) 
        FROM votes 
        WHERE fan=? AND sinf=? 
        GROUP BY student
    """, (fan, sinf))
    return cursor.fetchall()


def get_results_text(fan, sinf):
    results = get_results(fan, sinf)
    result_dict = {student: count for student, count in results}
    total = sum(result_dict.values())

    text = f"\n📊 {fan} — {sinf}\n\n"

    for student in DATA[fan][sinf]:
        name = student["name"]
        filial = student.get("filial", "")

        count = result_dict.get(name, 0)
        percent = (count / total * 100) if total else 0

        text += f"{name} ({filial}) — {count} ta ({percent:.1f}%)\n"

    text += f"\n🗳 Jami: {total}\n"
    return text


# ================= EXCEL =================

def generate_excel():
    wb = Workbook()
    wb.remove(wb.active)

    for fan in DATA:
        ws = wb.create_sheet(title=fan)
        ws.append(["Sinf", "O‘quvchi", "Filial", "Ovoz", "Foiz"])

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for sinf in DATA[fan]:
            results = get_results(fan, sinf)
            result_dict = {student: count for student, count in results}
            total = sum(result_dict.values())

            for student in DATA[fan][sinf]:
                name = student["name"]
                filial = student.get("filial", "")

                count = result_dict.get(name, 0)
                percent = (count / total * 100) if total else 0

                ws.append([sinf, name, filial, count, round(percent, 2)])

    filename = "natijalar.xlsx"
    wb.save(filename)
    return filename


# ================= START =================

@dp.message(CommandStart())
async def start_handler(message: Message):
    if voting_active():
        await message.answer(f"⏳ Qolgan vaqt: {get_remaining_time()}")
    else:
        await message.answer("❌ Ovoz berish tugagan.")

    await show_menu(message)


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

    await message.answer(
        "📚 Fan tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# ================= FAN =================

@dp.callback_query(F.data.startswith("fan|"))
async def fan_handler(call: CallbackQuery):
    await call.answer()
    fan = call.data.split("|")[1]

    buttons = [
        [InlineKeyboardButton(text=sinf, callback_data=f"sinf|{fan}|{sinf}")]
        for sinf in DATA[fan]
    ]

    await call.message.edit_text(
        "🏫 Sinf tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# ================= SINF =================

@dp.callback_query(F.data.startswith("sinf|"))
async def sinf_handler(call: CallbackQuery):
    await call.answer()

    _, fan, sinf = call.data.split("|")

    buttons = []

    for student in DATA[fan][sinf]:
        name = student["name"]
        filial = student.get("filial", "")
        maktab = student.get("maktab")
        sinf_num = student.get("sinf")

        # 👇 BARCHA HOLATLARNI QAMRAYDI
        parts = [f"{name}"]

        if filial:
            parts.append(f"({filial})")

        if maktab:
            parts.append(f"{maktab}-m")

        if sinf_num:
            parts.append(f"{sinf_num}-s")

        display = " ".join(parts)

        buttons.append(
            [InlineKeyboardButton(
                text=display,
                callback_data=f"vote|{fan}|{sinf}|{name}"
            )]
        )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await call.message.edit_text("👨‍🎓 O‘quvchini tanlang:", reply_markup=kb)


# ================= VOTE =================

@dp.callback_query(F.data.startswith("vote|"))
async def vote_handler(call: CallbackQuery):
    await call.answer()

    _, fan, sinf, student = call.data.split("|")

    if not voting_active():
        await call.message.answer("❌ Ovoz berish tugagan.")
        return

    success = add_vote(call.from_user.id, fan, sinf, student)

    if not success:
        await call.message.answer("❌ Siz allaqachon ovoz bergansiz!")
        return

    await call.message.answer("✅ Ovozingiz qabul qilindi!")
    await call.message.answer(get_results_text(fan, sinf))


# ================= RESULTS =================

@dp.callback_query(F.data == "results")
async def results_handler(call: CallbackQuery):
    await call.answer()

    buttons = [
        [InlineKeyboardButton(text=fan, callback_data=f"resfan|{fan}")]
        for fan in DATA
    ]

    await call.message.edit_text(
        "📊 Qaysi fan?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data.startswith("resfan|"))
async def results_fan(call: CallbackQuery):
    await call.answer()
    fan = call.data.split("|")[1]

    buttons = [
        [InlineKeyboardButton(text=sinf, callback_data=f"ressinf|{fan}|{sinf}")]
        for sinf in DATA[fan]
    ]

    await call.message.edit_text(
        f"📊 {fan}\nSinf tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data.startswith("ressinf|"))
async def results_sinf(call: CallbackQuery):
    await call.answer()
    _, fan, sinf = call.data.split("|")

    await call.message.edit_text(get_results_text(fan, sinf))


# ================= EXCEL =================

@dp.message(Command("excel"))
async def send_excel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz admin emassiz.")
        return

    filename = generate_excel()
    await message.answer_document(FSInputFile(filename))


# ================= RUN =================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
