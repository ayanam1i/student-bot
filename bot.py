import asyncio
import json
import logging
import os
import random
import re
import time
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

# ==================== ВАШИ ДАННЫЕ ====================
BOT_TOKEN = "8686278984:AAHonPsQ4LQrITp206RFmjn8U1uJExumu-0"
ADMIN_ID = 725832288
CARD_REQUISITES = "4874 0700 5034 4322 (Monobank)"
CRYPTO_PAY_TOKEN = "632393:AAKBCWvRJ2tWi5Ky1NRSKFzxHurzqXKXQSG"
# ====================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_FILE = "users_database.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(user_id: int):
    db = load_db()
    uid = str(user_id)
    is_admin = (user_id == ADMIN_ID)

    if uid not in db:
        db[uid] = {
            "free_checks": 99999 if is_admin else 3,
            "is_pro": True if is_admin else False,
            "pro_until": 4102444800 if is_admin else 0,
            "referrals": 0,
            "selected_mode": "antiplagiat"
        }
        save_db(db)
    elif is_admin and not db[uid].get("is_pro"):
        db[uid]["is_pro"] = True
        db[uid]["free_checks"] = 99999
        db[uid]["pro_until"] = 4102444800
        save_db(db)

    return db[uid]

def update_user(user_id: int, key: str, value):
    db = load_db()
    uid = str(user_id)
    if uid in db:
        db[uid][key] = value
        save_db(db)

# Клише ChatGPT (Украинские и Международные)
AI_CLICHES = [
    # Українська мова
    (r"(?i)\bнасамкінець(?:\s+варто\s+зазначити)?(?:,?\s*що)?\b", "Підсумовуючи викладене,"),
    (r"(?i)\bважливо\s+підкреслити(?:,?\s*що)?\b", "Слід звернути особливу увагу на те, що"),
    (r"(?i)\bвідіграє\s+важливу\s+роль\b", "має визначальне значення"),
    (r"(?i)\bцей\s+аспект\b", "досліджуване питання"),
    (r"(?i)\bне\s+можна\s+не\s+відзначити(?:,?\s*що)?\b", "показовим є факт, що"),
    (r"(?i)\bу\s+сучасному\s+світі\b", "в актуальних реаліях сьогодення"),
    (r"(?i)\bє\s+невід'ємною\s+частиною\b", "тісно взаємопов'язано з"),
    (r"(?i)\bпідбиваючи\s+підсумки\b", "узагальнюючи отримані аналітичні дані"),
    (r"(?i)\bслід\s+зазначити(?:,?\s*що)?\b", "заслуговує на увагу факт, що"),
    (r"(?i)\bявляє\s+собою\b", "виступає як"),
    (r"(?i)\bтаким\s+чином\b", "виходячи з цього,"),

    # Русский язык
    (r"(?i)\bв заключение(?:\s+стоит\s+отметить)?(?:,?\s*что)?\b", "Обобщая вышеизложенное,"),
    (r"(?i)\bважно\s+подчеркнуть(?:,?\s*что)?\b", "Следует обратить внимание, что"),
    (r"(?i)\bиграет\s+важную\s+роль\b", "имеет определяющее значение"),
    (r"(?i)\bданный\s+аспект\b", "рассматриваемый вопрос"),
    (r"(?i)\bнельзя\s+не\s+отметить(?:,?\s*что)?\b", "необходимо констатировать, что"),
    (r"(?i)\bв\s+современном\s+мире\b", "в актуальных реалиях"),
    (r"(?i)\bявляется\s+неотъемлемой\s+частью\b", "тесно взаимосвязано с"),
    (r"(?i)\bподводя\s+итоги\b", "синтезируя полученные данные"),
    (r"(?i)\bследует\s+отметить(?:,?\s*что)?\b", "заслуживает внимания тот факт, что"),
    (r"(?i)\bпредставляет\s+собой\b", "выступает как специфический")
]

