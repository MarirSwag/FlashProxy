import aiohttp
import aiofiles
import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    Message
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===================== НАСТРОЙКИ =====================
API_KEY = "2ceb6b52bf-9b7fd55343-c444559a23"
BOT_TOKEN = "8124149270:AAFRVZ_q6rA9f9cScJIEs0lxYYYFlEGapvI"
ADMIN_ID = 1967888210

PAYMENT_LINK = "https://www.tbank.ru/cf/5COiqw9ez0B"
SUPPORT_LINK = "https://t.me/BloodMichine"

ULTRA_LINK = (
    "https://t.me/socks?server=193.58.122.141"
    "&port=122&user=nordox&pass=johsiv-Tekmi1-riwpyt"
)
ULTRA_PRICE = 99
ULTRA_STARS = 145

BASE_URL = f"https://px6.link/api/{API_KEY}"
PROXY_VERSION = 4
PROXY_TYPE = "socks"
PROXY_COUNTRY = "kz"

DATA_FILE = "bot_data.json"

maintenance_mode = False
file_lock = asyncio.Lock()

# ===================== ПЕРИОДЫ И ЦЕНЫ =====================
PERIODS = {
    "7": {"name": "1 неделя", "price": 50, "days": 7, "stars": 75},
    "30": {"name": "1 месяц", "price": 199, "days": 30, "stars": 290},
    "60": {"name": "2 месяца", "price": 349, "days": 60, "stars": 500},
    "90": {"name": "3 месяца", "price": 499, "days": 90, "stars": 720},
}

# ===================== ТЕКСТЫ =====================
INSTRUCTION_TEXT = (
    "🛠 <b>Как запустить Flash Proxy за 10 секунд:</b>\n\n"
    "1️⃣ <b>Получи ссылку</b> — После оплаты бот "
    "пришлёт тебе специальную ссылку.\n\n"
    "2️⃣ <b>Нажми на неё</b> — Telegram сам "
    "откроет настройки прокси.\n\n"
    "3️⃣ <b>Нажми «Включить» (Enable)</b> — И всё! "
    "В верхней части списка чатов появится "
    "значок щита 🛡. Это значит, что ты под "
    "защитой и на максимальной скорости.\n\n"
    "💡 <b>Включать VPN больше не нужно!</b> "
    "Telegram будет работать сам по себе."
)

HOW_IT_WORKS_TEXT = (
    "⚡️ <b>Как работает Flash Proxy?</b>\n\n"
    "Всё максимально просто: мы не заставляем "
    "тебя скачивать тяжёлые приложения. Мы "
    "используем встроенную функцию самого "
    "Telegram.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🛠 <b>1. Подключение в один клик</b>\n"
    "После оплаты бот выдаёт тебе «магическую» "
    "ссылку. Ты нажимаешь на неё, и Telegram сам "
    "настраивает соединение. 10 секунд — "
    "и ты в сети.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🏆 <b>2. Почему это лучше любого VPN?</b>\n\n"
    "🎯 <b>Точечная работа</b>\n"
    "Прокси работает только внутри Telegram. "
    "Твой Сбербанк, Госуслуги и игры будут "
    "работать через обычный интернет без "
    "лагов и блокировок.\n\n"
    "🔋 <b>Экономия заряда</b>\n"
    "Телефон не тратит энергию на работу "
    "фонового VPN-сервиса. Батарея живёт "
    "дольше.\n\n"
    "🚀 <b>Стабильная скорость</b>\n"
    "Фото, тяжёлые видео и «кружочки» будут "
    "грузиться мгновенно. Никаких "
    "«Connecting...» по три минуты.\n\n"
    "🛡 <b>Личный канал</b>\n"
    "В отличие от бесплатных VPN, где на одном "
    "сервере сидят тысячи людей, здесь ты "
    "получаешь выделенный канал связи.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "💡 <b>Итог:</b> Ты один раз включаешь "
    "Flash Proxy, и Telegram работает всегда, "
    "а ты даже не замечаешь блокировок."
)

ULTRA_TEXT = (
    "🛡 <b>Flash Proxy ULTRA — Обход блокировок "
    "Telegram навсегда!</b>\n\n"
    "Забудь про ежемесячные списания. "
    "Один платёж — и Telegram работает всегда.\n\n"
    "💸 Цена: <b>Всего 99 ₽</b> (Единоразово)\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "✅ Telegram работает без VPN\n"
    "✅ Все сообщения и медиа летают\n"
    "✅ Подключение в один клик\n"
    "✅ Работает навсегда — платишь один раз\n\n"
    "⚠️ <i>Shared канал — на сервере могут быть "
    "другие пользователи</i>\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Выбери способ оплаты 👇"
)

MAINTENANCE_TEXT = (
    "🔧 <b>Тех. работы</b>\n\n"
    "Бот временно на обслуживании.\n"
    "Попробуй позже — скоро всё заработает!"
)

# ===================== ЛОГИРОВАНИЕ =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== БОТ =====================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

pending_payments = {}


# ===================== ХРАНИЛИЩЕ (ASYNC) =====================
async def load_data() -> dict:
    async with file_lock:
        if os.path.exists(DATA_FILE):
            try:
                async with aiofiles.open(DATA_FILE, "r") as f:
                    content = await f.read()
                    return json.loads(content)
            except:
                pass
        return {"users": {}, "proxies": {}}


async def save_data(data: dict):
    async with file_lock:
        tmp_file = DATA_FILE + ".tmp"
        async with aiofiles.open(tmp_file, "w") as f:
            await f.write(
                json.dumps(data, ensure_ascii=False, indent=2)
            )
        os.replace(tmp_file, DATA_FILE)


async def save_user(
    user_id: int, first_name: str, username: str
) -> bool:
    data = await load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "first_name": first_name,
            "username": username or "",
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        await save_data(data)
        return True
    return False


async def save_proxy(user_id: int, proxy_info: dict):
    data = await load_data()
    uid = str(user_id)
    if uid not in data["proxies"]:
        data["proxies"][uid] = []
    data["proxies"][uid].append(proxy_info)
    await save_data(data)


