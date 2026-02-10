import requests
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    Message
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===================== НАСТРОЙКИ =====================
API_KEY = "2ceb6b52bf-9b7fd55343-c444559a23"
BOT_TOKEN = "8124149270:AAFRVZ_q6rA9f9cScJIEs0lxYYYFlEGapvI"
CRYPTOBOT_TOKEN = "529805:AAH22XbKK6qPCv07XYL9pFf7aeVQPx4NQkR"
ADMIN_ID = 1967888210  # твой Telegram ID

# Ссылка на сбор средств (Тинькофф, СБП, ЮMoney и т.д.)
PAYMENT_LINK = "https://www.tbank.ru/cf/5COiqw9ez0B"

BASE_URL = f"https://px6.link/api/{API_KEY}"
CRYPTOBOT_API = "https://pay.crypt.bot/api"
PROXY_VERSION = 6
PROXY_TYPE = "socks"

# ===================== ТАРИФЫ =====================
TARIFFS = {
    "ru": {
        "name": "🚀 RU-Скорость",
        "country": "ru",
        "description": (
            "🚀 <b>RU-Скорость (Россия)</b>\n\n"
            "✅ Сообщения летают мгновенно\n"
            "✅ Видео открывается без задержек\n"
            "✅ Минимальный пинг\n\n"
            "⚠️ <i>Может не открывать "
            "заблокированные ресурсы</i>"
        ),
        "short": "🇷🇺 Россия • Быстрый пинг",
    },
    "nl": {
        "name": "🛡️ EU-Обход",
        "country": "nl",
        "description": (
            "🛡️ <b>EU-Обход (Нидерланды)</b>\n\n"
            "✅ Работает при любых блокировках\n"
            "✅ Полный доступ ко всем ресурсам\n"
            "✅ Европейский сервер\n\n"
            "⚠️ <i>Пинг чуть выше "
            "(небольшая задержка)</i>"
        ),
        "short": "🇳🇱 Нидерланды • Обход блокировок",
    },
}

# ===================== ПЕРИОДЫ И ЦЕНЫ =====================
PERIODS = {
    "7": {"name": "1 неделя", "price": 50, "days": 7, "stars": 75},
    "30": {"name": "1 месяц", "price": 199, "days": 30, "stars": 290},
    "60": {"name": "2 месяца", "price": 349, "days": 60, "stars": 500},
    "90": {"name": "3 месяца", "price": 499, "days": 90, "stars": 720},
}

# ===================== ЛОГИРОВАНИЕ =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== БОТ =====================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Ожидающие оплаты по ссылке
pending_payments = {}


# ===================== СОСТОЯНИЯ =====================
class BuyProxy(StatesGroup):
    choosing_tariff = State()
    choosing_period = State()
    choosing_payment = State()
    waiting_confirm = State()


# ===================== PROXY6 API =====================
def api_get_balance() -> dict:
    try:
        data = requests.get(BASE_URL, timeout=10).json()
        if data["status"] == "yes":
            return {
                "ok": True,
                "balance": data["balance"],
                "currency": data["currency"],
            }
        return {"ok": False, "error": data.get("error", "?")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_get_count(country: str) -> dict:
    try:
        url = (
            f"{BASE_URL}/getcount"
            f"?country={country}&version={PROXY_VERSION}"
        )
        data = requests.get(url, timeout=10).json()
        if data["status"] == "yes":
            return {"ok": True, "count": data["count"]}
        return {"ok": False, "error": data.get("error", "?")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_check_before_buy(country: str, period: int) -> dict:
    count = api_get_count(country)
    if count["ok"] and int(count["count"]) == 0:
        return {"ok": False, "error": "Нет прокси в наличии"}
    try:
        url = (
            f"{BASE_URL}/getprice"
            f"?count=1&period={period}&version={PROXY_VERSION}"
        )
        data = requests.get(url, timeout=10).json()
        if data["status"] == "yes":
            price = float(data["price"])
            balance_data = api_get_balance()
            if balance_data["ok"]:
                balance = float(balance_data["balance"])
                if balance < price:
                    return {
                        "ok": False,
                        "error": "Временно нет в наличии"
                    }
        return {"ok": True}
    except:
        return {"ok": True}


def api_buy_proxy(country: str, period: int) -> dict:
    try:
        url = (
            f"{BASE_URL}/buy"
            f"?count=1"
            f"&period={period}"
            f"&country={country}"
            f"&version={PROXY_VERSION}"
            f"&type={PROXY_TYPE}"
        )
        data = requests.get(url, timeout=30).json()
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
                "balance": data.get("balance", "?"),
                "currency": data.get("currency", ""),
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
                    data.get("error", "Неизвестная ошибка")
                ),
            }
    except Exception as e:
        logger.error(f"Buy error: {e}")
        return {"ok": False, "error": str(e)}


