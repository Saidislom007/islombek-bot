import asyncio
import base64
import hashlib
import os
import random
import sqlite3
import string
import time
from contextlib import closing
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from cryptography.fernet import Fernet


TOKEN = "8562451249:AAGoRws4uP865VZiLGAohrvFGrKNodq0jxg"

DB_NAME = "password_manager.db"
SESSION_TIMEOUT = 300
MAX_PIN_ATTEMPTS = 3
PIN_BLOCK_SECONDS = 120

bot = Bot(token=TOKEN)
dp = Dispatcher()

USER_LANG = {}
UNLOCKED_USERS = {}
PIN_FAILS = {} 
TEXTS = {
    "uz": {
        "choose_lang": "🌐 Tilni tanlang:",
        "main_menu_locked": "🔒 Bot qulflangan.\nDavom etish uchun PIN kiriting.",
        "main_menu_unlocked": "🏠 Asosiy menyu",
        "guide_title": "📘 Qo‘llanma",
        "guide_text": (
            "📘 Qo‘llanma\n\n"
            "🔐 Create — yangi login/parol saqlash\n"
            "📂 Vault — saqlangan ma’lumotlar\n"
            "🔎 Search — platforma bo‘yicha qidirish\n"
            "⚙️ Settings — sozlamalar va export\n"
            "🛡 Security — PIN, lock, PIN almashtirish\n\n"
            "Parollar bazada shifrlangan holda saqlanadi.\n"
            "Bot auto-lock bo‘ladi.\n"
            "PIN 3 marta xato kiritilsa vaqtincha blok bo‘ladi."
        ),
        "guide_btn": "📘 Qo‘llanma",
        "create_btn": "🔐 Create",
        "vault_btn": "📂 Vault",
        "search_btn": "🔎 Search",
        "settings_btn": "⚙️ Settings",
        "security_btn": "🛡 Security",
        "back_btn": "⬅️ Orqaga",
        "home_btn": "🏠 Bosh menyu",

        "unlock_btn": "🔓 Ochish",
        "lock_btn": "🔒 Yopish",
        "set_pin_btn": "⚙️ PIN o‘rnatish",
        "change_pin_btn": "♻️ PIN almashtirish",

        "ask_new_pin": "🔐 Yangi 4 xonali PIN kiriting:",
        "ask_confirm_pin": "🔁 PIN ni qayta kiriting:",
        "ask_old_pin": "🔐 Eski PIN ni kiriting:",
        "ask_unlock_pin": "🔓 PIN kiriting:",
        "pin_invalid": "❌ PIN faqat 4 xonali raqam bo‘lishi kerak.",
        "pin_not_match": "❌ PIN lar mos kelmadi.",
        "pin_set_success": "✅ PIN saqlandi.",
        "pin_changed_success": "✅ PIN almashtirildi.",
        "unlock_success": "✅ Bot ochildi.",
        "unlock_failed": "❌ PIN noto‘g‘ri.",
        "old_pin_wrong": "❌ Eski PIN noto‘g‘ri.",
        "locked_success": "🔒 Bot yopildi.",
        "no_pin_yet": "⚠️ Avval PIN o‘rnating.",
        "pin_exists": "ℹ️ PIN allaqachon mavjud.",
        "need_unlock": "🔒 Avval botni PIN bilan oching.",
        "pin_blocked": "⛔ Juda ko‘p xato urinish. Keyinroq urinib ko‘ring.",

        "create_type_menu": "🔐 Menyudan birini tanlang, men sizga parol generatsiya qilaman:",
        "numbers_only": "1️⃣ Faqat raqamlar",
        "letters_only": "2️⃣ Faqat harflar",
        "letters_numbers": "3️⃣ Raqam + harf",
        "all_mixed": "4️⃣ Raqam + harf + belgilar",
        "choose_length": "📏 Parol uzunligini tanlang:",
        "custom_length_btn": "✍️ O‘zim kiritaman",
        "ask_custom_length": "✍️ Parol uzunligini kiriting.\nMasalan: 25",
        "invalid_length": "❌ Uzunlik 4 dan 64 gacha bo‘lishi kerak.",

        "ask_platform": "📱 Platforma nomini kiriting:",
        "ask_login": "👤 Login/username kiriting:\nKerak bo‘lmasa `-` yuboring.",
        "ask_email": "📧 Email kiriting:\nKerak bo‘lmasa `-` yuboring.",
        "ask_note": "📝 Izoh kiriting:\nKerak bo‘lmasa `-` yuboring.",

        "saved_item": (
            "✅ Saqlandi\n\n"
            "📱 Platforma: {platform}\n"
            "👤 Login: {login}\n"
            "📧 Email: {email}\n"
            "🔐 Parol: `{password}`\n"
            "📝 Izoh: {note}"
        ),

        "empty_vault": "📭 Hozircha saqlangan ma’lumotlar yo‘q.",
        "vault_page_hidden": (
            "📂 Vault\n\n"
            "📍 {current}/{total}\n"
            "📱 Platforma: {platform}\n"
            "👤 Login: {login}\n"
            "📧 Email: {email}\n"
            "🔐 Parol: `************`\n"
            "📝 Izoh: {note}"
        ),
        "vault_page_shown": (
            "📂 Vault\n\n"
            "📍 {current}/{total}\n"
            "📱 Platforma: {platform}\n"
            "👤 Login: {login}\n"
            "📧 Email: {email}\n"
            "🔐 Parol: `{password}`\n"
            "📝 Izoh: {note}"
        ),
        "copied_label": "📋 Ko‘rsatildi",
        "deleted": "✅ O‘chirildi.",
        "after_delete_empty": "✅ O‘chirildi.\n\n📭 Endi vault bo‘sh.",
        "delete_all_btn": "🗑 Hammasini o‘chirish",
        "confirm_delete_all": "⚠️ Rostdan ham hammasini o‘chirmoqchimisiz?",
        "confirm_yes": "✅ Ha",
        "confirm_no": "❌ Yo‘q",
        "all_deleted": "✅ Hamma ma’lumot o‘chirildi.",

        "search_prompt": "🔎 Qidirish uchun platforma nomini kiriting:",
        "search_no_results": "❌ Hech narsa topilmadi.",
        "search_results_title": "🔎 Qidiruv natijalari",

        "edit_btn": "✏️ Edit",
        "regen_btn": "♻️ Regenerate",
        "show_btn": "👁 Show",
        "delete_btn": "🗑 Delete",
        "next_btn": "➡️",
        "prev_btn": "⬅️",

        "edit_menu": "✏️ Qaysi maydonni o‘zgartirasiz?",
        "edit_platform": "📱 Platforma",
        "edit_login": "👤 Login",
        "edit_email": "📧 Email",
        "edit_note": "📝 Izoh",
        "edit_password": "🔐 Parol",
        "ask_new_value": "✏️ Yangi qiymatni yuboring:",
        "updated_success": "✅ Yangilandi.",
        "regen_done": "✅ Yangi parol generatsiya qilindi.",

        "settings_text": (
            "⚙️ Settings\n\n"
            "⏳ Auto-lock: 5 minut\n"
            "📤 Export: txt\n"
            "🗑 Delete all mavjud"
        ),
        "export_btn": "📤 Export TXT",

        "security_text": "🛡 Security bo‘limi",
        "fallback": "🤖 Menyudan foydalaning.",
    },
    "en": {
        "choose_lang": "🌐 Choose language:",
        "main_menu_locked": "🔒 Bot is locked.\nEnter PIN to continue.",
        "main_menu_unlocked": "🏠 Main menu",
        "guide_title": "📘 Guide",
        "guide_text": (
            "📘 Guide\n\n"
            "🔐 Create — save new login/password\n"
            "📂 Vault — saved items\n"
            "🔎 Search — search by platform\n"
            "⚙️ Settings — settings and export\n"
            "🛡 Security — PIN, lock, change PIN\n\n"
            "Passwords are stored encrypted.\n"
            "Bot auto-locks.\n"
            "3 wrong PIN attempts trigger temporary block."
        ),
        "guide_btn": "📘 Guide",
        "create_btn": "🔐 Create",
        "vault_btn": "📂 Vault",
        "search_btn": "🔎 Search",
        "settings_btn": "⚙️ Settings",
        "security_btn": "🛡 Security",
        "back_btn": "⬅️ Back",
        "home_btn": "🏠 Home",

        "unlock_btn": "🔓 Unlock",
        "lock_btn": "🔒 Lock",
        "set_pin_btn": "⚙️ Set PIN",
        "change_pin_btn": "♻️ Change PIN",

        "ask_new_pin": "🔐 Enter new 4-digit PIN:",
        "ask_confirm_pin": "🔁 Re-enter PIN:",
        "ask_old_pin": "🔐 Enter old PIN:",
        "ask_unlock_pin": "🔓 Enter PIN:",
        "pin_invalid": "❌ PIN must be exactly 4 digits.",
        "pin_not_match": "❌ PINs do not match.",
        "pin_set_success": "✅ PIN saved.",
        "pin_changed_success": "✅ PIN changed.",
        "unlock_success": "✅ Bot unlocked.",
        "unlock_failed": "❌ Wrong PIN.",
        "old_pin_wrong": "❌ Old PIN is incorrect.",
        "locked_success": "🔒 Bot locked.",
        "no_pin_yet": "⚠️ Set a PIN first.",
        "pin_exists": "ℹ️ PIN already exists.",
        "need_unlock": "🔒 Unlock with PIN first.",
        "pin_blocked": "⛔ Too many wrong attempts. Try again later.",

        "create_type_menu": "🔐 Choose one, I will generate a password for you:",
        "numbers_only": "1️⃣ Numbers only",
        "letters_only": "2️⃣ Letters only",
        "letters_numbers": "3️⃣ Numbers + letters",
        "all_mixed": "4️⃣ Numbers + letters + symbols",
        "choose_length": "📏 Choose password length:",
        "custom_length_btn": "✍️ Enter manually",
        "ask_custom_length": "✍️ Enter length.\nExample: 25",
        "invalid_length": "❌ Length must be between 4 and 64.",

        "ask_platform": "📱 Enter platform name:",
        "ask_login": "👤 Enter login/username:\nSend `-` if not needed.",
        "ask_email": "📧 Enter email:\nSend `-` if not needed.",
        "ask_note": "📝 Enter note:\nSend `-` if not needed.",

        "saved_item": (
            "✅ Saved\n\n"
            "📱 Platform: {platform}\n"
            "👤 Login: {login}\n"
            "📧 Email: {email}\n"
            "🔐 Password: `{password}`\n"
            "📝 Note: {note}"
        ),

        "empty_vault": "📭 No saved items yet.",
        "vault_page_hidden": (
            "📂 Vault\n\n"
            "📍 {current}/{total}\n"
            "📱 Platform: {platform}\n"
            "👤 Login: {login}\n"
            "📧 Email: {email}\n"
            "🔐 Password: `************`\n"
            "📝 Note: {note}"
        ),
        "vault_page_shown": (
            "📂 Vault\n\n"
            "📍 {current}/{total}\n"
            "📱 Platform: {platform}\n"
            "👤 Login: {login}\n"
            "📧 Email: {email}\n"
            "🔐 Password: `{password}`\n"
            "📝 Note: {note}"
        ),
        "copied_label": "📋 Shown",
        "deleted": "✅ Deleted.",
        "after_delete_empty": "✅ Deleted.\n\n📭 Vault is now empty.",
        "delete_all_btn": "🗑 Delete all",
        "confirm_delete_all": "⚠️ Are you sure you want to delete everything?",
        "confirm_yes": "✅ Yes",
        "confirm_no": "❌ No",
        "all_deleted": "✅ All data deleted.",

        "search_prompt": "🔎 Enter platform name to search:",
        "search_no_results": "❌ Nothing found.",
        "search_results_title": "🔎 Search results",

        "edit_btn": "✏️ Edit",
        "regen_btn": "♻️ Regenerate",
        "show_btn": "👁 Show",
        "delete_btn": "🗑 Delete",
        "next_btn": "➡️",
        "prev_btn": "⬅️",

        "edit_menu": "✏️ Which field do you want to edit?",
        "edit_platform": "📱 Platform",
        "edit_login": "👤 Login",
        "edit_email": "📧 Email",
        "edit_note": "📝 Note",
        "edit_password": "🔐 Password",
        "ask_new_value": "✏️ Send new value:",
        "updated_success": "✅ Updated.",
        "regen_done": "✅ New password generated.",

        "settings_text": (
            "⚙️ Settings\n\n"
            "⏳ Auto-lock: 5 minutes\n"
            "📤 Export: txt\n"
            "🗑 Delete all is available"
        ),
        "export_btn": "📤 Export TXT",

        "security_text": "🛡 Security section",
        "fallback": "🤖 Use the menu.",
    },
    "tr": {
        "choose_lang": "🌐 Dil seçin:",
        "main_menu_locked": "🔒 Bot kilitli.\nDevam etmek için PIN girin.",
        "main_menu_unlocked": "🏠 Ana menü",
        "guide_title": "📘 Kılavuz",
        "guide_text": (
            "📘 Kılavuz\n\n"
            "🔐 Create — yeni giriş/şifre kaydet\n"
            "📂 Vault — kayıtlı öğeler\n"
            "🔎 Search — platforma göre ara\n"
            "⚙️ Settings — ayarlar ve export\n"
            "🛡 Security — PIN, kilit, PIN değiştir\n\n"
            "Şifreler şifrelenmiş saklanır.\n"
            "Bot otomatik kilitlenir.\n"
            "3 yanlış PIN geçici blok uygular."
        ),
        "guide_btn": "📘 Kılavuz",
        "create_btn": "🔐 Create",
        "vault_btn": "📂 Vault",
        "search_btn": "🔎 Search",
        "settings_btn": "⚙️ Settings",
        "security_btn": "🛡 Security",
        "back_btn": "⬅️ Geri",
        "home_btn": "🏠 Ana menü",

        "unlock_btn": "🔓 Aç",
        "lock_btn": "🔒 Kilitle",
        "set_pin_btn": "⚙️ PIN ayarla",
        "change_pin_btn": "♻️ PIN değiştir",

        "ask_new_pin": "🔐 Yeni 4 haneli PIN girin:",
        "ask_confirm_pin": "🔁 PIN'i tekrar girin:",
        "ask_old_pin": "🔐 Eski PIN'i girin:",
        "ask_unlock_pin": "🔓 PIN girin:",
        "pin_invalid": "❌ PIN tam 4 rakam olmalı.",
        "pin_not_match": "❌ PIN'ler eşleşmiyor.",
        "pin_set_success": "✅ PIN kaydedildi.",
        "pin_changed_success": "✅ PIN değiştirildi.",
        "unlock_success": "✅ Bot açıldı.",
        "unlock_failed": "❌ Yanlış PIN.",
        "old_pin_wrong": "❌ Eski PIN yanlış.",
        "locked_success": "🔒 Bot kilitlendi.",
        "no_pin_yet": "⚠️ Önce PIN ayarlayın.",
        "pin_exists": "ℹ️ PIN zaten var.",
        "need_unlock": "🔒 Önce PIN ile açın.",
        "pin_blocked": "⛔ Çok fazla yanlış deneme. Sonra tekrar deneyin.",

        "create_type_menu": "🔐 Birini seçin, size şifre oluşturayım:",
        "numbers_only": "1️⃣ Sadece rakamlar",
        "letters_only": "2️⃣ Sadece harfler",
        "letters_numbers": "3️⃣ Rakam + harf",
        "all_mixed": "4️⃣ Rakam + harf + semboller",
        "choose_length": "📏 Şifre uzunluğunu seçin:",
        "custom_length_btn": "✍️ Manuel gir",
        "ask_custom_length": "✍️ Uzunluğu girin.\nÖrnek: 25",
        "invalid_length": "❌ Uzunluk 4 ile 64 arasında olmalı.",

        "ask_platform": "📱 Platform adını girin:",
        "ask_login": "👤 Login/username girin:\nGerekmiyorsa `-` gönderin.",
        "ask_email": "📧 Email girin:\nGerekmiyorsa `-` gönderin.",
        "ask_note": "📝 Not girin:\nGerekmiyorsa `-` gönderin.",

        "saved_item": (
            "✅ Kaydedildi\n\n"
            "📱 Platform: {platform}\n"
            "👤 Login: {login}\n"
            "📧 Email: {email}\n"
            "🔐 Şifre: `{password}`\n"
            "📝 Not: {note}"
        ),

        "empty_vault": "📭 Henüz kayıt yok.",
        "vault_page_hidden": (
            "📂 Vault\n\n"
            "📍 {current}/{total}\n"
            "📱 Platform: {platform}\n"
            "👤 Login: {login}\n"
            "📧 Email: {email}\n"
            "🔐 Şifre: `************`\n"
            "📝 Not: {note}"
        ),
        "vault_page_shown": (
            "📂 Vault\n\n"
            "📍 {current}/{total}\n"
            "📱 Platform: {platform}\n"
            "👤 Login: {login}\n"
            "📧 Email: {email}\n"
            "🔐 Şifre: `{password}`\n"
            "📝 Not: {note}"
        ),
        "copied_label": "📋 Gösterildi",
        "deleted": "✅ Silindi.",
        "after_delete_empty": "✅ Silindi.\n\n📭 Vault artık boş.",
        "delete_all_btn": "🗑 Hepsini sil",
        "confirm_delete_all": "⚠️ Her şeyi silmek istediğinize emin misiniz?",
        "confirm_yes": "✅ Evet",
        "confirm_no": "❌ Hayır",
        "all_deleted": "✅ Tüm veriler silindi.",

        "search_prompt": "🔎 Aramak için platform adı girin:",
        "search_no_results": "❌ Bir şey bulunamadı.",
        "search_results_title": "🔎 Arama sonuçları",

        "edit_btn": "✏️ Edit",
        "regen_btn": "♻️ Regenerate",
        "show_btn": "👁 Show",
        "delete_btn": "🗑 Delete",
        "next_btn": "➡️",
        "prev_btn": "⬅️",

        "edit_menu": "✏️ Hangi alanı değiştirmek istiyorsunuz?",
        "edit_platform": "📱 Platform",
        "edit_login": "👤 Login",
        "edit_email": "📧 Email",
        "edit_note": "📝 Not",
        "edit_password": "🔐 Şifre",
        "ask_new_value": "✏️ Yeni değeri gönderin:",
        "updated_success": "✅ Güncellendi.",
        "regen_done": "✅ Yeni şifre oluşturuldu.",

        "settings_text": (
            "⚙️ Settings\n\n"
            "⏳ Auto-lock: 5 dakika\n"
            "📤 Export: txt\n"
            "🗑 Hepsini sil mevcut"
        ),
        "export_btn": "📤 Export TXT",

        "security_text": "🛡 Güvenlik bölümü",
        "fallback": "🤖 Menüyü kullanın.",
    },
}