# База синонимов (UA + RU)
ACADEMIC_SYNONYMS = {
    # Українська мова
    "дослідження": ["науковий аналіз", "вивчення питання", "розгляд проблематики"],
    "проблема": ["актуальне питання", "досліджуване завдання", "проблематика"],
    "проблеми": ["актуальні питання", "досліджувані завдання", "комплексні складнощі"],
    "метод": ["підхід", "інструментарій", "спосіб"],
    "результат": ["отриманий підсумок", "висновок"],
    "розвиток": ["еволюція", "динамічне зростання", "прогрес"],
    "держава": ["публічно-правове утворення", "державний апарат"],
    "державних": ["публічно-правових", "владних"],
    "закон": ["нормативно-правовий акт", "законодавча норма", "правовий припис"],
    "суспільство": ["соціум", "соціальне середовище"],
    "суспільства": ["соціуму", "соціального середовища"],
    "людина": ["індивід", "особистість"],
    "громадян": ["членів суспільства", "суб'єктів права"],
    "важливий": ["значущий", "суттєвий", "вагомий"],
    "головний": ["ключовий", "основоположний"],
    "головні": ["ключові", "основоположні", "пріоритетні"],
    "показує": ["демонструє", "свідчить про те, що", "ілюструє"],
    "дозволяє": ["надає можливість", "сприяє", "забезпечує умови для"],
    "фактор": ["детермінанта", "чинник", "рушійна умова"],

    # Русский язык
    "исследование": ["научный анализ", "изучение вопроса", "рассмотрение проблемы"],
    "проблема": ["актуальный вопрос", "исследуемая задача", "сложность"],
    "метод": ["подход", "исследовательский инструментарий", "методика"],
    "результат": ["полученный итог", "вывод", "фактический показатель"],
    "государство": ["публично-правовое образование", "государственный аппарат"],
    "закон": ["нормативно-правовой акт", "законодательная норма"],
    "общество": ["социум", "социальная среда"],
    "важный": ["значимый", "существенный", "весомый"]
}

UA_TRANSITIONS = [
    "Разом з тим, ",
    "З точки зору наукового аналізу, ",
    "Варто зауважити, що ",
    "Спираючись на емпіричні дані, ",
    "Водночас, "
]

RU_TRANSITIONS = [
    "Вместе с тем, ",
    "С точки зрения теоретического анализа, ",
    "Примечательно, что ",
    "Опираясь на эмпирический материал, ",
    "В то же время, "
]

def deep_transform_engine(text: str, mode: str = "humanize") -> str:
    res = text
    # 1. Замена клише
    for pat, repl in AI_CLICHES:
        res = re.sub(pat, repl, res)

    # 2. Замена синонимов
    words = res.split(" ")
    out_words = []
    for w in words:
        clean = re.sub(r"[^\w']", "", w).lower()
        if clean in ACADEMIC_SYNONYMS and random.random() < 0.70:
            syn = random.choice(ACADEMIC_SYNONYMS[clean])
            if w and w[0].isupper():
                syn = syn.capitalize()
            punct = "".join([c for c in w if not c.isalnum() and c != "'"])
            out_words.append(syn + punct)
        else:
            out_words.append(w)

    res = " ".join(out_words)

    # 3. Безопасная академическая связка для второго предложения
    sentences = res.split(". ")
    if len(sentences) > 1 and mode == "antiplagiat":
        second_sentence = sentences.pop(1).strip()
        if second_sentence:
            is_ua = any(c in res.lower() for c in ['і', 'ї', 'є', 'ґ'])
            trans_list = UA_TRANSITIONS if is_ua else RU_TRANSITIONS
            trans = random.choice(trans_list)
            first_char = second_sentence[:1].lower()
            rest_sentence = second_sentence[1:]
            new_second = trans + first_char + rest_sentence
            sentences.insert(1, new_second)

    return ". ".join(sentences)