# ===================== CRYPTOBOT API =====================
def cryptobot_create_invoice(
    amount: float,
    user_id: int,
    tariff_key: str,
    period_key: str
) -> dict:
    try:
        payload = f"{user_id}:{tariff_key}:{period_key}"
        url = f"{CRYPTOBOT_API}/createInvoice"
        headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
        data = {
            "currency_type": "fiat",
            "fiat": "RUB",
            "amount": str(amount),
            "description": "Прокси SOCKS5",
            "payload": payload,
            "expires_in": 3600,
        }
        resp = requests.post(
            url, headers=headers, json=data, timeout=10
        ).json()

        if resp.get("ok"):
            return {
                "ok": True,
                "url": resp["result"]["bot_invoice_url"],
                "invoice_id": resp["result"]["invoice_id"],
            }
        return {
            "ok": False,
            "error": resp.get("error", {}).get(
                "name", "Ошибка CryptoBot"
            ),
        }
    except Exception as e:
        logger.error(f"CryptoBot error: {e}")
        return {"ok": False, "error": str(e)}


def cryptobot_check_invoice(invoice_id: int) -> dict:
    try:
        url = f"{CRYPTOBOT_API}/getInvoices"
        headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
        params = {"invoice_ids": str(invoice_id)}
        resp = requests.get(
            url, headers=headers, params=params, timeout=10
        ).json()

        if resp.get("ok") and resp["result"]["items"]:
            invoice = resp["result"]["items"][0]
            return {
                "ok": True,
                "status": invoice["status"],
            }
        return {"ok": False, "error": "Счёт не найден"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ===================== ВЫДАЧА ПРОКСИ =====================
async def deliver_proxy(
    chat_id: int,
    tariff_key: str,
    period_key: str
):
    tariff = TARIFFS.get(tariff_key, TARIFFS["ru"])
    period_data = PERIODS.get(period_key, PERIODS["7"])

    result = api_buy_proxy(
        country=tariff["country"],
        period=period_data["days"]
    )

    if result["ok"]:
        host = result["host"]
        port = result["port"]
        user = result["user"]
        password = result["pass"]
        date_end = result["date_end"]

        tg_link = (
            f"https://t.me/socks"
            f"?server={host}"
            f"&port={port}"
            f"&user={user}"
            f"&pass={password}"
        )
        raw = f"{host}:{port}:{user}:{password}"

        await bot.send_message(
            chat_id,
            f"✅ <b>Прокси готов!</b>\n\n"
            f"📦 Тариф: <b>{tariff['name']}</b>\n"
            f"🌍 Локация: <b>{tariff['short']}</b>\n"
            f"🔧 Тип: <b>SOCKS5</b>\n"
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
        logger.info(f"Delivered proxy to {chat_id}: {host}:{port}")
    else:
        await bot.send_message(
            chat_id,
            f"❌ <b>Ошибка:</b> {result['error']}\n\n"
            f"Напиши админу для решения проблемы.",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )


# ===================== КЛАВИАТУРЫ =====================
def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛒 Купить прокси",
            callback_data="buy"
        )],
        [InlineKeyboardButton(
            text="💰 Баланс",
            callback_data="balance"
        )],
    ])