def get_lang(user_id: int) -> str:
    return USER_LANG.get(user_id, "uz")


def t(user_id: int, key: str) -> str:
    return TEXTS[get_lang(user_id)][key]


def safe_value(value: Optional[str]) -> str:
    if value is None or value == "":
        return "-"
    return value


def normalize_index(index: int, total: int) -> int:
    if total <= 0:
        return 0
    if index < 0:
        return 0
    if index >= total:
        return total - 1
    return index


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def is_valid_pin(pin: str) -> bool:
    return pin.isdigit() and len(pin) == 4


def set_unlocked(user_id: int):
    UNLOCKED_USERS[user_id] = time.time() + SESSION_TIMEOUT


def is_unlocked(user_id: int) -> bool:
    expires = UNLOCKED_USERS.get(user_id)
    if not expires:
        return False
    if time.time() > expires:
        UNLOCKED_USERS.pop(user_id, None)
        return False
    return True


def lock_user(user_id: int):
    UNLOCKED_USERS.pop(user_id, None)


def user_blocked(user_id: int) -> bool:
    data = PIN_FAILS.get(user_id)
    if not data:
        return False
    blocked_until = data.get("blocked_until", 0)
    if blocked_until and time.time() < blocked_until:
        return True
    if blocked_until and time.time() >= blocked_until:
        PIN_FAILS.pop(user_id, None)
        return False
    return False


