import os
import requests
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===================== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ =====================
load_dotenv()

API_KEY = os.getenv("PROXY6_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_KEY or not BOT_TOKEN:
    raise ValueError(
        "Установи переменные окружения:\n"
        "PROXY6_API_KEY=твой_ключ\n"
        "BOT_TOKEN=твой_токен"
    )

# ===================== НАСТРОЙКИ =====================
BASE_URL = f"https://px6.link/api/{API_KEY}"
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
    "7": {
        "name": "1 неделя",
        "price": 50,
        "days": 7,
    },
    "30": {
        "name": "1 месяц",
        "price": 199,
        "days": 30,
    },
    "60": {
        "name": "2 месяца",
        "price": 349,
        "days": 60,
    },
    "90": {
        "name": "3 месяца",
        "price": 499,
        "days": 90,
    },
}

# ===================== ЛОГИРОВАНИЕ =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== БОТ =====================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ===================== СОСТОЯНИЯ =====================
class BuyProxy(StatesGroup):
    choosing_tariff = State()
    choosing_period = State()
    confirming = State()


# ===================== API =====================
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


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Оплатить и получить",
            callback_data="confirm"
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


# --------- БАЛАНС ---------
@dp.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    result = api_get_balance()
    if result["ok"]:
        text = (
            f"💰 <b>Баланс:</b> "
            f"{result['balance']} {result['currency']}"
        )
    else:
        text = f"❌ {result['error']}"

    await callback.message.edit_text(
        text, reply_markup=menu_btn(), parse_mode="HTML"
    )
    await callback.answer()


# --------- ШАГ 1: ТАРИФ ---------
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


# --------- ШАГ 2: ПЕРИОД ---------
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


# --------- НАЗАД К ПЕРИОДУ ---------
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


# --------- ШАГ 3: ПОДТВЕРЖДЕНИЕ ---------
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
    await state.set_state(BuyProxy.confirming)

    data = await state.get_data()
    tariff_key = data.get("tariff", "ru")
    tariff = TARIFFS.get(tariff_key, TARIFFS["ru"])

    count_result = api_get_count(tariff["country"])
    if count_result["ok"] and int(count_result["count"]) > 0:
        stock = f"📊 В наличии: <b>{count_result['count']} шт.</b>"
    elif count_result["ok"]:
        stock = "📊 ⚠️ <b>Нет в наличии!</b>"
    else:
        stock = ""

    await callback.message.edit_text(
        f"🧾 <b>Твой заказ:</b>\n\n"
        f"📦 Тариф: <b>{tariff['name']}</b>\n"
        f"🌍 Локация: <b>{tariff['short']}</b>\n"
        f"🔧 Тип: <b>SOCKS5</b>\n"
        f"📅 Срок: <b>{period_data['name']}</b>\n"
        f"💵 Цена: <b>{period_data['price']} ₽</b>\n"
        f"{stock}\n\n"
        f"Всё верно? 👇",
        reply_markup=confirm_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# --------- ШАГ 4: ПОКУПКА ---------
@dp.callback_query(F.data == "confirm", BuyProxy.confirming)
async def cb_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    tariff_key = data.get("tariff", "ru")
    tariff = TARIFFS.get(tariff_key, TARIFFS["ru"])
    period_key = data.get("period", "7")
    period_data = PERIODS.get(period_key, PERIODS["7"])

    await callback.message.edit_text(
        f"⏳ <b>Покупаю {tariff['name']} прокси...</b>\n"
        f"Подожди пару секунд ⌛",
        parse_mode="HTML"
    )
    await callback.answer()

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

        await callback.message.edit_text(
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

        logger.info(
            f"User {callback.from_user.id} bought "
            f"{tariff['name']} #{result['id']} "
            f"{host}:{port} for {period_data['days']}d "
            f"({period_data['price']} RUB)"
        )

    else:
        await callback.message.edit_text(
            f"❌ <b>Ошибка:</b> {result['error']}\n\n"
            f"Попробуй позже или напиши админу.",
            reply_markup=after_buy_kb(),
            parse_mode="HTML"
        )


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