def tariff_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 RU-Скорость (Россия)",
            callback_data="tariff_ru"
        )],
        [InlineKeyboardButton(
            text="🛡️ EU-Обход (Нидерланды)",
            callback_data="tariff_nl"
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
            text=f"🤖 CryptoBot ({period_data['price']} ₽)",
            callback_data="pay_crypto"
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


def after_buy_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛒 Купить ещё",
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


# ===================== ОБРАБОТЧИКИ =====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"🔐 Персональные SOCKS5 прокси для Telegram\n\n"
        f"📦 <b>Два тарифа:</b>\n\n"
        f"🚀 <b>RU-Скорость</b> — всё летает, "
        f"минимальный пинг\n"
        f"🛡️ <b>EU-Обход</b> — работает при любых "
        f"блокировках\n\n"
        f"💰 <b>Цены:</b>\n"
        f"├ 1 неделя — <b>50 ₽</b>\n"
        f"├ 1 месяц — <b>199 ₽</b>\n"
        f"├ 2 месяца — <b>349 ₽</b>\n"
        f"└ 3 месяца — <b>499 ₽</b>\n\n"
        f"💳 <b>Способы оплаты:</b>\n"
        f"├ ⭐ Telegram Stars\n"
        f"├ 🤖 CryptoBot\n"
        f"└ 💳 Перевод по ссылке\n\n"
        f"Нажми <b>«Купить прокси»</b> 👇",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
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


@dp.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    result = api_get_balance()
    if result["ok"]:
        text = (
            f"💰 <b>Баланс Proxy6:</b> "
            f"{result['balance']} {result['currency']}"
        )
    else:
        text = f"❌ {result['error']}"
    await callback.message.edit_text(
        text, reply_markup=menu_btn(), parse_mode="HTML"
    )
    await callback.answer()


# ========== ШАГ 1: ТАРИФ ==========
@dp.callback_query(F.data == "buy")
async def cb_buy(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(BuyProxy.choosing_tariff)
    await callback.message.edit_text(
        "📦 <b>Выбери тариф:</b>\n\n"
        "🚀 <b>RU-Скорость (Россия)</b>\n"
        "├ Сообщения летают мгновенно\n"
        "├ Видео без задержек\n"
        "└ ⚠️ Может не открывать "
        "заблокированные ресурсы\n\n"
        "🛡️ <b>EU-Обход (Нидерланды)</b>\n"
        "├ Работает при любых блокировках\n"
        "├ Полный доступ ко всему\n"
        "└ ⚠️ Пинг чуть выше",
        reply_markup=tariff_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== ШАГ 2: ПЕРИОД ==========
@dp.callback_query(
    F.data.startswith("tariff_"),
    BuyProxy.choosing_tariff
)
async def cb_tariff(callback: CallbackQuery, state: FSMContext):
    tariff_key = callback.data.split("_")[1]
    tariff = TARIFFS.get(tariff_key)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await state.update_data(tariff=tariff_key)
    await state.set_state(BuyProxy.choosing_period)

    await callback.message.edit_text(
        f"{tariff['description']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 <b>Выбери срок:</b>",
        reply_markup=period_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "back_period")
async def cb_back_period(
    callback: CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    tariff_key = data.get("tariff", "ru")
    tariff = TARIFFS.get(tariff_key, TARIFFS["ru"])
    await state.set_state(BuyProxy.choosing_period)

    await callback.message.edit_text(
        f"{tariff['description']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 <b>Выбери срок:</b>",
        reply_markup=period_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== ШАГ 3: СПОСОБ ОПЛАТЫ ==========
@dp.callback_query(
    F.data.startswith("period_"),
    BuyProxy.choosing_period
)
async def cb_period(callback: CallbackQuery, state: FSMContext):
    period_key = callback.data.split("_")[1]
    period_data = PERIODS.get(period_key)
    if not period_data:
        await callback.answer("Период не найден", show_alert=True)
        return

    await state.update_data(period=period_key)
    await state.set_state(BuyProxy.choosing_payment)

    data = await state.get_data()
    tariff_key = data.get("tariff", "ru")
    tariff = TARIFFS.get(tariff_key, TARIFFS["ru"])

    await callback.message.edit_text(
        f"🧾 <b>Твой заказ:</b>\n\n"
        f"📦 Тариф: <b>{tariff['name']}</b>\n"
        f"🌍 Локация: <b>{tariff['short']}</b>\n"
        f"🔧 Тип: <b>SOCKS5</b>\n"
        f"📅 Срок: <b>{period_data['name']}</b>\n"
        f"💵 Цена: <b>{period_data['price']} ₽</b>\n\n"
        f"💳 <b>Выбери способ оплаты:</b>",
        reply_markup=payment_kb(period_key),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== ОПЛАТА: TELEGRAM STARS ==========
@dp.callback_query(
    F.data == "pay_stars",
    BuyProxy.choosing_payment
)
async def cb_pay_stars(
    callback: CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    tariff_key = data.get("tariff", "ru")
    period_key = data.get("period", "7")
    tariff = TARIFFS.get(tariff_key, TARIFFS["ru"])
    period_data = PERIODS.get(period_key, PERIODS["7"])

    check = api_check_before_buy(
        tariff["country"], period_data["days"]
    )
    if not check["ok"]:
        await state.clear()
        await callback.message.edit_text(
            f"❌ <b>{check['error']}</b>\n\n"
            f"Попробуй позже или напиши админу.",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await state.clear()

    prices = [
        LabeledPrice(
            label=f"{tariff['name']} — {period_data['name']}",
            amount=period_data["stars"]
        )
    ]

    await callback.message.delete()

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Прокси {tariff['name']}",
        description=(
            f"SOCKS5 прокси\n"
            f"Тариф: {tariff['name']}\n"
            f"Срок: {period_data['name']}"
        ),
        payload=f"{tariff_key}:{period_key}",
        currency="XTR",
        prices=prices,
    )
    await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    parts = payload.split(":")
    tariff_key = parts[0]
    period_key = parts[1]

    await message.answer(
        "⏳ <b>Оплата получена! Покупаю прокси...</b>",
        parse_mode="HTML"
    )

    await deliver_proxy(
        chat_id=message.from_user.id,
        tariff_key=tariff_key,
        period_key=period_key
    )

    logger.info(
        f"Stars payment from {message.from_user.id}: "
        f"{tariff_key}:{period_key}"
    )


# ========== ОПЛАТА: CRYPTOBOT ==========
@dp.callback_query(
    F.data == "pay_crypto",
    BuyProxy.choosing_payment
)
async def cb_pay_crypto(
    callback: CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    tariff_key = data.get("tariff", "ru")
    period_key = data.get("period", "7")
    tariff = TARIFFS.get(tariff_key, TARIFFS["ru"])
    period_data = PERIODS.get(period_key, PERIODS["7"])

    check = api_check_before_buy(
        tariff["country"], period_data["days"]
    )
    if not check["ok"]:
        await state.clear()
        await callback.message.edit_text(
            f"❌ <b>{check['error']}</b>\n\n"
            f"Попробуй позже или напиши админу.",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await state.clear()

    result = cryptobot_create_invoice(
        amount=period_data["price"],
        user_id=callback.from_user.id,
        tariff_key=tariff_key,
        period_key=period_key
    )

    if result["ok"]:
        invoice_id = result["invoice_id"]
        await callback.message.edit_text(
            f"🤖 <b>Счёт создан!</b>\n\n"
            f"💵 Сумма: <b>{period_data['price']} ₽</b>\n"
            f"⏰ Счёт действует 1 час\n\n"
            f"<b>Инструкция:</b>\n"
            f"1️⃣ Нажми кнопку <b>«Оплатить»</b>\n"
            f"2️⃣ Оплати в CryptoBot\n"
            f"3️⃣ Вернись сюда и нажми <b>«Я оплатил»</b>\n"
            f"4️⃣ Получи прокси 🎉",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="💳 Оплатить",
                    url=result["url"]
                )],
                [InlineKeyboardButton(
                    text="✅ Я оплатил",
                    callback_data=(
                        f"check_crypto_{invoice_id}"
                        f"_{tariff_key}_{period_key}"
                    )
                )],
                [InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel"
                )],
            ]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка CryptoBot: {result['error']}",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("check_crypto_"))
async def cb_check_crypto(callback: CallbackQuery):
    parts = callback.data.split("_")
    invoice_id = int(parts[2])
    tariff_key = parts[3]
    period_key = parts[4]

    result = cryptobot_check_invoice(invoice_id)

    if result["ok"] and result["status"] == "paid":
        await callback.message.edit_text(
            "⏳ <b>Оплата подтверждена! Покупаю прокси...</b>",
            parse_mode="HTML"
        )
        await deliver_proxy(
            chat_id=callback.from_user.id,
            tariff_key=tariff_key,
            period_key=period_key
        )
    elif result["ok"] and result["status"] == "active":
        await callback.answer(
            "⏳ Оплата ещё не поступила. "
            "Оплати и нажми кнопку снова.",
            show_alert=True
        )
    else:
        await callback.answer(
            "❌ Счёт не найден или истёк.",
            show_alert=True
        )


# ========== ОПЛАТА: ССЫЛКА НА ПЕРЕВОД ==========
@dp.callback_query(
    F.data == "pay_link",
    BuyProxy.choosing_payment
)
async def cb_pay_link(
    callback: CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    tariff_key = data.get("tariff", "ru")
    period_key = data.get("period", "7")
    tariff = TARIFFS.get(tariff_key, TARIFFS["ru"])
    period_data = PERIODS.get(period_key, PERIODS["7"])

    check = api_check_before_buy(
        tariff["country"], period_data["days"]
    )
    if not check["ok"]:
        await state.clear()
        await callback.message.edit_text(
            f"❌ <b>{check['error']}</b>\n\n"
            f"Попробуй позже или напиши админу.",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await state.set_state(BuyProxy.waiting_confirm)
    await state.update_data(tariff=tariff_key, period=period_key)

    # Сохраняем заявку
    pending_payments[callback.from_user.id] = {
        "tariff": tariff_key,
        "period": period_key,
    }

    await callback.message.edit_text(
        f"💳 <b>Оплата переводом</b>\n\n"
        f"📦 Заказ: <b>{tariff['name']} — "
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


@dp.callback_query(F.data == "paid_link")
async def cb_paid_link(callback: CallbackQuery, state: FSMContext):
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

    tariff = TARIFFS.get(payment["tariff"], TARIFFS["ru"])
    period_data = PERIODS.get(payment["period"], PERIODS["7"])

    user_link = (
        f'<a href="tg://user?id={user.id}">'
        f'{user.first_name}</a>'
    )

    # Уведомляем админа
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"💳 <b>Новая оплата по ссылке!</b>\n\n"
            f"👤 Клиент: {user_link}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📦 Тариф: <b>{tariff['name']}</b>\n"
            f"📅 Срок: <b>{period_data['name']}</b>\n"
            f"💵 Сумма: <b>{period_data['price']} ₽</b>\n\n"
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
        "прокси.\n"
        "Обычно это занимает до 15 минут.",
        reply_markup=menu_btn(),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== АДМИН: ПОДТВЕРЖДЕНИЕ / ОТКЛОНЕНИЕ ==========
@dp.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    user_id = int(callback.data.split("_")[1])
    payment = pending_payments.pop(user_id, None)

    if not payment:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>ПОДТВЕРЖДЕНО</b>",
        parse_mode="HTML"
    )
    await callback.answer("Подтверждено!")

    await bot.send_message(
        user_id,
        "⏳ <b>Оплата подтверждена! Покупаю прокси...</b>",
        parse_mode="HTML"
    )

    await deliver_proxy(
        chat_id=user_id,
        tariff_key=payment["tariff"],
        period_key=payment["period"]
    )

    logger.info(f"Link payment approved for {user_id}")


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
        "Напиши админу если считаешь "
        "что это ошибка.",
        reply_markup=main_kb(),
        parse_mode="HTML"
    )


# ========== ЛЮБОЙ ТЕКСТ ==========
@dp.message()
async def handle_any(message: types.Message):
    await message.answer(
        "Нажми /start 👇",
        reply_markup=main_kb()
    )


# ===================== ЗАПУСК =====================
async def main():
    logger.info("Бот запущен")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
