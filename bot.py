"""
jobs.ge Telegram Bot — вакансии и резюме с оплатой Telegram Stars.
Stack: aiogram 3.x, aiosqlite, Pillow.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    BufferedInputFile,
    PreCheckoutQuery,
    Message,
)
from aiogram.enums import ParseMode

from instagram import generate_post_image, generate_caption, publish_post, delete_post

# ────────── Config ──────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8775633587:AAHdvdHUyA59ZLI5Ut1LlZ6bxYCnYtKA7lU")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
DB_PATH = os.getenv("DB_PATH", "/data/jobs.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ────────── i18n ──────────
TEXTS: dict[str, dict[str, str]] = {
    "choose_lang": {
        "ge": "აირჩიეთ ენა:",
        "ru": "Выберите язык:",
        "en": "Choose language:",
    },
    "main_menu": {
        "ge": "რა გსურთ?",
        "ru": "Что вы ищете?",
        "en": "What are you looking for?",
    },
    "looking_job": {"ge": "🔍 ვეძებ სამუშაოს", "ru": "🔍 Ищу работу", "en": "🔍 Looking for a job"},
    "looking_employee": {"ge": "🏢 ვეძებ თანამშრომელს", "ru": "🏢 Ищу сотрудника", "en": "🏢 Looking for an employee"},
    # resume flow
    "ask_name": {"ge": "შეიყვანეთ თქვენი სახელი:", "ru": "Введите ваше имя:", "en": "Enter your name:"},
    "ask_profession": {"ge": "პროფესია / სპეციალობა:", "ru": "Профессия / специальность:", "en": "Profession / specialty:"},
    "ask_experience": {"ge": "გამოცდილება (წლები):", "ru": "Опыт работы (лет):", "en": "Work experience (years):"},
    "ask_skills": {"ge": "უნარები:", "ru": "Навыки:", "en": "Skills:"},
    "ask_salary": {"ge": "სასურველი ხელფასი (ან 'შეთანხმებით'):", "ru": "Желаемая зарплата (или 'по договорённости'):", "en": "Desired salary (or 'negotiable'):"},
    "ask_contact": {"ge": "კონტაქტი (ტელეფონი ან @username):", "ru": "Контакт (телефон или @username):", "en": "Contact (phone or @username):"},
    "ask_city": {"ge": "ქალაქი:", "ru": "Город:", "en": "City:"},
    # job flow
    "ask_company": {"ge": "კომპანიის სახელი:", "ru": "Название компании:", "en": "Company name:"},
    "ask_position": {"ge": "ვაკანსია / თანამდებობა:", "ru": "Вакансия / должность:", "en": "Position / vacancy:"},
    "ask_duties": {"ge": "მოვალეობების აღწერა:", "ru": "Описание обязанностей:", "en": "Job description:"},
    "ask_requirements": {"ge": "მოთხოვნები:", "ru": "Требования:", "en": "Requirements:"},
    "ask_employment": {"ge": "დასაქმების ტიპი (სრული/ნაწილობრივი/დისტანციური):", "ru": "Тип занятости (полная/частичная/удалённая):", "en": "Employment type (full/part/remote):"},
    # common
    "preview_title": {"ge": "📋 გადახედეთ:", "ru": "📋 Превью:", "en": "📋 Preview:"},
    "pay_publish": {"ge": "💳 გადახდა და გამოქვეყნება", "ru": "💳 Оплатить и опубликовать", "en": "💳 Pay & Publish"},
    "cancel": {"ge": "❌ გაუქმება", "ru": "❌ Отмена", "en": "❌ Cancel"},
    "published": {"ge": "✅ გამოქვეყნდა! 48 საათის შემდეგ ავტომატურად წაიშლება.", "ru": "✅ Опубликовано! Автоудаление через 48ч.", "en": "✅ Published! Auto-delete in 48h."},
    "cancelled": {"ge": "გაუქმებულია.", "ru": "Отменено.", "en": "Cancelled."},
    "too_long": {"ge": "⚠️ ტექსტი ძალიან გრძელია! მაქსიმუმ {max} სიმბოლო. ახლა: {cur}. სცადე თავიდან.", "ru": "⚠️ Слишком длинный текст! Максимум {max} символов. Сейчас: {cur}. Попробуй ещё раз.", "en": "⚠️ Text too long! Maximum {max} characters. Current: {cur}. Try again."},
    "post_expired": {"ge": "⏰ თქვენი პოსტი ვადაგასულია.", "ru": "⏰ Ваш пост истёк.", "en": "⏰ Your post has expired."},
    "payment_title_resume": {"ge": "რეზიუმე გამოქვეყნება", "ru": "Публикация резюме", "en": "Resume publication"},
    "payment_title_job": {"ge": "ვაკანსიის გამოქვეყნება", "ru": "Публикация вакансии", "en": "Vacancy publication"},
    "payment_desc_resume": {"ge": "50 Stars ≈ 10 ლარი", "ru": "50 Stars ≈ 10 лари", "en": "50 Stars ≈ 10 GEL"},
    "payment_desc_job": {"ge": "100 Stars ≈ 20 ლარი", "ru": "100 Stars ≈ 20 лари", "en": "100 Stars ≈ 20 GEL"},
    "choose_payment": {"ge": "აირჩიეთ გადახდის მეთოდი:", "ru": "Выберите способ оплаты:", "en": "Choose payment method:"},
    "pay_stars": {"ge": "⭐ Telegram Stars", "ru": "⭐ Telegram Stars", "en": "⭐ Telegram Stars"},
    "pay_bank": {"ge": "💳 საბანკო გადარიცხვა", "ru": "💳 Перевод на карту", "en": "💳 Bank transfer"},
    "bank_details": {
        "ge": "💳 <b>საბანკო გადარიცხვა</b>\n\nIBAN: <code>GE51TB7866536010100033</code>\nმიმღები: Taymuraz Tokazov\nთანხა: {amount} ₾\n\nგადარიცხვის შემდეგ გამოგზავნეთ ჩეკის სკრინშოტი 👇",
        "ru": "💳 <b>Оплата переводом</b>\n\nIBAN: <code>GE51TB7866536010100033</code>\nПолучатель: Taymuraz Tokazov\nСумма: {amount} ₾\n\nПосле перевода отправьте скриншот чека 👇",
        "en": "💳 <b>Bank transfer</b>\n\nIBAN: <code>GE51TB7866536010100033</code>\nRecipient: Taymuraz Tokazov\nAmount: {amount} ₾\n\nAfter transfer, send a screenshot of the receipt 👇",
    },
    "receipt_received": {
        "ge": "✅ ჩეკი მიღებულია! ადმინისტრატორი შეამოწმებს და გამოაქვეყნებს თქვენს პოსტს.",
        "ru": "✅ Чек получен! Админ проверит и опубликует ваш пост.",
        "en": "✅ Receipt received! Admin will verify and publish your post.",
    },
    "admin_approve": {"ge": "✅ დადასტურება", "ru": "✅ Подтвердить", "en": "✅ Approve"},
    "admin_reject": {"ge": "❌ უარყოფა", "ru": "❌ Отклонить", "en": "❌ Reject"},
    "payment_approved": {
        "ge": "✅ გადახდა დადასტურებულია! თქვენი პოსტი გამოქვეყნდა. ავტომატურად წაიშლება 48 საათის შემდეგ.",
        "ru": "✅ Оплата подтверждена! Ваш пост опубликован. Автоудаление через 48ч.",
        "en": "✅ Payment confirmed! Your post is published. Auto-delete in 48h.",
    },
    "payment_rejected": {
        "ge": "❌ გადახდა არ დადასტურდა. სცადეთ თავიდან.",
        "ru": "❌ Оплата не подтверждена. Попробуйте снова.",
        "en": "❌ Payment not confirmed. Please try again.",
    },
}

CITY_BUTTONS = {
    "ge": ["თბილისი", "ბათუმი", "ქუთაისი", "სხვა"],
    "ru": ["Тбилиси", "Батуми", "Кутаиси", "Другой"],
    "en": ["Tbilisi", "Batumi", "Kutaisi", "Other"],
}


def t(key: str, lang: str) -> str:
    return TEXTS.get(key, {}).get(lang, TEXTS.get(key, {}).get("en", key))


# ────────── FSM States ──────────
class ResumeForm(StatesGroup):
    name = State()
    profession = State()
    experience = State()
    skills = State()
    salary = State()
    contact = State()
    city = State()


class JobForm(StatesGroup):
    company = State()
    position = State()
    duties = State()
    requirements = State()
    salary = State()
    employment = State()
    contact = State()
    city = State()


class WaitReceipt(StatesGroup):
    photo = State()


# ────────── Database ──────────
db: aiosqlite.Connection | None = None


async def init_db():
    global db
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT NOT NULL DEFAULT 'en',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            data TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            instagram_post_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT,
            payment_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER,
            amount_stars INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            telegram_payment_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    await db.commit()


async def get_lang(user_id: int) -> str:
    async with db.execute("SELECT language FROM users WHERE user_id=?", (user_id,)) as cur:
        row = await cur.fetchone()
    return row[0] if row else "en"


async def set_lang(user_id: int, lang: str):
    await db.execute(
        "INSERT INTO users(user_id, language) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET language=?",
        (user_id, lang, lang),
    )
    await db.commit()


async def create_post(user_id: int, post_type: str, data: dict) -> int:
    cur = await db.execute(
        "INSERT INTO posts(user_id, type, data, status) VALUES(?,?,?,?)",
        (user_id, post_type, json.dumps(data, ensure_ascii=False), "pending"),
    )
    await db.commit()
    return cur.lastrowid


async def mark_post_paid(post_id: int, payment_id: int):
    expires = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    await db.execute(
        "UPDATE posts SET status='paid', payment_id=?, expires_at=? WHERE id=?",
        (payment_id, expires, post_id),
    )
    await db.commit()


async def mark_post_published(post_id: int, ig_id: str | None = None):
    await db.execute(
        "UPDATE posts SET status='published', instagram_post_id=? WHERE id=?",
        (ig_id, post_id),
    )
    await db.commit()


async def create_payment(user_id: int, post_id: int, amount: int, tg_payment_id: str) -> int:
    cur = await db.execute(
        "INSERT INTO payments(user_id, post_id, amount_stars, status, telegram_payment_id) VALUES(?,?,?,?,?)",
        (user_id, post_id, amount, "completed", tg_payment_id),
    )
    await db.commit()
    return cur.lastrowid


# ────────── Helpers ──────────
def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("looking_job", lang), callback_data="role_resume")],
        [InlineKeyboardButton(text=t("looking_employee", lang), callback_data="role_job")],
    ])


def city_kb(lang: str) -> InlineKeyboardMarkup:
    cities = CITY_BUTTONS.get(lang, CITY_BUTTONS["en"])
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=c, callback_data=f"city_{c}")] for c in cities]
    )


def preview_kb(lang: str, post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("pay_publish", lang), callback_data=f"choose_pay_{post_id}")],
        [InlineKeyboardButton(text=t("cancel", lang), callback_data="cancel")],
    ])


def payment_method_kb(lang: str, post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("pay_stars", lang), callback_data=f"pay_stars_{post_id}")],
        [InlineKeyboardButton(text=t("pay_bank", lang), callback_data=f"pay_bank_{post_id}")],
        [InlineKeyboardButton(text=t("cancel", lang), callback_data="cancel")],
    ])


def format_preview(data: dict, lang: str) -> str:
    lines = [t("preview_title", lang), ""]
    for k, v in data.items():
        lines.append(f"<b>{k}</b>: {v}")
    return "\n".join(lines)


# ────────── /start & language ──────────
@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇪 ქართული", callback_data="lang_ge"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ]
    ])
    await msg.answer("🇬🇪 აირჩიეთ ენა / 🇬🇧 Choose language:", reply_markup=kb)


@router.callback_query(F.data.startswith("lang_"))
async def on_lang(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lang = cb.data.split("_", 1)[1]
    await set_lang(cb.from_user.id, lang)
    await cb.message.edit_text(t("main_menu", lang), reply_markup=main_menu_kb(lang))
    await cb.answer()


# ────────── Role selection ──────────
@router.callback_query(F.data == "role_resume")
async def start_resume(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    await state.update_data(lang=lang, flow="resume")
    await cb.message.edit_text(t("ask_name", lang))
    await state.set_state(ResumeForm.name)
    await cb.answer()


@router.callback_query(F.data == "role_job")
async def start_job(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    await state.update_data(lang=lang, flow="job")
    await cb.message.edit_text(t("ask_company", lang))
    await state.set_state(JobForm.company)
    await cb.answer()


# ────────── Length check ──────────
MAX_FIELD_LEN = 200

async def check_len(msg: Message, state: FSMContext, max_len: int = MAX_FIELD_LEN) -> bool:
    """Return True if text is too long (caller should return)."""
    if msg.text and len(msg.text) > max_len:
        d = await state.get_data()
        lang = d.get("lang", "en")
        await msg.answer(t("too_long", lang).format(max=max_len, cur=len(msg.text)))
        return True
    return False


# ────────── Resume flow ──────────
@router.message(ResumeForm.name)
async def r_name(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(r_name=msg.text)
    await msg.answer(t("ask_profession", d["lang"]))
    await state.set_state(ResumeForm.profession)


@router.message(ResumeForm.profession)
async def r_prof(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(r_profession=msg.text)
    await msg.answer(t("ask_experience", d["lang"]))
    await state.set_state(ResumeForm.experience)


@router.message(ResumeForm.experience)
async def r_exp(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(r_experience=msg.text)
    await msg.answer(t("ask_skills", d["lang"]))
    await state.set_state(ResumeForm.skills)


@router.message(ResumeForm.skills)
async def r_skills(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(r_skills=msg.text)
    await msg.answer(t("ask_salary", d["lang"]))
    await state.set_state(ResumeForm.salary)


@router.message(ResumeForm.salary)
async def r_salary(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(r_salary=msg.text)
    await msg.answer(t("ask_contact", d["lang"]))
    await state.set_state(ResumeForm.contact)


@router.message(ResumeForm.contact)
async def r_contact(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(r_contact=msg.text)
    await msg.answer(t("ask_city", d["lang"]), reply_markup=city_kb(d["lang"]))
    await state.set_state(ResumeForm.city)


@router.callback_query(ResumeForm.city, F.data.startswith("city_"))
async def r_city(cb: types.CallbackQuery, state: FSMContext):
    city = cb.data.split("_", 1)[1]
    await state.update_data(r_city=city)
    await cb.answer()
    await _show_resume_preview(cb.message, state, cb.from_user.id)


@router.message(ResumeForm.city)
async def r_city_text(msg: Message, state: FSMContext):
    if await check_len(msg, state, 100): return
    await state.update_data(r_city=msg.text)
    await _show_resume_preview(msg, state, msg.from_user.id)


async def _show_resume_preview(msg, state: FSMContext, user_id: int):
    d = await state.get_data()
    lang = d["lang"]
    labels = {
        "ge": ["სახელი", "პროფესია", "გამოცდილება", "უნარები", "ხელფასი", "კონტაქტი", "ქალაქი"],
        "ru": ["Имя", "Профессия", "Опыт", "Навыки", "Зарплата", "Контакт", "Город"],
        "en": ["Name", "Profession", "Experience", "Skills", "Salary", "Contact", "City"],
    }
    keys = ["r_name", "r_profession", "r_experience", "r_skills", "r_salary", "r_contact", "r_city"]
    lb = labels.get(lang, labels["en"])
    data = {lb[i]: d.get(keys[i], "—") for i in range(len(keys))}
    post_id = await create_post(user_id, "resume", data)
    await state.update_data(post_id=post_id)
    text = format_preview(data, lang)
    if hasattr(msg, "edit_text"):
        await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=preview_kb(lang, post_id))
    else:
        await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=preview_kb(lang, post_id))
    await state.set_state(None)


# ────────── Job flow ──────────
@router.message(JobForm.company)
async def j_company(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(j_company=msg.text)
    await msg.answer(t("ask_position", d["lang"]))
    await state.set_state(JobForm.position)


@router.message(JobForm.position)
async def j_pos(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(j_position=msg.text)
    await msg.answer(t("ask_duties", d["lang"]))
    await state.set_state(JobForm.duties)


@router.message(JobForm.duties)
async def j_duties(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(j_duties=msg.text)
    await msg.answer(t("ask_requirements", d["lang"]))
    await state.set_state(JobForm.requirements)


@router.message(JobForm.requirements)
async def j_req(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(j_requirements=msg.text)
    await msg.answer(t("ask_salary", d["lang"]))
    await state.set_state(JobForm.salary)


@router.message(JobForm.salary)
async def j_salary(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(j_salary=msg.text)
    await msg.answer(t("ask_employment", d["lang"]))
    await state.set_state(JobForm.employment)


@router.message(JobForm.employment)
async def j_empl(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(j_employment=msg.text)
    await msg.answer(t("ask_contact", d["lang"]))
    await state.set_state(JobForm.contact)


@router.message(JobForm.contact)
async def j_contact(msg: Message, state: FSMContext):
    if await check_len(msg, state): return
    d = await state.get_data()
    await state.update_data(j_contact=msg.text)
    await msg.answer(t("ask_city", d["lang"]), reply_markup=city_kb(d["lang"]))
    await state.set_state(JobForm.city)


@router.callback_query(JobForm.city, F.data.startswith("city_"))
async def j_city(cb: types.CallbackQuery, state: FSMContext):
    city = cb.data.split("_", 1)[1]
    await state.update_data(j_city=city)
    await cb.answer()
    await _show_job_preview(cb.message, state, cb.from_user.id)


@router.message(JobForm.city)
async def j_city_text(msg: Message, state: FSMContext):
    if await check_len(msg, state, 100): return
    await state.update_data(j_city=msg.text)
    await _show_job_preview(msg, state, msg.from_user.id)


async def _show_job_preview(msg, state: FSMContext, user_id: int):
    d = await state.get_data()
    lang = d["lang"]
    labels = {
        "ge": ["კომპანია", "ვაკანსია", "მოვალეობები", "მოთხოვნები", "ხელფასი", "დასაქმების ტიპი", "კონტაქტი", "ქალაქი"],
        "ru": ["Компания", "Вакансия", "Обязанности", "Требования", "Зарплата", "Тип занятости", "Контакт", "Город"],
        "en": ["Company", "Position", "Duties", "Requirements", "Salary", "Employment", "Contact", "City"],
    }
    keys = ["j_company", "j_position", "j_duties", "j_requirements", "j_salary", "j_employment", "j_contact", "j_city"]
    lb = labels.get(lang, labels["en"])
    data = {lb[i]: d.get(keys[i], "—") for i in range(len(keys))}
    post_id = await create_post(user_id, "job", data)
    await state.update_data(post_id=post_id)
    text = format_preview(data, lang)
    if hasattr(msg, "edit_text"):
        await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=preview_kb(lang, post_id))
    else:
        await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=preview_kb(lang, post_id))
    await state.set_state(None)


# ────────── Payment ──────────
@router.callback_query(F.data.startswith("choose_pay_"))
async def choose_payment(cb: types.CallbackQuery, state: FSMContext):
    post_id = int(cb.data.split("choose_pay_")[1])
    lang = await get_lang(cb.from_user.id)
    await state.update_data(pending_post_id=post_id)
    await cb.message.edit_text(t("choose_payment", lang), reply_markup=payment_method_kb(lang, post_id))
    await cb.answer()


@router.callback_query(F.data.startswith("pay_stars_"))
async def on_pay_stars(cb: types.CallbackQuery, state: FSMContext):
    post_id = int(cb.data.split("pay_stars_")[1])
    lang = await get_lang(cb.from_user.id)

    async with db.execute("SELECT type FROM posts WHERE id=?", (post_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        await cb.answer("Post not found", show_alert=True)
        return

    post_type = row[0]
    is_job = post_type == "job"
    amount = 100 if is_job else 50
    title = t("payment_title_job" if is_job else "payment_title_resume", lang)
    desc = t("payment_desc_job" if is_job else "payment_desc_resume", lang)

    await state.update_data(pending_post_id=post_id, pending_type=post_type)

    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=title,
        description=desc,
        payload=f"post_{post_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=amount)],
    )
    await cb.answer()


@router.callback_query(F.data.startswith("pay_bank_"))
async def on_pay_bank(cb: types.CallbackQuery, state: FSMContext):
    post_id = int(cb.data.split("pay_bank_")[1])
    lang = await get_lang(cb.from_user.id)

    async with db.execute("SELECT type FROM posts WHERE id=?", (post_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        await cb.answer("Post not found", show_alert=True)
        return

    post_type = row[0]
    is_job = post_type == "job"
    amount_gel = 20 if is_job else 10

    await state.update_data(pending_post_id=post_id, pending_type=post_type)
    details = t("bank_details", lang).format(amount=amount_gel)
    await cb.message.edit_text(details, parse_mode=ParseMode.HTML)
    await state.set_state(WaitReceipt.photo)
    await cb.answer()


@router.message(WaitReceipt.photo, F.photo)
async def on_receipt_photo(msg: Message, state: FSMContext):
    d = await state.get_data()
    post_id = d.get("pending_post_id")
    lang = await get_lang(msg.from_user.id)

    # notify admin with receipt
    if ADMIN_CHAT_ID:
        async with db.execute("SELECT type, data FROM posts WHERE id=?", (post_id,)) as cur:
            row = await cur.fetchone()
        post_type, data_json = row[0], json.loads(row[1])

        admin_text = (
            f"💳 Банковский перевод — проверить!\n\n"
            f"Post #{post_id} ({post_type})\n"
            f"User: {msg.from_user.id} (@{msg.from_user.username or '—'})\n"
            f"Сумма: {'20' if post_type == 'job' else '10'} ₾\n\n"
            + "\n".join(f"{k}: {v}" for k, v in data_json.items())
        )
        approve_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_approve_{post_id}_{msg.from_user.id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{post_id}_{msg.from_user.id}"),
            ]
        ])
        await bot.send_photo(
            int(ADMIN_CHAT_ID),
            photo=msg.photo[-1].file_id,
            caption=admin_text,
            reply_markup=approve_kb,
        )

    await msg.answer(t("receipt_received", lang))
    await state.clear()


@router.message(WaitReceipt.photo)
async def on_receipt_not_photo(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    hints = {"ge": "გთხოვთ გამოაგზავნოთ ჩეკის ფოტო 📸", "ru": "Пожалуйста, отправьте фото чека 📸", "en": "Please send a photo of the receipt 📸"}
    await msg.answer(hints.get(lang, hints["en"]))


# ────────── Admin approve/reject ──────────
@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    post_id = int(parts[2])
    user_id = int(parts[3])
    lang = await get_lang(user_id)

    payment_id = await create_payment(user_id, post_id, 0, "bank_transfer")
    await mark_post_paid(post_id, payment_id)

    async with db.execute("SELECT type, data FROM posts WHERE id=?", (post_id,)) as cur:
        row = await cur.fetchone()
    post_type, data_json = row[0], json.loads(row[1])

    img_buf = generate_post_image(data_json, post_type)
    caption = generate_caption(data_json, post_type, lang)
    # Upload image via Telegram to get public URL, then publish to Instagram
    from instagram import upload_image_to_hosting
    image_url = await upload_image_to_hosting(img_buf)
    img_buf.seek(0)  # reset for user preview
    ig_id = None
    if image_url:
        ig_id = await publish_post(image_url, caption)
    await mark_post_published(post_id, ig_id)

    # notify user
    await bot.send_message(user_id, t("payment_approved", lang))
    await bot.send_photo(user_id, BufferedInputFile(img_buf.read(), filename="post.png"), caption="✅ Published to Instagram!" if ig_id else "Instagram preview")

    await cb.message.edit_caption(caption=cb.message.caption + "\n\n✅ APPROVED", reply_markup=None)
    await cb.answer("Approved!")


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    post_id = int(parts[2])
    user_id = int(parts[3])
    lang = await get_lang(user_id)

    await db.execute("UPDATE posts SET status='rejected' WHERE id=?", (post_id,))
    await db.commit()

    await bot.send_message(user_id, t("payment_rejected", lang))
    await cb.message.edit_caption(caption=cb.message.caption + "\n\n❌ REJECTED", reply_markup=None)
    await cb.answer("Rejected")


@router.callback_query(F.data == "cancel")
async def on_cancel(cb: types.CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    await state.clear()
    await cb.message.edit_text(t("cancelled", lang))
    await cb.answer()


@router.pre_checkout_query()
async def on_pre_checkout(pcq: PreCheckoutQuery):
    await pcq.answer(ok=True)


@router.message(F.successful_payment)
async def on_success_payment(msg: Message, state: FSMContext):
    sp = msg.successful_payment
    payload = sp.invoice_payload  # "post_{id}"
    post_id = int(payload.split("_", 1)[1])
    user_id = msg.from_user.id
    lang = await get_lang(user_id)

    tg_payment_id = sp.telegram_payment_charge_id
    amount = sp.total_amount

    payment_id = await create_payment(user_id, post_id, amount, tg_payment_id)
    await mark_post_paid(post_id, payment_id)

    # get post data
    async with db.execute("SELECT type, data FROM posts WHERE id=?", (post_id,)) as cur:
        row = await cur.fetchone()
    post_type, data_json = row[0], json.loads(row[1])

    # generate Instagram image + caption
    img_buf = generate_post_image(data_json, post_type)
    caption = generate_caption(data_json, post_type, lang)

    # Upload image via Telegram to get public URL, then publish to Instagram
    from instagram import upload_image_to_hosting
    image_url = await upload_image_to_hosting(img_buf)
    img_buf.seek(0)  # reset for user preview
    ig_id = None
    if image_url:
        ig_id = await publish_post(image_url, caption)
    await mark_post_published(post_id, ig_id)

    # send confirmation
    await msg.answer(t("published", lang))

    # send image preview to user
    await msg.answer_photo(BufferedInputFile(img_buf.read(), filename="post.png"), caption="✅ Published to Instagram!" if ig_id else "Instagram preview")

    # notify admin
    if ADMIN_CHAT_ID:
        try:
            admin_text = (
                f"📢 New {post_type} #{post_id}\n"
                f"User: {user_id} (@{msg.from_user.username or '—'})\n"
                f"Stars: {amount}\n"
                f"Payment: {tg_payment_id}\n\n"
                + "\n".join(f"{k}: {v}" for k, v in data_json.items())
            )
            await bot.send_message(int(ADMIN_CHAT_ID), admin_text)
        except Exception as e:
            log.error("Failed to notify admin: %s", e)


# ────────── Auto-delete task ──────────
async def auto_delete_loop():
    """Check every hour for expired posts."""
    while True:
        await asyncio.sleep(3600)
        try:
            now = datetime.now(timezone.utc).isoformat()
            async with db.execute(
                "SELECT id, user_id, instagram_post_id FROM posts WHERE status IN ('paid','published') AND expires_at < ?",
                (now,),
            ) as cur:
                rows = await cur.fetchall()
            for post_id, user_id, ig_id in rows:
                # delete from Instagram if posted
                if ig_id:
                    await delete_post(ig_id)
                # mark expired
                await db.execute("UPDATE posts SET status='expired' WHERE id=?", (post_id,))
                await db.commit()
                # notify user
                lang = await get_lang(user_id)
                try:
                    await bot.send_message(user_id, t("post_expired", lang))
                except Exception:
                    pass
            if rows:
                log.info("Expired %d posts", len(rows))
        except Exception as e:
            log.error("auto_delete_loop error: %s", e)


# ────────── Main ──────────
async def main():
    await init_db()
    asyncio.create_task(auto_delete_loop())
    log.info("Bot starting in polling mode...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