def register_failed_pin(user_id: int):
    data = PIN_FAILS.get(user_id, {"count": 0, "blocked_until": 0})
    data["count"] += 1
    if data["count"] >= MAX_PIN_ATTEMPTS:
        data["blocked_until"] = time.time() + PIN_BLOCK_SECONDS
        data["count"] = 0
    PIN_FAILS[user_id] = data


def clear_failed_pin(user_id: int):
    PIN_FAILS.pop(user_id, None)


def get_secret_key() -> bytes:
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        cur.execute("SELECT value FROM app_meta WHERE key='secret_key'")
        row = cur.fetchone()
        if row:
            return row[0].encode()

        secret = Fernet.generate_key()
        cur.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)", ("secret_key", secret.decode()))
        conn.commit()
        return secret


FERNET = None


def encrypt_text(text: str) -> str:
    return FERNET.encrypt(text.encode()).decode()


def decrypt_text(token: str) -> str:
    return FERNET.decrypt(token.encode()).decode()

class PinState(StatesGroup):
    waiting_for_new_pin = State()
    waiting_for_confirm_pin = State()
    waiting_for_unlock_pin = State()
    waiting_for_old_pin_for_change = State()
    waiting_for_change_new_pin = State()
    waiting_for_change_confirm_pin = State()