async def get_user_proxies(user_id: int) -> list:
    data = await load_data()
    return data["proxies"].get(str(user_id), [])


async def get_all_proxies() -> dict:
    data = await load_data()
    return data["proxies"]


# ===================== СОСТОЯНИЯ =====================
class BuyProxy(StatesGroup):
    choosing_type = State()
    choosing_period = State()
    choosing_payment = State()
    waiting_confirm = State()


class BroadcastState(StatesGroup):
    waiting_message = State()


# ===================== PROXY6 API (ASYNC) =====================
async def api_get_balance() -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                BASE_URL,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                if data["status"] == "yes":
                    return {
                        "ok": True,
                        "balance": data["balance"],
                        "currency": data["currency"],
                    }
                return {
                    "ok": False,
                    "error": data.get("error", "?")
                }
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def api_get_count(country: str) -> dict:
    try:
        url = (
            f"{BASE_URL}/getcount"
            f"?country={country}&version={PROXY_VERSION}"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                if data["status"] == "yes":
                    return {"ok": True, "count": data["count"]}
                return {
                    "ok": False,
                    "error": data.get("error", "?")
                }
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def api_check_before_buy(
    country: str, period: int
) -> dict:
    count = await api_get_count(country)
    if count["ok"] and int(count["count"]) == 0:
        return {"ok": False, "error": "Нет прокси в наличии"}
    try:
        url = (
            f"{BASE_URL}/getprice"
            f"?count=1&period={period}&version={PROXY_VERSION}"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                if data["status"] == "yes":
                    price = float(data["price"])
                    balance_data = await api_get_balance()
                    if balance_data["ok"]:
                        balance = float(
                            balance_data["balance"]
                        )
                        if balance < price:
                            return {
                                "ok": False,
                                "error": "Временно нет в наличии"
                            }
        return {"ok": True}
    except:
        return {"ok": True}


async def api_buy_proxy(country: str, period: int) -> dict:
    try:
        url = (
            f"{BASE_URL}/buy"
            f"?count=1"
            f"&period={period}"
            f"&country={country}"
            f"&version={PROXY_VERSION}"
            f"&type={PROXY_TYPE}"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                logger.info(f"buy response: {data}")

                if data["status"] == "yes":
                    proxy_key = list(data["list"].keys())[0]
                    p = data["list"][proxy_key]
                    return {
                        "ok": True,
                        "id": p["id"],
                        "host": p["host"],
                        "port": p["port"],
                        "user": p["user"],
                        "pass": p["pass"],
                        "type": p["type"],
                        "date_end": p["date_end"],
                    }
                else:
                    error_id = data.get("error_id", 0)
                    errors = {
                        400: "Недостаточно средств на балансе",
                        300: "Нет доступных прокси",
                        220: "Ошибка страны",
                        210: "Ошибка периода",
                    }
                    return {
                        "ok": False,
                        "error": errors.get(
                            error_id,
                            data.get(
                                "error", "Неизвестная ошибка"
                            )
                        ),
                    }
    except Exception as e:
        logger.error(f"Buy error: {e}")
        return {"ok": False, "error": str(e)}


async def api_check_proxy(proxy_id: str) -> dict:
    try:
        url = f"{BASE_URL}/check?ids={proxy_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()
                if data["status"] == "yes":
                    return {
                        "ok": True,
                        "working": data.get(
                            "proxy_status", False
                        ),
                    }
                return {
                    "ok": False,
                    "error": data.get("error", "?")
                }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ===================== ВЫДАЧА ULTRA =====================
async def deliver_ultra(chat_id: int):
    await save_proxy(chat_id, {
        "id": "ultra_shared",
        "host": "193.58.122.141",
        "port": "122",
        "user": "nordox",
        "pass": "johsiv-Tekmi1-riwpyt",
        "tariff": "♾ ULTRA",
        "tariff_key": "ultra",
        "country": "🛡 Flash Proxy",
        "period": "Навсегда",
        "period_key": "forever",
        "price": ULTRA_PRICE,
        "date_end": "2099-12-31 23:59:59",
        "bought": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

    await bot.send_message(
        chat_id,
        f"✅ <b>Flash Proxy ULTRA активирован!</b>\n\n"
        f"📦 Тариф: <b>♾ ULTRA — Навсегда</b>\n"
        f"🔧 Тип: <b>Shared SOCKS5</b>\n"
        f"💵 Оплачено: <b>{ULTRA_PRICE} ₽</b>\n"
        f"⏰ Срок: <b>Навсегда ♾</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🖥 Сервер: <code>193.58.122.141</code>\n"
        f"🚪 Порт: <code>122</code>\n"
        f"👤 Логин: <code>nordox</code>\n"
        f"🔑 Пароль: <code>"
        f"johsiv-Tekmi1-riwpyt</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 <b>Ссылка для Telegram (SOCKS5):</b>\n"
        f"👇 Нажми — прокси подключится\n\n"
        f"{ULTRA_LINK}",
        reply_markup=after_buy_kb(),
        parse_mode="HTML"
    )


# ===================== ВЫДАЧА ПРОКСИ =====================
async def deliver_proxy(chat_id: int, period_key: str):
    period_data = PERIODS.get(period_key, PERIODS["7"])

    result = await api_buy_proxy(
        country=PROXY_COUNTRY,
        period=period_data["days"]
    )

    if result["ok"]:
        host = result["host"]
        port = result["port"]
        user = result["user"]
        password = result["pass"]
        date_end = result["date_end"]
        proxy_id = result["id"]

        tg_link = (
            f"https://t.me/socks"
            f"?server={host}"
            f"&port={port}"
            f"&user={user}"
            f"&pass={password}"
        )
        raw = f"{host}:{port}:{user}:{password}"

        await save_proxy(chat_id, {
            "id": str(proxy_id),
            "host": host,
            "port": port,
            "user": user,
            "pass": password,
            "tariff": "🛡 Обход блокировок",
            "tariff_key": "proxy",
            "country": "🛡 Flash Proxy",
            "period": period_data["name"],
            "period_key": period_key,
            "price": period_data["price"],
            "date_end": date_end,
            "bought": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })

        await bot.send_message(
            chat_id,
            f"✅ <b>Прокси готов!</b>\n\n"
            f"📦 Тариф: <b>🛡 Обход блокировок Telegram</b>\n"
            f"🔧 Тип: <b>SOCKS5 (Личный)</b>\n"
            f"📅 Срок: <b>{period_data['name']}</b>\n"
            f"💵 Оплачено: <b>{period_data['price']} ₽</b>\n"
            f"⏰ Действует до: <b>{date_end}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🖥 Сервер: <code>{host}</code>\n"
            f"🚪 Порт: <code>{port}</code>\n"
            f"👤 Логин: <code>{user}</code>\n"
            f"🔑 Пароль: <code>{password}</code>\n\n"
            f"📋 Строка: <code>{raw}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 <b>Ссылка для Telegram (SOCKS5):</b>\n"
            f"👇 Нажми — прокси подключится\n\n"
            f"{tg_link}",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )
        logger.info(
            f"Delivered proxy to {chat_id}: {host}:{port}"
        )
    else:
        await bot.send_message(
            chat_id,
            f"❌ <b>Ошибка:</b> {result['error']}\n\n"
            f"Напиши в поддержку для решения проблемы.",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )


# ===================== КЛАВИАТУРЫ =====================
def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛡 Купить прокси",
            callback_data="buy"
        )],
        [InlineKeyboardButton(
            text="📋 Мои прокси",
            callback_data="my_proxies"
        )],
        [
            InlineKeyboardButton(
                text="📖 Инструкция",
                callback_data="instruction"
            ),
            InlineKeyboardButton(
                text="⚡️ Как это работает?",
                callback_data="how_it_works"
            ),
        ],
        [InlineKeyboardButton(
            text="💬 Поддержка",
            url=SUPPORT_LINK
        )],
    ])


def type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛡 Личный прокси (по периоду)",
            callback_data="type_personal"
        )],
        [InlineKeyboardButton(
            text="♾ ULTRA — Навсегда за 99₽",
            callback_data="type_ultra"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        )],
    ])