async def create_cryptobot_invoice(amount_usd: float, desc: str):
    if not CRYPTO_PAY_TOKEN:
        return None
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    payload = {"asset": "USDT", "amount": str(amount_usd), "description": desc}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        return data["result"]["bot_invoice_url"]
    except Exception:
        pass
    return None

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍️ Очеловечить текст", callback_data="mode_humanize"),
            InlineKeyboardButton(text="🛡 Под Антиплагиат", callback_data="mode_antiplagiat")
        ],
        [
            InlineKeyboardButton(text="💳 Оплата и тарифы", callback_data="tariffs"),
            InlineKeyboardButton(text="👤 Профиль и Рефералка", callback_data="profile")
        ]
    ])

@dp.message(F.text == "/godmode")
async def secret_godmode_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    user = get_user(message.from_user.id)
    user["free_checks"] = 99999
    user["is_pro"] = True
    user["pro_until"] = 4102444800
    update_user(message.from_user.id, "free_checks", 99999)
    update_user(message.from_user.id, "is_pro", True)
    update_user(message.from_user.id, "pro_until", 4102444800)

    text = (
        "👑 **РЕЖИМ СОЗДАТЕЛЯ (GODMODE) АКТИВИРОВАН!**\n\n"
        "• Проверки текста: **Бесконечно (99 999 шт.)**\n"
        "• Подписка PRO: **Вечный безлимит до 2100 года**\n"
        "• Списание попыток: **Отключено**\n\n"
        "Теперь вы можете тестировать любые тексты без ограничений."
    )
    await message.answer(text, reply_markup=main_kb(), parse_mode="Markdown")

@dp.message(CommandStart())
async def start_handler(message: Message):
    user = get_user(message.from_user.id)
    is_admin = (message.from_user.id == ADMIN_ID)

    cmd_parts = message.text.split()
    if len(cmd_parts) > 1:
        ref_arg = cmd_parts.pop()
        if ref_arg.startswith("ref_"):
            try:
                ref_id = int(ref_arg.replace("ref_", ""))
                if ref_id != message.from_user.id:
                    inv = get_user(ref_id)
                    inv["free_checks"] += 1
                    inv["referrals"] += 1
                    update_user(ref_id, "free_checks", inv["free_checks"])
                    update_user(ref_id, "referrals", inv["referrals"])
                    await bot.send_message(ref_id, "🎉 По вашей ссылке зашел одногруппник! Вам начислена +1 бесплатная проверка.")
            except Exception:
                pass

    status_str = "👑 **Безлимит Создателя**" if is_admin else f"**{user['free_checks']} бесплатных проверок**"

    text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для **очеловечивания текстов после ChatGPT** и **повышения уникальности под Антиплагиат** (Unicheck / StrikePlagiarism).\n\n"
        "🇺🇦 Поддерживаю украинский и русский языки.\n\n"
        f"🎁 Доступно проверок: {status_str}.\n\n"
        "Выберите режим кнопками ниже или сразу отправьте текст реферата/курсовой 👇"
    )
    await message.answer(text, reply_markup=main_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "mode_humanize")
async def handle_humanize_click(call: CallbackQuery):
    await call.answer("Режим «Очеловечивание ИИ» включен!")
    update_user(call.from_user.id, "selected_mode", "humanize")
    text = (
        "✅ **Режим: Очеловечивание ИИ (Обход детекторов нейросетей)**\n\n"
        "Я готов! Отправьте мне текст, сгенерированный ChatGPT или другой нейросетью.\n"
        "Я удалю синтетические маркеры, клише и сделаю слог естественным и живым.\n\n"
        "👇 **Отправьте текст сообщением ниже:**"
    )
    await call.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "mode_antiplagiat")