class CreateState(StatesGroup):
    waiting_for_custom_length = State()
    waiting_for_platform = State()
    waiting_for_login = State()
    waiting_for_email = State()
    waiting_for_note = State()


class SearchState(StatesGroup):
    waiting_for_query = State()


class EditState(StatesGroup):
    waiting_for_new_value = State()


def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                pin_hash TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS vault (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                login TEXT,
                email TEXT,
                password TEXT NOT NULL,
                note TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        conn.commit()


def has_pin(user_id: int) -> bool:
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT pin_hash FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row is not None and row[0] is not None


def get_pin_hash(user_id: int) -> Optional[str]:
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT pin_hash FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None


def set_pin_hash(user_id: int, pin_hash: str):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, pin_hash)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET pin_hash=excluded.pin_hash
        """, (user_id, pin_hash))
        conn.commit()


def verify_pin(user_id: int, pin: str) -> bool:
    saved = get_pin_hash(user_id)
    if not saved:
        return False
    return saved == hash_pin(pin)


def save_vault_item(user_id: int, platform: str, login: str, email: str, password: str, note: str):
    now = int(time.time())
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO vault (user_id, platform, login, email, password, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            platform,
            login,
            email,
            encrypt_text(password),
            note,
            now,
            now
        ))
        conn.commit()


def get_vault_items(user_id: int):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM vault WHERE user_id=? ORDER BY id DESC", (user_id,))
        return cur.fetchall()


def get_vault_item(item_id: int, user_id: int):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM vault WHERE id=? AND user_id=?", (item_id, user_id))
        return cur.fetchone()


def search_vault_items(user_id: int, query: str):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        like = f"%{query.lower()}%"
        cur.execute("""
            SELECT * FROM vault
            WHERE user_id=?
              AND (
                  lower(platform) LIKE ?
                  OR lower(COALESCE(login, '')) LIKE ?
                  OR lower(COALESCE(email, '')) LIKE ?
                  OR lower(COALESCE(note, '')) LIKE ?
              )
            ORDER BY id DESC
        """, (user_id, like, like, like, like))
        return cur.fetchall()


def update_vault_field(item_id: int, user_id: int, field: str, value: str):
    now = int(time.time())
    if field not in {"platform", "login", "email", "password", "note"}:
        return
    if field == "password":
        value = encrypt_text(value)

    with closing(sqlite3.connect(DB_NAME)) as conn:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE vault
            SET {field}=?, updated_at=?
            WHERE id=? AND user_id=?
        """, (value, now, item_id, user_id))
        conn.commit()


def delete_vault_item(item_id: int, user_id: int):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM vault WHERE id=? AND user_id=?", (item_id, user_id))
        conn.commit()


def delete_all_vault_items(user_id: int):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM vault WHERE user_id=?", (user_id,))
        conn.commit()


def generate_password_by_type(password_type: str, length: int) -> str:
    if password_type == "numbers":
        chars = string.digits
    elif password_type == "letters":
        chars = string.ascii_letters
    elif password_type == "letters_numbers":
        chars = string.ascii_letters + string.digits
    else:
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=<>?"

    return "".join(random.choice(chars) for _ in range(length))


def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uzbek", callback_data="lang:uz")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang:tr")],
    ])