def period_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"📅 {p['name']} — {p['price']} ₽",
            callback_data=f"period_{code}"
        )]
        for code, p in PERIODS.items()
    ]
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад", callback_data="buy"
        ),
        InlineKeyboardButton(
            text="❌ Отмена", callback_data="cancel"
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_kb(period_key: str) -> InlineKeyboardMarkup:
    period_data = PERIODS[period_key]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⭐ Telegram Stars ({period_data['stars']} ⭐)",
            callback_data="pay_stars"
        )],
        [InlineKeyboardButton(
            text=f"💳 Перевод ({period_data['price']} ₽)",
            callback_data="pay_link"
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back_period"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        )],
    ])


def ultra_payment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⭐ Telegram Stars ({ULTRA_STARS} ⭐)",
            callback_data="pay_stars_ultra"
        )],
        [InlineKeyboardButton(
            text=f"💳 Перевод ({ULTRA_PRICE} ₽)",
            callback_data="pay_link_ultra"
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="buy"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        )],
    ])


def after_buy_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛡 Купить ещё",
            callback_data="buy"
        )],
        [InlineKeyboardButton(
            text="📖 Инструкция",
            callback_data="instruction"
        )],
        [
            InlineKeyboardButton(
                text="💬 Поддержка",
                url=SUPPORT_LINK
            ),
            InlineKeyboardButton(
                text="⬅️ Меню",
                callback_data="menu"
            ),
        ],
    ])


def info_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛡 Купить прокси",
            callback_data="buy"
        )],
        [InlineKeyboardButton(
            text="⬅️ Меню",
            callback_data="menu"
        )],
    ])


def menu_btn() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⬅️ Меню", callback_data="menu"
        )]
    ])


def admin_kb() -> InlineKeyboardMarkup:
    global maintenance_mode
    if maintenance_mode:
        maint_text = "✅ Тех. работы ВКЛ — выключить"
    else:
        maint_text = "🔧 Тех. работы ВЫКЛ — включить"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="adm_stats"
        )],
        [InlineKeyboardButton(
            text="👥 Пользователи",
            callback_data="adm_users"
        )],
        [InlineKeyboardButton(
            text="🟢 Активные прокси",
            callback_data="adm_active"
        )],
        [InlineKeyboardButton(
            text="💰 Баланс Proxy6",
            callback_data="adm_balance"
        )],
        [InlineKeyboardButton(
            text="📢 Рассылка",
            callback_data="adm_broadcast"
        )],
        [InlineKeyboardButton(
            text=maint_text,
            callback_data="adm_maintenance"
        )],
    ])


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⬅️ Админ-панель",
            callback_data="adm_back"
        )]
    ])


# ===================== ТЕХ. РАБОТЫ =====================
def is_maintenance(user_id: int) -> bool:
    global maintenance_mode
    return maintenance_mode and user_id != ADMIN_ID


# ===================== АДМИН ТЕКСТ =====================
async def get_admin_text() -> str:
    data = await load_data()
    total_users = len(data["users"])
    total_proxies = active_proxies = total_income = 0

    for uid, proxies in data["proxies"].items():
        for p in proxies:
            total_proxies += 1
            total_income += p.get("price", 0)
            try:
                end_date = datetime.strptime(
                    p["date_end"], "%Y-%m-%d %H:%M:%S"
                )
                if end_date > datetime.now():
                    active_proxies += 1
            except:
                pass

    balance = await api_get_balance()
    balance_text = (
        f"{balance['balance']} {balance['currency']}"
        if balance["ok"] else "Ошибка"
    )

    global maintenance_mode
    maint_status = "🔴 ВКЛ" if maintenance_mode else "🟢 ВЫКЛ"

    return (
        f"👑 <b>Админ-панель</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"├ 👥 Пользователей: <b>{total_users}</b>\n"
        f"├ 📦 Всего покупок: <b>{total_proxies}</b>\n"
        f"├ 🟢 Активных: <b>{active_proxies}</b>\n"
        f"├ 💵 Доход: <b>{total_income} ₽</b>\n"
        f"├ 💰 Proxy6: <b>{balance_text}</b>\n"
        f"└ 🔧 Тех. работы: <b>{maint_status}</b>\n\n"
        f"Выбери действие 👇"
    )