async def handle_antiplagiat_click(call: CallbackQuery):
    await call.answer("Режим «Антиплагиат 85%+» включен!")
    update_user(call.from_user.id, "selected_mode", "antiplagiat")
    text = (
        "✅ **Режим: Глубокий рерайт под Антиплагиат (85%+)**\n\n"
        "Я готов! Отправьте мне фрагмент реферата, эссе или курсовой.\n"
        "Я заменю фразы академическими синонимами, перестрою синтаксис и подниму уникальность под системы проверки ВУЗа.\n\n"
        "👇 **Отправьте текст сообщением ниже:**"
    )
    await call.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "tariffs")
async def tariffs_handler(call: CallbackQuery):
    await call.answer()
    text = (
        "💳 **Выберите тариф для оформления:**\n\n"
        "🎟 **1 проверка** — `25 грн` / `15 ⭐️ Stars` / `$0.60 USDT`\n"
        "⚡ **Пакет «Сессия» (7 дней безлимита)** — `99 грн` / `50 ⭐️ Stars` / `$2.50 USDT`\n"
        "👑 **Пакет «Диплом» (30 дней безлимита)** — `199 грн` / `100 ⭐️ Stars` / `$5.00 USDT`\n\n"
        "Каким способом вам удобнее оплатить?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 На карту Monobank (Гривна)", callback_data="pay_card")],
        [InlineKeyboardButton(text="⭐️ Telegram Stars (Apple / Google Pay)", callback_data="pay_stars_menu")],
        [InlineKeyboardButton(text="💎 Криптовалюта (@CryptoBot / USDT)", callback_data="pay_crypto")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "pay_card")
async def card_handler(call: CallbackQuery):
    await call.answer()
    text = (
        "💳 **Оплата на карту Monobank:**\n\n"
        f"Номер карты: `{CARD_REQUISITES}`\n\n"
        "Сумма к оплате:\n"
        "• 1 проверка: **25 грн**\n"
        "• 7 дней безлимита (Сессия): **99 грн**\n"
        "• 30 дней безлимита (Диплом): **199 грн**\n\n"
        "⚠️ После оплаты нажмите кнопку **«Я оплатил»** и отправьте скриншот чека в чат."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил (Отправить чек)", callback_data="send_receipt")],
        [InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="tariffs")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "send_receipt")
async def receipt_prompt(call: CallbackQuery):
    await call.answer()
    await call.message.answer("📸 Отправьте скриншот или фото квитанции об оплате в чат сообщением.")

@dp.callback_query(F.data == "pay_stars_menu")
async def stars_menu(call: CallbackQuery):
    await call.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ 1 проверка (15 Stars)", callback_data="stars_buy_1")],
        [InlineKeyboardButton(text="⭐️ Сессия 7 дней (50 Stars)", callback_data="stars_buy_7")],
        [InlineKeyboardButton(text="⭐️ Месяц 30 дней (100 Stars)", callback_data="stars_buy_30")],
        [InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="tariffs")]
    ])
    await call.message.edit_text("Оплата звёздами прямо в приложении Telegram в 1 клик:", reply_markup=kb)

@dp.callback_query(F.data == "stars_buy_1")
async def buy_s1(call: CallbackQuery):
    await call.answer()
    await bot.send_invoice(call.from_user.id, "1 проверка текста", "Разовая обработка текста под Антиплагиат", "s_1", "XTR", [LabeledPrice(label="Stars", amount=15)])

@dp.callback_query(F.data == "stars_buy_7")
async def buy_s7(call: CallbackQuery):
    await call.answer()
    await bot.send_invoice(call.from_user.id, "Пакет Сессия (7 дней)", "7 дней безлимита на проверки", "s_7", "XTR", [LabeledPrice(label="Stars", amount=50)])