def home_kb(user_id: int):
    if is_unlocked(user_id):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(user_id, "guide_btn"), callback_data="menu:guide")],
            [InlineKeyboardButton(text=t(user_id, "create_btn"), callback_data="menu:create")],
            [
                InlineKeyboardButton(text=t(user_id, "vault_btn"), callback_data="menu:vault"),
                InlineKeyboardButton(text=t(user_id, "search_btn"), callback_data="menu:search"),
            ],
            [
                InlineKeyboardButton(text=t(user_id, "settings_btn"), callback_data="menu:settings"),
                InlineKeyboardButton(text=t(user_id, "security_btn"), callback_data="menu:security"),
            ],
        ])
    else:
        buttons = [
            [InlineKeyboardButton(text=t(user_id, "guide_btn"), callback_data="menu:guide")],
            [InlineKeyboardButton(text=t(user_id, "unlock_btn"), callback_data="security:unlock")],
        ]
        if has_pin(user_id):
            buttons.append([InlineKeyboardButton(text=t(user_id, "change_pin_btn"), callback_data="security:change_pin")])
        else:
            buttons.append([InlineKeyboardButton(text=t(user_id, "set_pin_btn"), callback_data="security:set_pin")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)


def one_back_kb(user_id: int, cb: str = "menu:home"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(user_id, "back_btn"), callback_data=cb)]
    ])


def create_type_kb(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(user_id, "numbers_only"), callback_data="ptype:numbers")],
        [InlineKeyboardButton(text=t(user_id, "letters_only"), callback_data="ptype:letters")],
        [InlineKeyboardButton(text=t(user_id, "letters_numbers"), callback_data="ptype:letters_numbers")],
        [InlineKeyboardButton(text=t(user_id, "all_mixed"), callback_data="ptype:all")],
        [InlineKeyboardButton(text=t(user_id, "back_btn"), callback_data="menu:home")],
    ])


def length_kb(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="6", callback_data="plen:6"),
            InlineKeyboardButton(text="8", callback_data="plen:8"),
            InlineKeyboardButton(text="10", callback_data="plen:10"),
        ],
        [
            InlineKeyboardButton(text="12", callback_data="plen:12"),
            InlineKeyboardButton(text="16", callback_data="plen:16"),
            InlineKeyboardButton(text="20", callback_data="plen:20"),
        ],
        [InlineKeyboardButton(text=t(user_id, "custom_length_btn"), callback_data="plen:custom")],
        [InlineKeyboardButton(text=t(user_id, "back_btn"), callback_data="menu:create")],
    ])


def security_kb(user_id: int):
    buttons = []
    if is_unlocked(user_id):
        buttons.append([InlineKeyboardButton(text=t(user_id, "lock_btn"), callback_data="security:lock")])
    else:
        buttons.append([InlineKeyboardButton(text=t(user_id, "unlock_btn"), callback_data="security:unlock")])

    if has_pin(user_id):
        buttons.append([InlineKeyboardButton(text=t(user_id, "change_pin_btn"), callback_data="security:change_pin")])
    else:
        buttons.append([InlineKeyboardButton(text=t(user_id, "set_pin_btn"), callback_data="security:set_pin")])

    buttons.append([InlineKeyboardButton(text=t(user_id, "home_btn"), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_kb(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(user_id, "export_btn"), callback_data="settings:export")],
        [InlineKeyboardButton(text=t(user_id, "delete_all_btn"), callback_data="settings:delete_all")],
        [InlineKeyboardButton(text=t(user_id, "home_btn"), callback_data="menu:home")],
    ])


def confirm_delete_all_kb(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(user_id, "confirm_yes"), callback_data="settings:delete_all_yes"),
            InlineKeyboardButton(text=t(user_id, "confirm_no"), callback_data="settings:delete_all_no"),
        ],
        [InlineKeyboardButton(text=t(user_id, "home_btn"), callback_data="menu:home")],
    ])


def vault_item_kb(user_id: int, index: int, total: int, item_id: int, source: str = "vault"):
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton(text=t(user_id, "prev_btn"), callback_data=f"{source}:nav:{index - 1}"))
    if index < total - 1:
        nav.append(InlineKeyboardButton(text=t(user_id, "next_btn"), callback_data=f"{source}:nav:{index + 1}"))

    rows = [
        [InlineKeyboardButton(text=t(user_id, "show_btn"), callback_data=f"{source}:show:{item_id}:{index}")],
        [
            InlineKeyboardButton(text=t(user_id, "edit_btn"), callback_data=f"item:edit:{item_id}:{source}:{index}"),
            InlineKeyboardButton(text=t(user_id, "regen_btn"), callback_data=f"item:regen:{item_id}:{source}:{index}"),
        ],
        [InlineKeyboardButton(text=t(user_id, "delete_btn"), callback_data=f"{source}:delete:{item_id}:{index}")],
    ]
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=t(user_id, "home_btn"), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_fields_kb(user_id: int, item_id: int, source: str, index: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(user_id, "edit_platform"), callback_data=f"editfield:platform:{item_id}:{source}:{index}")],
        [InlineKeyboardButton(text=t(user_id, "edit_login"), callback_data=f"editfield:login:{item_id}:{source}:{index}")],
        [InlineKeyboardButton(text=t(user_id, "edit_email"), callback_data=f"editfield:email:{item_id}:{source}:{index}")],
        [InlineKeyboardButton(text=t(user_id, "edit_note"), callback_data=f"editfield:note:{item_id}:{source}:{index}")],
        [InlineKeyboardButton(text=t(user_id, "edit_password"), callback_data=f"editfield:password:{item_id}:{source}:{index}")],
        [InlineKeyboardButton(text=t(user_id, "back_btn"), callback_data=f"{source}:show:{item_id}:{index}")],
    ])


async def safe_edit(call: CallbackQuery, text: str, reply_markup=None):
    try:
        await call.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await call.answer()
            return
        raise


async def render_home(call: CallbackQuery, state: FSMContext):
    await state.clear()
    text = t(call.from_user.id, "main_menu_unlocked") if is_unlocked(call.from_user.id) else t(call.from_user.id, "main_menu_locked")
    await safe_edit(call, text, home_kb(call.from_user.id))