# ===================== ОБРАБОТЧИКИ =====================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user

    if is_maintenance(user.id):
        await message.answer(MAINTENANCE_TEXT, parse_mode="HTML")
        return

    is_new = await save_user(
        user.id, user.first_name, user.username
    )

    if is_new:
        user_link = (
            f'<a href="tg://user?id={user.id}">'
            f'{user.first_name}</a>'
        )
        username_text = (
            f"@{user.username}" if user.username else "нет"
        )
        data = await load_data()
        total_users = len(data["users"])
        try:
            await bot.send_message(
                ADMIN_ID,
                f"👤 <b>Новый пользователь!</b>\n\n"
                f"├ Имя: {user_link}\n"
                f"├ Username: {username_text}\n"
                f"├ ID: <code>{user.id}</code>\n"
                f"└ Всего: <b>{total_users}</b>",
                parse_mode="HTML"
            )
        except:
            pass

    await message.answer(
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"🛡 <b>Flash Proxy — Обход блокировок "
        f"Telegram</b>\n\n"
        f"Telegram не работает? Сообщения не "
        f"отправляются? Медиа не грузится?\n\n"
        f"Flash Proxy решает это <b>за 10 секунд</b>.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛡 <b>Личный прокси (выделенный):</b>\n"
        f"├ 1 неделя — <b>50 ₽</b>\n"
        f"├ 1 месяц — <b>199 ₽</b>\n"
        f"├ 2 месяца — <b>349 ₽</b>\n"
        f"└ 3 месяца — <b>499 ₽</b>\n\n"
        f"♾ <b>ULTRA (общий канал):</b>\n"
        f"└ Навсегда — <b>99 ₽</b>\n\n"
        f"💳 <b>Способы оплаты:</b>\n"
        f"├ ⭐ Telegram Stars\n"
        f"└ 💳 Перевод по ссылке\n\n"
        f"Нажми <b>«Купить прокси»</b> 👇",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if is_maintenance(callback.from_user.id):
        await callback.message.edit_text(
            MAINTENANCE_TEXT, parse_mode="HTML"
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыбери действие:",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Отменено.",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "instruction")
async def cb_instruction(callback: CallbackQuery):
    await callback.message.edit_text(
        INSTRUCTION_TEXT,
        reply_markup=info_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "how_it_works")
async def cb_how_it_works(callback: CallbackQuery):
    await callback.message.edit_text(
        HOW_IT_WORKS_TEXT,
        reply_markup=info_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== МОИ ПРОКСИ ==========
@dp.callback_query(F.data == "my_proxies")
async def cb_my_proxies(callback: CallbackQuery):
    if is_maintenance(callback.from_user.id):
        await callback.message.edit_text(
            MAINTENANCE_TEXT, parse_mode="HTML"
        )
        await callback.answer()
        return

    proxies = await get_user_proxies(callback.from_user.id)

    if not proxies:
        await callback.message.edit_text(
            "📋 <b>Мои прокси</b>\n\n"
            "У тебя пока нет прокси.\n"
            "Нажми «Купить» чтобы начать!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🛡 Купить прокси",
                    callback_data="buy"
                )],
                [InlineKeyboardButton(
                    text="⬅️ Меню", callback_data="menu"
                )],
            ]),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text = f"📋 <b>Мои прокси ({len(proxies)} шт.):</b>\n\n"

    for i, p in enumerate(proxies[-5:], 1):
        try:
            end_date = datetime.strptime(
                p["date_end"], "%Y-%m-%d %H:%M:%S"
            )
            if end_date > datetime.now():
                days_left = (end_date - datetime.now()).days
                if days_left > 3650:
                    status = "♾ Навсегда"
                else:
                    status = f"🟢 Активен ({days_left} дн.)"
            else:
                status = "🔴 Истёк"
        except:
            status = "⚪ Неизвестно"

        tg_link = (
            f"https://t.me/socks"
            f"?server={p['host']}"
            f"&port={p['port']}"
            f"&user={p['user']}"
            f"&pass={p['pass']}"
        )

        tariff_name = p.get("tariff", "🛡 Обход блокировок")

        text += (
            f"<b>{i}.</b> {tariff_name}\n"
            f"├ Срок: {p.get('period', '?')}\n"
            f"├ {status}\n"
            f"├ <code>{p['host']}:{p['port']}"
            f":{p['user']}:{p['pass']}</code>\n"
            f"└ Ссылка: {tg_link}\n\n"
        )

    buttons = []
    for i, p in enumerate(proxies[-5:], 1):
        if p.get("id") != "ultra_shared":
            try:
                end_date = datetime.strptime(
                    p["date_end"], "%Y-%m-%d %H:%M:%S"
                )
                if end_date > datetime.now():
                    buttons.append([InlineKeyboardButton(
                        text=f"🔍 Проверить прокси #{i}",
                        callback_data=f"check_{p['id']}"
                    )])
            except:
                pass

    buttons.append([InlineKeyboardButton(
        text="🛡 Купить ещё", callback_data="buy"
    )])
    buttons.append([InlineKeyboardButton(
        text="⬅️ Меню", callback_data="menu"
    )])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("check_"))
async def cb_check_proxy(callback: CallbackQuery):
    proxy_id = callback.data.split("_")[1]
    await callback.answer("🔍 Проверяю...")
    result = await api_check_proxy(proxy_id)
    if result["ok"]:
        if result["working"]:
            await callback.answer(
                "✅ Прокси работает!", show_alert=True
            )
        else:
            await callback.answer(
                "❌ Прокси не работает. "
                "Напиши в поддержку.",
                show_alert=True
            )
    else:
        await callback.answer(
            f"⚠️ Ошибка: {result['error']}",
            show_alert=True
        )