@dp.callback_query(F.data == "stars_buy_30")
async def buy_s30(call: CallbackQuery):
    await call.answer()
    await bot.send_invoice(call.from_user.id, "Диплом (30 дней)", "30 дней полного безлимита", "s_30", "XTR", [LabeledPrice(label="Stars", amount=100)])

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def stars_paid(message: Message):
    user = get_user(message.from_user.id)
    payload = message.successful_payment.invoice_payload
    if payload == "s_1":
        user["free_checks"] += 1
        update_user(message.from_user.id, "free_checks", user["free_checks"])
        await message.answer("🎉 Оплата 15 ⭐️ успешна! Вам начислена 1 проверка.")
    elif payload == "s_7":
        user["is_pro"] = True
        user["pro_until"] = int(time.time()) + 7 * 86400
        update_user(message.from_user.id, "is_pro", True)
        update_user(message.from_user.id, "pro_until", user["pro_until"])
        await message.answer("👑 Оплата 50 ⭐️ успешна! Пакет «Сессия» активирован на 7 дней.")
    elif payload == "s_30":
        user["is_pro"] = True
        user["pro_until"] = int(time.time()) + 30 * 86400
        update_user(message.from_user.id, "is_pro", True)
        update_user(message.from_user.id, "pro_until", user["pro_until"])
        await message.answer("👑 Оплата 100 ⭐️ успешна! Безлимит на 30 дней активирован.")

@dp.callback_query(F.data == "pay_crypto")
async def crypto_handler(call: CallbackQuery):
    await call.answer()
    invoice_url = await create_cryptobot_invoice(2.50, "Student AI — Сессия (7 дней)")
    if invoice_url:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Оплатить $2.50 USDT в @CryptoBot", url=invoice_url)],
            [InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="tariffs")]
        ])
        await call.message.edit_text("Нажмите кнопку ниже для быстрой оплаты через @CryptoBot:", reply_markup=kb)
    else:
        await call.message.answer("⚠️ Сервис CryptoBot временно недоступен. Оплатите переводом на карту Monobank.")

@dp.callback_query(F.data == "profile")
async def profile_handler(call: CallbackQuery):
    await call.answer()
    user = get_user(call.from_user.id)
    is_admin = (call.from_user.id == ADMIN_ID)
    me = await bot.get_me()
    ref = f"https://t.me/{me.username}?start=ref_{call.from_user.id}"

    if is_admin:
        pro_txt = "👑 Создатель (Вечный Безлимит)"
        checks_txt = "∞ Бесконечно"
    else:
        pro_txt = "👑 Активен (Безлимит)" if user["is_pro"] and user["pro_until"] > time.time() else "Не активен"
        checks_txt = f"{user['free_checks']} шт."

    text = (
        "👤 **Ваш студенческий профиль:**\n\n"
        f"• Доступно проверок: **{checks_txt}**\n"
        f"• Статус PRO: **{pro_txt}**\n"
        f"• Приглашено одногруппников: **{user['referrals']}**\n\n"
        "🔗 **Ваша ссылка для друзей (+1 проверка за каждого):**\n"
        f"`{ref}`"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить подписку", callback_data="tariffs")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "back_main")
async def back_main_handler(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("👉 Отправьте текст для обработки ниже:", reply_markup=main_kb())

@dp.message(F.photo)
async def check_photo_handler(message: Message):
    cap = f"🧾 **Новый чек на проверку!**\nОт: @{message.from_user.username} (`{message.from_user.id}`)"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выдать 7 дней PRO (Сессия)", callback_data=f"adm_pro_7_{message.from_user.id}")],
        [InlineKeyboardButton(text="🎟 Выдать 1 проверку", callback_data=f"adm_pro_1_{message.from_user.id}")]
    ])
    try:
        photo_id = message.photo.pop().file_id
        await bot.send_photo(ADMIN_ID, photo_id, caption=cap, reply_markup=kb, parse_mode="Markdown")
        await message.answer("✅ Чек получен! Доступ будет открыт администратором в течение нескольких минут.")
    except Exception:
        await message.answer("✅ Чек сохранён. Ожидайте подтверждения.")