def format_item_text(user_id: int, item, current: int, total: int, show_password: bool):
    platform = safe_value(item["platform"])
    login = safe_value(item["login"])
    email = safe_value(item["email"])
    note = safe_value(item["note"])
    password = decrypt_text(item["password"])

    if show_password:
        return t(user_id, "vault_page_shown").format(
            current=current, total=total,
            platform=platform, login=login, email=email,
            password=password, note=note
        )
    return t(user_id, "vault_page_hidden").format(
        current=current, total=total,
        platform=platform, login=login, email=email,
        password="************", note=note
    )


async def render_items_list(call: CallbackQuery, user_id: int, items, index: int, show_password: bool, source: str):
    if not items:
        await safe_edit(call, t(user_id, "empty_vault"), home_kb(user_id))
        return

    index = normalize_index(index, len(items))
    item = items[index]
    text = format_item_text(user_id, item, index + 1, len(items), show_password)
    await safe_edit(
        call,
        text,
        vault_item_kb(user_id, index, len(items), item["id"], source=source)
    )


async def ensure_unlocked(call: CallbackQuery, state: FSMContext) -> bool:
    user_id = call.from_user.id

    if not has_pin(user_id):
        await state.clear()
        await safe_edit(call, t(user_id, "no_pin_yet"), home_kb(user_id))
        return False

    if not is_unlocked(user_id):
        await state.clear()
        await safe_edit(call, t(user_id, "main_menu_locked"), home_kb(user_id))
        return False

    return True

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    lock_user(message.from_user.id)
    await message.answer(TEXTS["uz"]["choose_lang"], reply_markup=lang_kb())


@dp.callback_query(F.data.startswith("lang:"))
async def lang_handler(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":")[1]
    USER_LANG[call.from_user.id] = lang
    await render_home(call, state)
    await call.answer()


@dp.callback_query(F.data == "menu:home")
async def menu_home(call: CallbackQuery, state: FSMContext):
    await render_home(call, state)
    await call.answer()


@dp.callback_query(F.data == "menu:guide")
async def menu_guide(call: CallbackQuery):
    user_id = call.from_user.id
    await safe_edit(call, t(user_id, "guide_text"), one_back_kb(user_id, "menu:home"))
    await call.answer()


@dp.callback_query(F.data == "menu:security")
async def menu_security(call: CallbackQuery):
    user_id = call.from_user.id
    await safe_edit(call, t(user_id, "security_text"), security_kb(user_id))
    await call.answer()