# ========== ШАГ 1: ВЫБОР ТИПА ==========
@dp.callback_query(F.data == "buy")
async def cb_buy(callback: CallbackQuery, state: FSMContext):
    if is_maintenance(callback.from_user.id):
        await callback.message.edit_text(
            MAINTENANCE_TEXT, parse_mode="HTML"
        )
        await callback.answer()
        return

    await state.clear()
    await state.set_state(BuyProxy.choosing_type)
    await callback.message.edit_text(
        "🛡 <b>Обход блокировок Telegram</b>\n\n"
        "Выбери тип прокси:\n\n"
        "🛡 <b>Личный прокси</b>\n"
        "├ Выделенный сервер только для тебя\n"
        "├ Максимальная скорость\n"
        "└ Оплата по периоду\n\n"
        "♾ <b>ULTRA</b>\n"
        "├ Общий канал\n"
        "├ Один платёж — работает навсегда\n"
        "└ Всего 99 ₽",
        reply_markup=type_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== ЛИЧНЫЙ ПРОКСИ → ПЕРИОД ==========
@dp.callback_query(
    F.data == "type_personal",
    BuyProxy.choosing_type
)
async def cb_type_personal(
    callback: CallbackQuery, state: FSMContext
):
    await state.set_state(BuyProxy.choosing_period)

    await callback.message.edit_text(
        "🛡 <b>Личный прокси — Обход блокировок</b>\n\n"
        "✅ Выделенный сервер только для тебя\n"
        "✅ Максимальная скорость\n"
        "✅ Работает при любых блокировках\n"
        "✅ Подключение в один клик\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📅 <b>Выбери срок:</b>",
        reply_markup=period_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "back_period")
async def cb_back_period(
    callback: CallbackQuery, state: FSMContext
):
    await state.set_state(BuyProxy.choosing_period)
    await callback.message.edit_text(
        "🛡 <b>Личный прокси — Обход блокировок</b>\n\n"
        "✅ Выделенный сервер только для тебя\n"
        "✅ Максимальная скорость\n"
        "✅ Работает при любых блокировках\n"
        "✅ Подключение в один клик\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📅 <b>Выбери срок:</b>",
        reply_markup=period_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== ШАГ 2: ОПЛАТА ЛИЧНОГО ==========
@dp.callback_query(
    F.data.startswith("period_"),
    BuyProxy.choosing_period
)
async def cb_period(callback: CallbackQuery, state: FSMContext):
    period_key = callback.data.split("_")[1]
    period_data = PERIODS.get(period_key)
    if not period_data:
        await callback.answer(
            "Период не найден", show_alert=True
        )
        return

    await state.update_data(period=period_key)
    await state.set_state(BuyProxy.choosing_payment)

    await callback.message.edit_text(
        f"🧾 <b>Твой заказ:</b>\n\n"
        f"📦 Тариф: <b>🛡 Обход блокировок Telegram</b>\n"
        f"🔧 Тип: <b>SOCKS5 (Личный)</b>\n"
        f"📅 Срок: <b>{period_data['name']}</b>\n"
        f"💵 Цена: <b>{period_data['price']} ₽</b>\n\n"
        f"💳 <b>Выбери способ оплаты:</b>",
        reply_markup=payment_kb(period_key),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== STARS ЛИЧНЫЙ ==========
@dp.callback_query(
    F.data == "pay_stars",
    BuyProxy.choosing_payment
)
async def cb_pay_stars(
    callback: CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    period_key = data.get("period", "7")
    period_data = PERIODS.get(period_key, PERIODS["7"])

    check = await api_check_before_buy(
        PROXY_COUNTRY, period_data["days"]
    )
    if not check["ok"]:
        await state.clear()
        await callback.message.edit_text(
            f"❌ <b>{check['error']}</b>\n\n"
            f"Попробуй позже или напиши в поддержку.",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await state.clear()

    prices = [
        LabeledPrice(
            label=(
                f"🛡 Обход блокировок — "
                f"{period_data['name']}"
            ),
            amount=period_data["stars"]
        )
    ]

    await callback.message.delete()

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="🛡 Flash Proxy — Обход блокировок",
        description=(
            f"Личный SOCKS5 прокси\n"
            f"Срок: {period_data['name']}\n"
            f"Подключение в один клик"
        ),
        payload=f"proxy:{period_key}",
        currency="XTR",
        prices=prices,
    )
    await callback.answer()


# ========== ССЫЛКА ЛИЧНЫЙ ==========
@dp.callback_query(
    F.data == "pay_link",
    BuyProxy.choosing_payment
)
async def cb_pay_link(
    callback: CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    period_key = data.get("period", "7")
    period_data = PERIODS.get(period_key, PERIODS["7"])

    check = await api_check_before_buy(
        PROXY_COUNTRY, period_data["days"]
    )
    if not check["ok"]:
        await state.clear()
        await callback.message.edit_text(
            f"❌ <b>{check['error']}</b>\n\n"
            f"Попробуй позже или напиши в поддержку.",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await state.set_state(BuyProxy.waiting_confirm)
    await state.update_data(period=period_key)

    pending_payments[callback.from_user.id] = {
        "tariff": "proxy",
        "period": period_key,
    }

    await callback.message.edit_text(
        f"💳 <b>Оплата переводом</b>\n\n"
        f"📦 Заказ: <b>🛡 Обход блокировок — "
        f"{period_data['name']}</b>\n"
        f"💵 Сумма: <b>{period_data['price']} ₽</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Инструкция:</b>\n\n"
        f"1️⃣ Нажми кнопку <b>«Оплатить»</b> ниже\n"
        f"2️⃣ Переведи ровно "
        f"<b>{period_data['price']} ₽</b>\n"
        f"3️⃣ Вернись сюда и нажми "
        f"<b>«Я оплатил»</b>\n"
        f"4️⃣ Админ проверит и ты получишь "
        f"прокси 🎉\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏰ Проверка обычно занимает до 15 минут",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💳 Оплатить {period_data['price']} ₽",
                url=PAYMENT_LINK
            )],
            [InlineKeyboardButton(
                text="✅ Я оплатил",
                callback_data="paid_link"
            )],
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel"
            )],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== ULTRA ==========
@dp.callback_query(
    F.data == "type_ultra",
    BuyProxy.choosing_type
)
async def cb_ultra(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BuyProxy.choosing_payment)
    await state.update_data(tariff="ultra")

    await callback.message.edit_text(
        ULTRA_TEXT,
        reply_markup=ultra_payment_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(
    F.data == "pay_stars_ultra",
    BuyProxy.choosing_payment
)
async def cb_ultra_stars(
    callback: CallbackQuery, state: FSMContext
):
    await state.clear()

    prices = [
        LabeledPrice(
            label="♾ Flash Proxy ULTRA — Навсегда",
            amount=ULTRA_STARS
        )
    ]

    await callback.message.delete()

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="♾ Flash Proxy ULTRA",
        description=(
            "SOCKS5 прокси навсегда\n"
            "Обход блокировок Telegram\n"
            "Один платёж — работает всегда"
        ),
        payload="ultra:forever",
        currency="XTR",
        prices=prices,
    )
    await callback.answer()


@dp.callback_query(
    F.data == "pay_link_ultra",
    BuyProxy.choosing_payment
)
async def cb_ultra_link(
    callback: CallbackQuery, state: FSMContext
):
    await state.set_state(BuyProxy.waiting_confirm)

    pending_payments[callback.from_user.id] = {
        "tariff": "ultra",
        "period": "forever",
    }

    await callback.message.edit_text(
        f"💳 <b>Оплата ULTRA</b>\n\n"
        f"📦 Заказ: <b>♾ Flash Proxy ULTRA</b>\n"
        f"💵 Сумма: <b>{ULTRA_PRICE} ₽</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Инструкция:</b>\n\n"
        f"1️⃣ Нажми кнопку <b>«Оплатить»</b>\n"
        f"2️⃣ Переведи ровно <b>{ULTRA_PRICE} ₽</b>\n"
        f"3️⃣ Вернись и нажми <b>«Я оплатил»</b>\n"
        f"4️⃣ Получи прокси навсегда 🎉\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏰ Проверка до 15 минут",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💳 Оплатить {ULTRA_PRICE} ₽",
                url=PAYMENT_LINK
            )],
            [InlineKeyboardButton(
                text="✅ Я оплатил",
                callback_data="paid_link"
            )],
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel"
            )],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== ОПЛАТА STARS (общий хэндлер) ==========
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    parts = payload.split(":")
    tariff_key = parts[0]
    period_key = parts[1]

    if tariff_key == "ultra":
        await message.answer(
            "⏳ <b>Оплата получена! "
            "Активирую прокси...</b>",
            parse_mode="HTML"
        )
        await deliver_ultra(message.from_user.id)
    else:
        await message.answer(
            "⏳ <b>Оплата получена! "
            "Покупаю прокси...</b>",
            parse_mode="HTML"
        )
        await deliver_proxy(
            chat_id=message.from_user.id,
            period_key=period_key
        )