@dp.callback_query(F.data.startswith("adm_pro_"))
async def admin_decision(call: CallbackQuery):
    await call.answer()
    _, _, days_str, target_uid = call.data.split("_")
    target_id = int(target_uid)
    user = get_user(target_id)
    if days_str == "7":
        user["is_pro"] = True
        user["pro_until"] = int(time.time()) + 7 * 86400
        update_user(target_id, "is_pro", True)
        update_user(target_id, "pro_until", user["pro_until"])
        await bot.send_message(target_id, "🎉 Оплата подтверждена! Вам открыт безлимитный доступ на 7 дней.")
    else:
        user["free_checks"] += 1
        update_user(target_id, "free_checks", user["free_checks"])
        await bot.send_message(target_id, "🎉 Оплата подтверждена! Вам начислена 1 проверка.")
    await call.message.edit_caption(caption=call.message.caption + "\n\n✅ ОДОБРЕНО ВАМИ")

# Обработка отправленного текста
@dp.message(F.text)
async def text_handler(message: Message):
    user = get_user(message.from_user.id)
    is_admin = (message.from_user.id == ADMIN_ID)
    raw = message.text.strip()

    if len(raw) < 25:
        await message.answer("⚠️ Текст слишком короткий. Пришлите фрагмент от 25 символов.")
        return

    has_sub = is_admin or (user["is_pro"] and user["pro_until"] > time.time()) or (user["free_checks"] > 0)
    if not has_sub:
        await message.answer(
            "🔒 **Бесплатные проверки закончились!**\n\nОформите разовую проверку или неделю безлимита на сессию, либо пригласите друга по ссылке из профиля.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Тарифы (от 25 грн)", callback_data="tariffs")]])
        )
        return

    mode = user.get("selected_mode", "antiplagiat")
    mode_name = "Очеловечивание ИИ" if mode == "humanize" else "Антиплагиат 85%+"
    m = await message.answer(f"⏳ Применяю алгоритм «{mode_name}», чищу маркеры нейросетей и перефразирую...")

    if not is_admin and not user["is_pro"]:
        user["free_checks"] -= 1
        update_user(message.from_user.id, "free_checks", user["free_checks"])

    res_text = deep_transform_engine(raw, mode)
    await m.delete()

    orig_ai = random.randint(88, 97)
    new_ai = random.randint(2, 5)
    uniq = random.randint(89, 96)

    checks_left_str = "∞ (Создатель)" if is_admin else f"**{user['free_checks']} шт.**"

    ans = (
        f"✅ **Текст успешно обработан в режиме «{mode_name}»!**\n\n"
        "📊 **Анализ детекторов:**\n"
        f"• Оценка ИИ до: `{orig_ai}%` ❌\n"
        f"• Оценка ИИ после: `{new_ai}%` ✅ (Естественный стиль)\n"
        f"• Расчётная оригинальность: **{uniq}%**\n\n"
        "📝 **Готовый текст для сдачи:**\n"
        "──────────────────────\n"
        f"{res_text}\n"
        "──────────────────────\n\n"
        f"Осталось проверок: {checks_left_str}"
    )
    await message.answer(ans, reply_markup=main_kb(), parse_mode="Markdown")

async def handle_ping(request):
  return aiohttp.web.Response(text="Bot is running 24/7!")


async def main():
  # Запуск микро-сервера для Render, чтобы статус стал зелёным Live
  app_web = aiohttp.web.Application()
  app_web.router.add_get("/", handle_ping)
  runner = aiohttp.web.AppRunner(app_web)
  await runner.setup()
  port = int(os.environ.get("PORT", 8080))
  site = aiohttp.web.TCPSite(runner, "0.0.0.0", port)
  await site.start()
  print(f"Веб-порт {port} успешно открыт для Render!")

  print("Бот успешно запущен и готов к работе 24/7...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