@dp.callback_query(F.data == "menu:settings")
async def menu_settings(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    user_id = call.from_user.id
    await safe_edit(call, t(user_id, "settings_text"), settings_kb(user_id))
    await call.answer()


@dp.callback_query(F.data == "security:set_pin")
async def security_set_pin(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if has_pin(user_id):
        await safe_edit(call, t(user_id, "pin_exists"), security_kb(user_id))
        await call.answer()
        return
    await state.clear()
    await state.set_state(PinState.waiting_for_new_pin)
    await safe_edit(call, t(user_id, "ask_new_pin"), one_back_kb(user_id))
    await call.answer()


@dp.callback_query(F.data == "security:change_pin")
async def security_change_pin(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if not has_pin(user_id):
        await safe_edit(call, t(user_id, "no_pin_yet"), security_kb(user_id))
        await call.answer()
        return
    await state.clear()
    await state.set_state(PinState.waiting_for_old_pin_for_change)
    await safe_edit(call, t(user_id, "ask_old_pin"), one_back_kb(user_id))
    await call.answer()


@dp.callback_query(F.data == "security:unlock")
async def security_unlock(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    if user_blocked(user_id):
        await safe_edit(call, t(user_id, "pin_blocked"), home_kb(user_id))
        await call.answer()
        return
    if not has_pin(user_id):
        await safe_edit(call, t(user_id, "no_pin_yet"), home_kb(user_id))
        await call.answer()
        return
    await state.clear()
    await state.set_state(PinState.waiting_for_unlock_pin)
    await safe_edit(call, t(user_id, "ask_unlock_pin"), one_back_kb(user_id))
    await call.answer()


@dp.callback_query(F.data == "security:lock")
async def security_lock(call: CallbackQuery, state: FSMContext):
    lock_user(call.from_user.id)
    await render_home(call, state)
    await call.answer(t(call.from_user.id, "locked_success"))


@dp.message(PinState.waiting_for_new_pin)
async def pin_new(message: Message, state: FSMContext):
    pin = message.text.strip()
    if not is_valid_pin(pin):
        await message.answer(t(message.from_user.id, "pin_invalid"))
        return
    await state.update_data(first_pin=pin)
    await state.set_state(PinState.waiting_for_confirm_pin)
    await message.answer(t(message.from_user.id, "ask_confirm_pin"))


@dp.message(PinState.waiting_for_confirm_pin)
async def pin_confirm(message: Message, state: FSMContext):
    confirm_pin = message.text.strip()
    data = await state.get_data()
    if confirm_pin != data.get("first_pin"):
        await state.clear()
        await message.answer(t(message.from_user.id, "pin_not_match"))
        return
    set_pin_hash(message.from_user.id, hash_pin(confirm_pin))
    set_unlocked(message.from_user.id)
    await state.clear()
    await message.answer(t(message.from_user.id, "pin_set_success"), reply_markup=home_kb(message.from_user.id))


@dp.message(PinState.waiting_for_unlock_pin)
async def pin_unlock_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_blocked(user_id):
        await state.clear()
        await message.answer(t(user_id, "pin_blocked"))
        return

    pin = message.text.strip()
    if not verify_pin(user_id, pin):
        register_failed_pin(user_id)
        await message.answer(t(user_id, "unlock_failed"))
        return

    clear_failed_pin(user_id)
    set_unlocked(user_id)
    await state.clear()
    await message.answer(t(user_id, "unlock_success"), reply_markup=home_kb(user_id))


@dp.message(PinState.waiting_for_old_pin_for_change)
async def pin_old_for_change(message: Message, state: FSMContext):
    user_id = message.from_user.id
    pin = message.text.strip()

    if not verify_pin(user_id, pin):
        await state.clear()
        await message.answer(t(user_id, "old_pin_wrong"), reply_markup=home_kb(user_id))
        return

    await state.set_state(PinState.waiting_for_change_new_pin)
    await message.answer(t(user_id, "ask_new_pin"))


@dp.message(PinState.waiting_for_change_new_pin)
async def pin_change_new(message: Message, state: FSMContext):
    pin = message.text.strip()
    if not is_valid_pin(pin):
        await message.answer(t(message.from_user.id, "pin_invalid"))
        return
    await state.update_data(change_new_pin=pin)
    await state.set_state(PinState.waiting_for_change_confirm_pin)
    await message.answer(t(message.from_user.id, "ask_confirm_pin"))


@dp.message(PinState.waiting_for_change_confirm_pin)
async def pin_change_confirm(message: Message, state: FSMContext):
    pin = message.text.strip()
    data = await state.get_data()
    if pin != data.get("change_new_pin"):
        await state.clear()
        await message.answer(t(message.from_user.id, "pin_not_match"), reply_markup=home_kb(message.from_user.id))
        return

    set_pin_hash(message.from_user.id, hash_pin(pin))
    set_unlocked(message.from_user.id)
    await state.clear()
    await message.answer(t(message.from_user.id, "pin_changed_success"), reply_markup=home_kb(message.from_user.id))


@dp.callback_query(F.data == "menu:create")
async def menu_create(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    await state.clear()
    await safe_edit(call, t(call.from_user.id, "create_type_menu"), create_type_kb(call.from_user.id))
    await call.answer()


@dp.callback_query(F.data.startswith("ptype:"))
async def create_type_select(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    password_type = call.data.split(":")[1]
    await state.update_data(password_type=password_type)
    await safe_edit(call, t(call.from_user.id, "choose_length"), length_kb(call.from_user.id))
    await call.answer()


@dp.callback_query(F.data.startswith("plen:"))
async def create_length_select(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return

    raw = call.data.split(":")[1]
    user_id = call.from_user.id

    if raw == "custom":
        await state.set_state(CreateState.waiting_for_custom_length)
        await safe_edit(call, t(user_id, "ask_custom_length"), one_back_kb(user_id, "menu:create"))
        await call.answer()
        return

    if not raw.isdigit():
        await call.answer(t(user_id, "invalid_length"), show_alert=True)
        return

    length = int(raw)
    if length < 4 or length > 64:
        await call.answer(t(user_id, "invalid_length"), show_alert=True)
        return

    await state.update_data(password_length=length)
    await state.set_state(CreateState.waiting_for_platform)
    await safe_edit(call, t(user_id, "ask_platform"), one_back_kb(user_id, "menu:create"))
    await call.answer()


@dp.message(CreateState.waiting_for_custom_length)
async def custom_length_input(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(t(message.from_user.id, "invalid_length"))
        return

    length = int(raw)
    if length < 4 or length > 64:
        await message.answer(t(message.from_user.id, "invalid_length"))
        return

    await state.update_data(password_length=length)
    await state.set_state(CreateState.waiting_for_platform)
    await message.answer(t(message.from_user.id, "ask_platform"))


@dp.message(CreateState.waiting_for_platform)
async def create_platform_input(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer(t(message.from_user.id, "ask_platform"))
        return
    await state.update_data(platform=text)
    await state.set_state(CreateState.waiting_for_login)
    await message.answer(t(message.from_user.id, "ask_login"), parse_mode="Markdown")


@dp.message(CreateState.waiting_for_login)
async def create_login_input(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(login="" if text == "-" else text)
    await state.set_state(CreateState.waiting_for_email)
    await message.answer(t(message.from_user.id, "ask_email"), parse_mode="Markdown")


@dp.message(CreateState.waiting_for_email)
async def create_email_input(message: Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(email="" if text == "-" else text)
    await state.set_state(CreateState.waiting_for_note)
    await message.answer(t(message.from_user.id, "ask_note"), parse_mode="Markdown")


@dp.message(CreateState.waiting_for_note)
async def create_note_input(message: Message, state: FSMContext):
    text = message.text.strip()
    note = "" if text == "-" else text

    data = await state.get_data()
    password_type = data.get("password_type", "all")
    password_length = data.get("password_length", 12)
    platform = data.get("platform", "")
    login = data.get("login", "")
    email = data.get("email", "")

    password = generate_password_by_type(password_type, password_length)
    save_vault_item(message.from_user.id, platform, login, email, password, note)
    await state.clear()

    await message.answer(
        t(message.from_user.id, "saved_item").format(
            platform=safe_value(platform),
            login=safe_value(login),
            email=safe_value(email),
            password=password,
            note=safe_value(note),
        ),
        parse_mode="Markdown",
        reply_markup=home_kb(message.from_user.id)
    )


@dp.callback_query(F.data == "menu:vault")
async def menu_vault(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    items = get_vault_items(call.from_user.id)
    await render_items_list(call, call.from_user.id, items, 0, False, "vault")
    await call.answer()


@dp.callback_query(F.data.startswith("vault:nav:"))
async def vault_nav(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    index = int(call.data.split(":")[2])
    items = get_vault_items(call.from_user.id)
    await render_items_list(call, call.from_user.id, items, index, False, "vault")
    await call.answer()


@dp.callback_query(F.data.startswith("vault:show:"))
async def vault_show(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    parts = call.data.split(":")
    item_id = int(parts[2])
    index = int(parts[3])

    item = get_vault_item(item_id, call.from_user.id)
    if not item:
        items = get_vault_items(call.from_user.id)
        await render_items_list(call, call.from_user.id, items, 0, False, "vault")
        await call.answer()
        return

    items = get_vault_items(call.from_user.id)
    await render_items_list(call, call.from_user.id, items, index, True, "vault")
    await call.answer(t(call.from_user.id, "copied_label"))


@dp.callback_query(F.data.startswith("vault:delete:"))
async def vault_delete(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    parts = call.data.split(":")
    item_id = int(parts[2])
    index = int(parts[3])

    delete_vault_item(item_id, call.from_user.id)
    items = get_vault_items(call.from_user.id)

    if not items:
        await safe_edit(call, t(call.from_user.id, "after_delete_empty"), home_kb(call.from_user.id))
        await call.answer()
        return

    await render_items_list(call, call.from_user.id, items, normalize_index(index, len(items)), False, "vault")
    await call.answer(t(call.from_user.id, "deleted"))


@dp.callback_query(F.data == "menu:search")
async def menu_search(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    await state.clear()
    await state.set_state(SearchState.waiting_for_query)
    await safe_edit(call, t(call.from_user.id, "search_prompt"), one_back_kb(call.from_user.id, "menu:home"))
    await call.answer()


@dp.message(SearchState.waiting_for_query)
async def search_query_input(message: Message, state: FSMContext):
    query = message.text.strip()
    results = search_vault_items(message.from_user.id, query)
    await state.clear()

    if not results:
        await message.answer(t(message.from_user.id, "search_no_results"), reply_markup=home_kb(message.from_user.id))
        return

    first = results[0]
    text = format_item_text(message.from_user.id, first, 1, len(results), False)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=vault_item_kb(message.from_user.id, 0, len(results), first["id"], source=f"search:{base64.urlsafe_b64encode(query.encode()).decode()}")
    )


@dp.callback_query(F.data.startswith("search:"))
async def search_callbacks(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return

    parts = call.data.split(":")
    query_b64 = parts[1]
    action = parts[2]
    query = base64.urlsafe_b64decode(query_b64.encode()).decode()
    results = search_vault_items(call.from_user.id, query)

    if not results:
        await safe_edit(call, t(call.from_user.id, "search_no_results"), home_kb(call.from_user.id))
        await call.answer()
        return

    if action == "nav":
        index = int(parts[3])
        await render_items_list(call, call.from_user.id, results, index, False, f"search:{query_b64}")
        await call.answer()
        return

    if action == "show":
        item_id = int(parts[3])
        index = int(parts[4])
        item = get_vault_item(item_id, call.from_user.id)
        if not item:
            await render_items_list(call, call.from_user.id, results, 0, False, f"search:{query_b64}")
            await call.answer()
            return
        await render_items_list(call, call.from_user.id, results, index, True, f"search:{query_b64}")
        await call.answer(t(call.from_user.id, "copied_label"))
        return

    if action == "delete":
        item_id = int(parts[3])
        index = int(parts[4])
        delete_vault_item(item_id, call.from_user.id)
        results = search_vault_items(call.from_user.id, query)
        if not results:
            await safe_edit(call, t(call.from_user.id, "search_no_results"), home_kb(call.from_user.id))
            await call.answer()
            return
        await render_items_list(call, call.from_user.id, results, normalize_index(index, len(results)), False, f"search:{query_b64}")
        await call.answer(t(call.from_user.id, "deleted"))
        return


@dp.callback_query(F.data.startswith("item:edit:"))
async def item_edit(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    _, _, item_id, source, index = call.data.split(":")
    await state.clear()
    await state.update_data(edit_item_id=int(item_id), edit_source=source, edit_index=int(index))
    await safe_edit(
        call,
        t(call.from_user.id, "edit_menu"),
        edit_fields_kb(call.from_user.id, int(item_id), source, int(index))
    )
    await call.answer()


@dp.callback_query(F.data.startswith("editfield:"))
async def edit_field_select(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    _, field, item_id, source, index = call.data.split(":")
    await state.clear()
    await state.update_data(edit_field=field, edit_item_id=int(item_id), edit_source=source, edit_index=int(index))
    await state.set_state(EditState.waiting_for_new_value)
    await safe_edit(call, t(call.from_user.id, "ask_new_value"), one_back_kb(call.from_user.id, "menu:home"))
    await call.answer()


@dp.message(EditState.waiting_for_new_value)
async def edit_value_input(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("edit_field")
    item_id = data.get("edit_item_id")
    value = message.text.strip()
    update_vault_field(item_id, message.from_user.id, field, value)
    await state.clear()
    await message.answer(t(message.from_user.id, "updated_success"), reply_markup=home_kb(message.from_user.id))


@dp.callback_query(F.data.startswith("item:regen:"))
async def item_regen(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    _, _, item_id, source, index = call.data.split(":")
    new_password = generate_password_by_type("all", 16)
    update_vault_field(int(item_id), call.from_user.id, "password", new_password)

    if source.startswith("search"):
        query_b64 = source.split("search", 1)[1]
        # fallback to home due to compact structure
        await safe_edit(call, t(call.from_user.id, "regen_done"), home_kb(call.from_user.id))
    else:
        items = get_vault_items(call.from_user.id)
        await render_items_list(call, call.from_user.id, items, int(index), True, "vault")
    await call.answer(t(call.from_user.id, "regen_done"))


@dp.callback_query(F.data == "settings:export")
async def settings_export(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return

    items = get_vault_items(call.from_user.id)
    if not items:
        await call.answer(t(call.from_user.id, "empty_vault"), show_alert=True)
        return

    lines = []
    for idx, item in enumerate(items, start=1):
        lines.append(f"{idx}. Platform: {safe_value(item['platform'])}")
        lines.append(f"   Login: {safe_value(item['login'])}")
        lines.append(f"   Email: {safe_value(item['email'])}")
        lines.append(f"   Password: {decrypt_text(item['password'])}")
        lines.append(f"   Note: {safe_value(item['note'])}")
        lines.append("")

    content = "\n".join(lines).encode()
    file = BufferedInputFile(content, filename="vault_export.txt")
    await call.message.answer_document(file)
    await call.answer()


@dp.callback_query(F.data == "settings:delete_all")
async def settings_delete_all(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    await safe_edit(call, t(call.from_user.id, "confirm_delete_all"), confirm_delete_all_kb(call.from_user.id))
    await call.answer()


@dp.callback_query(F.data == "settings:delete_all_yes")
async def settings_delete_all_yes(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    delete_all_vault_items(call.from_user.id)
    await safe_edit(call, t(call.from_user.id, "all_deleted"), home_kb(call.from_user.id))
    await call.answer()


@dp.callback_query(F.data == "settings:delete_all_no")
async def settings_delete_all_no(call: CallbackQuery, state: FSMContext):
    if not await ensure_unlocked(call, state):
        await call.answer()
        return
    await safe_edit(call, t(call.from_user.id, "settings_text"), settings_kb(call.from_user.id))
    await call.answer()


@dp.message()
async def fallback(message: Message):
    user_id = message.from_user.id
    if user_id not in USER_LANG:
        await message.answer(TEXTS["uz"]["choose_lang"], reply_markup=lang_kb())
        return

    text = t(user_id, "main_menu_unlocked") if is_unlocked(user_id) else t(user_id, "main_menu_locked")
    await message.answer(text, reply_markup=home_kb(user_id))


async def main():
    global FERNET
    init_db()
    FERNET = Fernet(get_secret_key())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