# ========== Я ОПЛАТИЛ ==========
@dp.callback_query(F.data == "paid_link")
async def cb_paid_link(
    callback: CallbackQuery, state: FSMContext
):
    await state.clear()
    user = callback.from_user
    payment = pending_payments.get(user.id)

    if not payment:
        await callback.message.edit_text(
            "❌ Заявка не найдена. Попробуй заново.",
            reply_markup=main_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    if payment["tariff"] == "ultra":
        tariff_name = "♾ ULTRA"
        period_name = "Навсегда"
        price = ULTRA_PRICE
    else:
        period_data = PERIODS.get(
            payment["period"], PERIODS["7"]
        )
        tariff_name = "🛡 Обход блокировок"
        period_name = period_data["name"]
        price = period_data["price"]

    user_link = (
        f'<a href="tg://user?id={user.id}">'
        f'{user.first_name}</a>'
    )

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"💳 <b>Новая оплата по ссылке!</b>\n\n"
            f"👤 Клиент: {user_link}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📦 Тариф: <b>{tariff_name}</b>\n"
            f"📅 Срок: <b>{period_name}</b>\n"
            f"💵 Сумма: <b>{price} ₽</b>\n\n"
            f"Проверь поступление и нажми кнопку 👇"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"approve_{user.id}"
            )],
            [InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"reject_{user.id}"
            )],
        ]),
        parse_mode="HTML"
    )

    await callback.message.edit_text(
        "✅ <b>Заявка отправлена!</b>\n\n"
        "⏳ Админ проверит оплату и ты получишь "
        "прокси.\nОбычно это занимает до 15 минут.",
        reply_markup=menu_btn(),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== АДМИН: ОПЛАТА ==========
@dp.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    user_id = int(callback.data.split("_")[1])
    payment = pending_payments.pop(user_id, None)

    if not payment:
        await callback.answer(
            "Заявка не найдена", show_alert=True
        )
        return

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>ПОДТВЕРЖДЕНО</b>",
        parse_mode="HTML"
    )
    await callback.answer("Подтверждено!")

    if payment["tariff"] == "ultra":
        await bot.send_message(
            user_id,
            "⏳ <b>Оплата подтверждена! "
            "Активирую прокси...</b>",
            parse_mode="HTML"
        )
        await deliver_ultra(user_id)
    else:
        await bot.send_message(
            user_id,
            "⏳ <b>Оплата подтверждена! "
            "Покупаю прокси...</b>",
            parse_mode="HTML"
        )
        await deliver_proxy(
            chat_id=user_id,
            period_key=payment["period"]
        )


@dp.callback_query(F.data.startswith("reject_"))
async def cb_reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    user_id = int(callback.data.split("_")[1])
    pending_payments.pop(user_id, None)

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        parse_mode="HTML"
    )
    await callback.answer("Отклонено")

    await bot.send_message(
        user_id,
        "❌ <b>Оплата отклонена.</b>\n\n"
        "Возможные причины:\n"
        "├ Сумма не совпадает\n"
        "├ Перевод не найден\n"
        "└ Истекло время ожидания\n\n"
        "Напиши в поддержку если считаешь "
        "что это ошибка.",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )


# ========== АДМИН-ПАНЕЛЬ ==========
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = await get_admin_text()
    await message.answer(
        text, reply_markup=admin_kb(), parse_mode="HTML"
    )


@dp.callback_query(F.data == "adm_back")
async def cb_adm_back(
    callback: CallbackQuery, state: FSMContext
):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.clear()
    text = await get_admin_text()
    await callback.message.edit_text(
        text, reply_markup=admin_kb(), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "adm_maintenance")
async def cb_adm_maintenance(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    global maintenance_mode
    maintenance_mode = not maintenance_mode

    status = "ВКЛЮЧЕНЫ" if maintenance_mode else "ВЫКЛЮЧЕНЫ"
    await callback.answer(
        f"🔧 Тех. работы {status}.", show_alert=True
    )

    text = await get_admin_text()
    await callback.message.edit_text(
        text, reply_markup=admin_kb(), parse_mode="HTML"
    )


@dp.callback_query(F.data == "adm_stats")
async def cb_adm_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    data = await load_data()
    today = datetime.now()

    users_today = users_week = users_month = 0
    for uid, info in data["users"].items():
        try:
            joined = datetime.strptime(
                info["joined"], "%Y-%m-%d %H:%M"
            )
            diff = (today - joined).days
            if diff == 0:
                users_today += 1
            if diff <= 7:
                users_week += 1
            if diff <= 30:
                users_month += 1
        except:
            pass

    total_proxies = active_proxies = 0
    total_income = income_today = 0
    income_week = income_month = 0
    purchases_today = purchases_week = purchases_month = 0
    period_stats = {}

    for uid, proxies in data["proxies"].items():
        for p in proxies:
            total_proxies += 1
            price = p.get("price", 0)
            total_income += price

            pr = p.get("period", "?")
            period_stats[pr] = period_stats.get(pr, 0) + 1

            try:
                bought = datetime.strptime(
                    p["bought"], "%Y-%m-%d %H:%M"
                )
                diff = (today - bought).days
                if diff == 0:
                    purchases_today += 1
                    income_today += price
                if diff <= 7:
                    purchases_week += 1
                    income_week += price
                if diff <= 30:
                    purchases_month += 1
                    income_month += price
            except:
                pass

            try:
                end = datetime.strptime(
                    p["date_end"], "%Y-%m-%d %H:%M:%S"
                )
                if end > today:
                    active_proxies += 1
            except:
                pass

    period_text = ""
    for name, count in sorted(
        period_stats.items(),
        key=lambda x: x[1],
        reverse=True
    ):
        period_text += f"├ {name}: <b>{count}</b>\n"

    await callback.message.edit_text(
        f"📊 <b>Подробная статистика</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"├ Всего: <b>{len(data['users'])}</b>\n"
        f"├ Сегодня: <b>{users_today}</b>\n"
        f"├ За неделю: <b>{users_week}</b>\n"
        f"└ За месяц: <b>{users_month}</b>\n\n"
        f"📦 <b>Покупки:</b>\n"
        f"├ Всего: <b>{total_proxies}</b>\n"
        f"├ Активных: <b>{active_proxies}</b>\n"
        f"├ Сегодня: <b>{purchases_today}</b>\n"
        f"├ За неделю: <b>{purchases_week}</b>\n"
        f"└ За месяц: <b>{purchases_month}</b>\n\n"
        f"💵 <b>Доход:</b>\n"
        f"├ Всего: <b>{total_income} ₽</b>\n"
        f"├ Сегодня: <b>{income_today} ₽</b>\n"
        f"├ За неделю: <b>{income_week} ₽</b>\n"
        f"└ За месяц: <b>{income_month} ₽</b>\n\n"
        f"📅 <b>Периоды:</b>\n{period_text}",
        reply_markup=admin_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "adm_users")
async def cb_adm_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    data = await load_data()
    users = data["users"]

    if not users:
        await callback.message.edit_text(
            "👥 <b>Пользователей пока нет.</b>",
            reply_markup=admin_back_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    sorted_users = sorted(
        users.items(),
        key=lambda x: x[1].get("joined", ""),
        reverse=True
    )[:20]

    text = f"👥 <b>Последние 20 пользователей:</b>\n\n"
    for uid, info in sorted_users:
        un = info.get("username", "")
        un_text = f"@{un}" if un else "—"
        purchases = len(data["proxies"].get(uid, []))
        text += (
            f"├ {info.get('first_name', '?')} | "
            f"{un_text}\n"
            f"│ ID: <code>{uid}</code> | "
            f"Покупок: {purchases} | "
            f"{info.get('joined', '?')}\n\n"
        )

    await callback.message.edit_text(
        text, reply_markup=admin_back_kb(), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "adm_active")
async def cb_adm_active(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    data = await load_data()
    now = datetime.now()
    active_list = []

    for user_id, proxies in data["proxies"].items():
        user_info = data["users"].get(user_id, {})
        for p in proxies:
            try:
                end_date = datetime.strptime(
                    p["date_end"], "%Y-%m-%d %H:%M:%S"
                )
                if end_date > now:
                    days_left = (end_date - now).days
                    active_list.append({
                        "user_id": user_id,
                        "user_name": user_info.get(
                            "first_name", "?"
                        ),
                        "proxy": p,
                        "days_left": days_left,
                    })
            except:
                pass

    if not active_list:
        await callback.message.edit_text(
            "🟢 <b>Нет активных прокси.</b>",
            reply_markup=admin_back_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    active_list.sort(key=lambda x: x["days_left"])

    text = (
        f"🟢 <b>Активные прокси "
        f"({len(active_list)} шт.):</b>\n\n"
    )
    for item in active_list[:20]:
        p = item["proxy"]
        d = item["days_left"]
        if d > 3650:
            emoji = "♾"
            days_text = "навсегда"
        elif d <= 1:
            emoji = "🔴"
            days_text = f"{d} дн."
        elif d <= 3:
            emoji = "🟡"
            days_text = f"{d} дн."
        else:
            emoji = "🟢"
            days_text = f"{d} дн."

        text += (
            f"{emoji} {item['user_name']} "
            f"(ID: {item['user_id']})\n"
            f"├ {p.get('tariff', '🛡 Обход блокировок')}\n"
            f"├ {p['host']}:{p['port']}\n"
            f"└ Осталось: <b>{days_text}</b>\n\n"
        )

    await callback.message.edit_text(
        text, reply_markup=admin_back_kb(), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "adm_balance")
async def cb_adm_balance(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    balance = await api_get_balance()

    if balance["ok"]:
        bal = float(balance["balance"])
        text = (
            f"💰 <b>Баланс Proxy6:</b>\n\n"
            f"💵 <b>{balance['balance']} "
            f"{balance['currency']}</b>\n\n"
            f"📦 <b>Хватит на (KZ прокси):</b>\n"
        )
        async with aiohttp.ClientSession() as session:
            for code, p in PERIODS.items():
                try:
                    url = (
                        f"{BASE_URL}/getprice"
                        f"?count=1&period={p['days']}"
                        f"&version={PROXY_VERSION}"
                    )
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        price_data = await resp.json()
                        if price_data["status"] == "yes":
                            price = float(price_data["price"])
                            can_buy = (
                                int(bal / price)
                                if price > 0 else 0
                            )
                            text += (
                                f"├ {p['name']}: "
                                f"<b>{can_buy} шт.</b> "
                                f"({price} "
                                f"{balance['currency']}"
                                f"/шт.)\n"
                            )
                except:
                    pass
    else:
        text = f"❌ Ошибка: {balance['error']}"

    await callback.message.edit_text(
        text, reply_markup=admin_back_kb(), parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(
    callback: CallbackQuery, state: FSMContext
):
    if callback.from_user.id != ADMIN_ID:
        return

    await state.set_state(BroadcastState.waiting_message)
    data = await load_data()
    total = len(data["users"])

    await callback.message.edit_text(
        f"📢 <b>Рассылка</b>\n\n"
        f"Получателей: <b>{total}</b>\n\n"
        f"Отправь сообщение для рассылки.\n"
        f"Можно: текст, фото, видео.\n\n"
        f"Или нажми «Отмена» 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="❌ Отмена", callback_data="adm_back"
            )]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(BroadcastState.waiting_message)
async def handle_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    await state.clear()
    data = await load_data()
    users = data["users"]
    total = len(users)
    success = failed = 0

    status_msg = await message.answer(
        f"📢 <b>Рассылка...</b> 0/{total}",
        parse_mode="HTML"
    )

    for uid in users:
        try:
            await message.copy_to(int(uid))
            success += 1
        except:
            failed += 1
        await asyncio.sleep(0.1)

    await status_msg.edit_text(
        f"📢 <b>Рассылка завершена!</b>\n\n"
        f"├ ✅ Доставлено: <b>{success}</b>\n"
        f"├ ❌ Ошибок: <b>{failed}</b>\n"
        f"└ Всего: <b>{total}</b>",
        parse_mode="HTML"
    )


# ========== УВЕДОМЛЕНИЯ ОБ ИСТЕЧЕНИИ ==========
async def check_expiring_proxies():
    while True:
        try:
            all_proxies = await get_all_proxies()

            for uid_str, proxies in all_proxies.items():
                uid = int(uid_str)

                for p in proxies:
                    if p.get("id") == "ultra_shared":
                        continue

                    try:
                        end_date = datetime.strptime(
                            p["date_end"],
                            "%Y-%m-%d %H:%M:%S"
                        )
                        now = datetime.now()
                        diff = end_date - now

                        if (
                            timedelta(days=1) < diff
                            <= timedelta(days=2)
                            and not p.get("notified_2d")
                        ):
                            tg_link = (
                                f"https://t.me/socks"
                                f"?server={p['host']}"
                                f"&port={p['port']}"
                                f"&user={p['user']}"
                                f"&pass={p['pass']}"
                            )
                            await bot.send_message(
                                uid,
                                f"⚠️ <b>Прокси заканчивается "
                                f"через 2 дня!</b>\n\n"
                                f"📦 🛡 Обход блокировок\n"
                                f"⏰ До: "
                                f"<b>{p['date_end']}</b>\n\n"
                                f"📱 Ссылка: {tg_link}\n\n"
                                f"Продли чтобы не потерять "
                                f"доступ 👇",
                                reply_markup=(
                                    InlineKeyboardMarkup(
                                        inline_keyboard=[
                                            [InlineKeyboardButton(
                                                text=(
                                                    "🔄 Купить "
                                                    "новый"
                                                ),
                                                callback_data="buy"
                                            )],
                                        ]
                                    )
                                ),
                                parse_mode="HTML"
                            )
                            p["notified_2d"] = True
                            data = await load_data()
                            data["proxies"][uid_str] = proxies
                            await save_data(data)

                        elif (
                            timedelta(hours=0) < diff
                            <= timedelta(days=1)
                            and not p.get("notified_1d")
                        ):
                            await bot.send_message(
                                uid,
                                f"🔴 <b>Прокси истекает "
                                f"СЕГОДНЯ!</b>\n\n"
                                f"📦 🛡 Обход блокировок\n"
                                f"⏰ До: "
                                f"<b>{p['date_end']}</b>\n\n"
                                f"Купи новый прямо "
                                f"сейчас 👇",
                                reply_markup=(
                                    InlineKeyboardMarkup(
                                        inline_keyboard=[
                                            [InlineKeyboardButton(
                                                text="🛡 Купить",
                                                callback_data="buy"
                                            )],
                                        ]
                                    )
                                ),
                                parse_mode="HTML"
                            )
                            p["notified_1d"] = True
                            data = await load_data()
                            data["proxies"][uid_str] = proxies
                            await save_data(data)

                    except Exception as e:
                        logger.error(f"Notify error: {e}")

        except Exception as e:
            logger.error(f"Check expiring error: {e}")

        await asyncio.sleep(3600)


# ========== ЛЮБОЙ ТЕКСТ ==========
@dp.message()
async def handle_any(message: Message):
    if is_maintenance(message.from_user.id):
        await message.answer(
            MAINTENANCE_TEXT, parse_mode="HTML"
        )
        return
    await message.answer(
        "Нажми /start 👇", reply_markup=main_kb()
    )


# ===================== ЗАПУСК =====================
async def main():
    logger.info("Бот запущен")
    asyncio.create_task(check_expiring_proxies())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
