import asyncio
import logging
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

TOKEN = "8724496319:AAEWFWlIk8aE78dBShiiAsx3ZRue-X88yPQ"
CHANNEL_ID = -1001957079286 
ADMIN_ID = 851787801       

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# دیتابیس‌های موقت درون حافظه
authenticated_users = {} 
active_actions = {}      
all_players = set() # برای آمار و پیام همگانی

class GameStates(StatesGroup):
    waiting_for_code = State()
    main_menu = State()
    admin_menu = State()
    admin_broadcast = State()
    
    # لشکرکشی
    camp_origin = State()
    camp_dest = State()
    camp_time = State()
    camp_stats = State()
    camp_confirm = State()
    
    # اعلان جنگ
    war_target = State()
    war_stats = State()
    war_confirm = State()
    
    # بیانیه
    ann_media = State()
    
    # محاصره
    siege_target = State()
    siege_stats = State()
    siege_confirm = State()

    # عملیات‌های تعاملی کانال
    redirect_target = State()
    redirect_time = State()
    ambush_stats = State()

CAMP_PHOTO = "https://i.ibb.co/Vp0g6W5/image.png" 
WAR_PHOTO = "https://images.unsplash.com/photo-1618336753974-aae8e04506aa?q=80&w=600"
SIEGE_PHOTO = "https://images.unsplash.com/photo-1599740489246-0f33e7228f04?q=80&w=600"

# --- کیبوردها ---
def get_main_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="⚔️ لشکرکشی")
    builder.button(text="🛡️ اعلان جنگ")
    builder.button(text="🏰 محاصره")
    builder.button(text="📜 ثبت بیانیه")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📢 پیام همگانی")
    builder.button(text="📊 آمار ربات")
    builder.button(text="🔙 خروج از پنل")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_confirm_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ تایید")
    builder.button(text="❌ لغو")
    builder.button(text="🔙 بازگشت")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_back_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔙 بازگشت")
    return builder.as_markup(resize_keyboard=True)

def get_channel_buttons(action_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 بک", callback_data=f"chan_back:{action_id}")
    builder.button(text="🔄 تغییر مسیر", callback_data=f"chan_redir:{action_id}")
    builder.button(text="🪓 کمین", callback_data=f"chan_ambush:{action_id}")
    builder.adjust(3)
    return builder.as_markup()

def get_war_channel_buttons(action_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ لغو دستور جنگ (۱۰ دقیقه)", callback_data=f"chan_cancelwar:{action_id}")
    return builder.as_markup()

def get_siege_channel_buttons(action_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ لغو محاصره", callback_data=f"chan_cancelsiege:{action_id}")
    return builder.as_markup()

# --- هسته احراز هویت ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear() 
    user_id = message.from_user.id
    if user_id in authenticated_users:
        role = authenticated_users[user_id]
        if role == "admin":
            await message.answer("⚡️ سلام رئیس! به اتاق فرماندهی بازگشتید.", reply_markup=get_admin_keyboard())
            await state.set_state(GameStates.admin_menu)
        else:
            await message.answer("⚔️ خوش‌آمـدید سرورم، به قلعه خود بازگشتید.", reply_markup=get_main_menu_keyboard())
            await state.set_state(GameStates.main_menu)
    else:
        await message.answer("سلام فرمانده! به بازی خوش آمدید.\n\n🔑 لطفاً **کد ورود** خود را ارسال کنید:")
        await state.set_state(GameStates.waiting_for_code)

@dp.message(GameStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text == "1234":
        authenticated_users[user_id] = "player"
        all_players.add(user_id)
        await message.answer("✅ خوش‌آمـدید سرورم، قلعه شما از کشور ثبت شد.", reply_markup=get_main_menu_keyboard())
        await state.set_state(GameStates.main_menu)
    elif message.text == "8888":
        authenticated_users[user_id] = "admin"
        await message.answer("⚡️ سلام رئیس! پنل مدیریت ادمین فعال شد.", reply_markup=get_admin_keyboard())
        await state.set_state(GameStates.admin_menu)
    else:
        await message.answer("❌ کد اشتباه است! مجدداً تلاش کنید:")

@dp.message(F.text == "🔙 بازگشت")
async def global_back(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in authenticated_users:
        if authenticated_users[user_id] == "admin":
            await message.answer("پنل مدیریت:", reply_markup=get_admin_keyboard())
            await state.set_state(GameStates.admin_menu)
        else:
            await message.answer("🔙 به منوی اصلی بازگشتید:", reply_markup=get_main_menu_keyboard())
            await state.set_state(GameStates.main_menu)

# ==================== پنل مدیریت (ادمین) ====================
@dp.message(F.text == "📊 آمار ربات", GameStates.admin_menu)
async def admin_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"📊 **آمار فعلی بازی:**\n\n👥 تعداد بازیکنان فعال ثبت شده: `{len(all_players)}` کاربر")

@dp.message(F.text == "📢 پیام همگانی", GameStates.admin_menu)
async def admin_broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("📬 لطفاً پیام خود را (متن یا رسانه) جهت ارسال به تمام پلیرها بفرستید:", reply_markup=get_back_keyboard())
        await state.set_state(GameStates.admin_broadcast)

@dp.message(GameStates.admin_broadcast)
async def admin_broadcast_send(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    count = 0
    for p_id in all_players:
        try:
            if message.photo:
                await bot.send_photo(chat_id=p_id, photo=message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(chat_id=p_id, video=message.video.file_id, caption=message.caption)
            else:
                await bot.send_message(chat_id=p_id, text=message.text)
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ پیام همگانی با موفقیت به `{count}` بازیکن تحویل داده شد.", reply_markup=get_admin_keyboard())
    await state.set_state(GameStates.admin_menu)

@dp.message(F.text == "🔙 خروج از پنل", GameStates.admin_menu)
async def admin_logout(message: types.Message, state: FSMContext):
    await message.answer("از پنل مدیریت خارج شدید. برای ورود مجدد دستور /start را بزنید.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

# ==================== ۱. روند لشکرکشی ====================
@dp.message(F.text == "⚔️ لشکرکشی", GameStates.main_menu)
async def start_campaign(message: types.Message, state: FSMContext):
    await message.answer("📍 مرحله 1: **کشور و شهر مبدا** را وارد کنید:", reply_markup=get_back_keyboard())
    await state.set_state(GameStates.camp_origin)

@dp.message(GameStates.camp_origin)
async def process_camp_origin(message: types.Message, state: FSMContext):
    await state.update_data(origin=message.text)
    await message.answer("🏙️ مرحله 2: **کشور و شهر مقصد** را وارد کنید:", reply_markup=get_back_keyboard())
    await state.set_state(GameStates.camp_dest)

@dp.message(GameStates.camp_dest)
async def process_camp_dest(message: types.Message, state: FSMContext):
    await state.update_data(dest=message.text)
    await message.answer("⏳ مرحله 3: **زمان رسیدن** را وارد کنید:", reply_markup=get_back_keyboard())
    await state.set_state(GameStates.camp_time)

@dp.message(GameStates.camp_time)
async def process_camp_time(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer("📊 مرحله 4: **آمار لشکرکشی** خود را وارد کنید:", reply_markup=get_back_keyboard())
    await state.set_state(GameStates.camp_stats)

@dp.message(GameStates.camp_stats)
async def process_camp_stats(message: types.Message, state: FSMContext):
    await state.update_data(stats=message.text)
    data = await state.get_data()
    preview = f"🔍 **پیش‌نویس لشکرکشی:**\n\nمبدا: {data['origin']}\nمقصد: {data['dest']}\nزمان: {data['time']}\nآمار: {data['stats']}\n\n⁉️ تایید می‌فرمایید؟"
    await message.answer(preview, reply_markup=get_confirm_keyboard())
    await state.set_state(GameStates.camp_confirm)

@dp.message(GameStates.camp_confirm)
async def process_camp_final(message: types.Message, state: FSMContext):
    if message.text in ["✅ تایید", "✅ Tایید"]:
        data = await state.get_data()
        action_id = str(int(time.time()))
        active_actions[action_id] = {"owner_id": message.from_user.id, "type": "campaign", "data": data}
        
        chan_text = f"⚔️ **[ گزارش تحرکات ارتش ]**\n\n🚨 ارتش قدرتمند از مبدا **{data['origin']}** به سمت **{data['dest']}** به حرکت در آمده است!\n\n⏳ **زمان رسیدن:** {data['time']}"
        try:
            sent_msg = await bot.send_photo(chat_id=CHANNEL_ID, photo=CAMP_PHOTO, caption=chan_text, reply_markup=get_channel_buttons(action_id), parse_mode="Markdown")
            active_actions[action_id]["msg_id"] = sent_msg.message_id
        except Exception:
            sent_msg = await bot.send_message(chat_id=CHANNEL_ID, text=chan_text, reply_markup=get_channel_buttons(action_id), parse_mode="Markdown")
            active_actions[action_id]["msg_id"] = sent_msg.message_id
            
        adm_text = f"📬 **گزارش فنی لشکرکشی**\n👤 فرستنده: {message.from_user.first_name} (ID: `{message.from_user.id}`)\n📍 مبدا: {data['origin']}\n🎯 مقصد: {data['dest']}\n⏳ زمان: {data['time']}\n📊 آمار دقیق عددی: {data['stats']}"
        await bot.send_message(chat_id=ADMIN_ID, text=adm_text, parse_mode="Markdown")
        await message.answer("لشکرکشی شما تایید شد. ✅", reply_markup=get_main_menu_keyboard())
    else:
        await message.answer("لشکرکشی شما لغو شد. ❌", reply_markup=get_main_menu_keyboard())
    await state.set_state(GameStates.main_menu)

# ==================== ۲. روند اعلان جنگ ====================
@dp.message(F.text == "🛡️ اعلان جنگ", GameStates.main_menu)
async def start_war(message: types.Message, state: FSMContext):
    await message.answer("🛡️ مرحله 1: **نام شهر/کشور هدف** برای نبرد را وارد کنید:", reply_markup=get_back_keyboard())
    await state.set_state(GameStates.war_target)

@dp.message(GameStates.war_target)
async def process_war_target(message: types.Message, state: FSMContext):
    await state.update_data(target=message.text)
    await message.answer("📊 مرحله 2: **آمار نیروهای تهاجمی** خود را وارد کنید:", reply_markup=get_back_keyboard())
    await state.set_state(GameStates.war_stats)

@dp.message(GameStates.war_stats)
async def process_war_stats(message: types.Message, state: FSMContext):
    await state.update_data(stats=message.text)
    data = await state.get_data()
    preview = f"🔍 **پیش‌نویس فرمان جنگ:**\n\n🎯 هدف نبرد: {data['target']}\n📊 آمار ارتش: {data['stats']}\n\n⁉️ صادر شود؟"
    await message.answer(preview, reply_markup=get_confirm_keyboard())
    await state.set_state(GameStates.war_confirm)

@dp.message(GameStates.war_confirm)
async def process_war_final(message: types.Message, state: FSMContext):
    if message.text in ["✅ تایید", "✅ Tایید"]:
        data = await state.get_data()
        action_id = str(int(time.time()))
        active_actions[action_id] = {"owner_id": message.from_user.id, "type": "war", "time_created": time.time(), "data": data}
        
        chan_text = f"🔥 **[ طبل جنگ نواخته شد! ]**\n\n👑 فرمانی رسمی صادر شد! ارتش‌های خط مقدم آماده نبرد علیه **{data['target']}** شدند!"
        sent_msg = await bot.send_photo(chat_id=CHANNEL_ID, photo=WAR_PHOTO, caption=chan_text, reply_markup=get_war_channel_buttons(action_id), parse_mode="Markdown")
        active_actions[action_id]["msg_id"] = sent_msg.message_id
        
        adm_text = f"🚨 **گزارش فنی جنگ**\n👤 فرمانده: {message.from_user.first_name}\n🎯 هدف: {data['target']}\n📊 آمار تهاجم: {data['stats']}"
        await bot.send_message(chat_id=ADMIN_ID, text=adm_text, parse_mode="Markdown")
        await message.answer("اعلان جنگ شما تایید شد. ✅", reply_markup=get_main_menu_keyboard())
    else:
        await message.answer("اعلان جنگ شما لغو شد. ❌", reply_markup=get_main_menu_keyboard())
    await state.set_state(GameStates.main_menu)

# ==================== ۳. روند محاصره ====================
@dp.message(F.text == "🏰 محاصره", GameStates.main_menu)
async def start_siege(message: types.Message, state: FSMContext):
    await message.answer("🏰 مرحله 1: **نام شهری که محاصره می‌شود** را وارد کنید:", reply_markup=get_back_keyboard())
    await state.set_state(GameStates.siege_target)

@dp.message(GameStates.siege_target)
async def process_siege_target(message: types.Message, state: FSMContext):
    await state.update_data(target=message.text)
    await message.answer("📊 مرحله 2: **آمار نیروهای محاصره‌کننده** را وارد کنید:", reply_markup=get_back_keyboard())
    await state.set_state(GameStates.siege_stats)

@dp.message(GameStates.siege_stats)
async def process_siege_stats(message: types.Message, state: FSMContext):
    await state.update_data(stats=message.text)
    data = await state.get_data()
    preview = f"🔍 **پیش‌نویس فرمان محاصره:**\n\n🏰 شهر هدف: {data['target']}\n📊 آمار قوا: {data['stats']}\n\n⁉️ آغاز شود؟"
    await message.answer(preview, reply_markup=get_confirm_keyboard())
    await state.set_state(GameStates.siege_confirm)

@dp.message(GameStates.siege_confirm)
async def process_siege_final(message: types.Message, state: FSMContext):
    if message.text in ["✅ تایید", "✅ Tایید"]:
        data = await state.get_data()
        action_id = str(int(time.time()))
        active_actions[action_id] = {"owner_id": message.from_user.id, "type": "siege", "data": data}
        
        chan_text = f"⛓ **[ گزارش وضعیت محاصره ]**\n\n🛡️ شهر راهبردی **{data['target']}** کاملاً محاصره شده و در وضعیت انسداد نظامی قرار گرفت!"
        sent_msg = await bot.send_photo(chat_id=CHANNEL_ID, photo=SIEGE_PHOTO, caption=chan_text, reply_markup=get_siege_channel_buttons(action_id), parse_mode="Markdown")
        active_actions[action_id]["msg_id"] = sent_msg.message_id
        
        adm_text = f"🧱 **گزارش فنی محاصره**\n👤 عامل: {message.from_user.first_name}\n🏰 شهر: {data['target']}\n📊 نیروها: {data['stats']}"
        await bot.send_message(chat_id=ADMIN_ID, text=adm_text, parse_mode="Markdown")
        await message.answer("فرمان محاصره شما تایید شد. ✅", reply_markup=get_main_menu_keyboard())
    else:
        await message.answer("فرمان محاصره شما لغو شد. ❌", reply_markup=get_main_menu_keyboard())
    await state.set_state(GameStates.main_menu)

# ==================== ۴. ثبت بیانیه رسمی ====================
@dp.message(F.text == "📜 ثبت بیانیه", GameStates.main_menu)
async def start_announcement(message: types.Message, state: FSMContext):
    await message.answer("📜 **متن، عکس، ویدیو یا داکیومنت بیانیه** خود را ارسال کنید:", reply_markup=get_back_keyboard())
    await state.set_state(GameStates.ann_media)

@dp.message(GameStates.ann_media)
async def process_ann_media(message: types.Message, state: FSMContext):
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    header = f"📜 **[ بیانیه رسمی پادشاهی ]**\n\n📢 ابلاغیه رسمی از طرف امپراتوری\n👤 توسط: {username}\n\n"
    
    if message.photo:
        await bot.send_photo(chat_id=CHANNEL_ID, photo=message.photo[-1].file_id, caption=header + (message.caption or ""), parse_mode="Markdown")
    elif message.video:
        await bot.send_video(chat_id=CHANNEL_ID, video=message.video.file_id, caption=header + (message.caption or ""), parse_mode="Markdown")
    else:
        await bot.send_message(chat_id=CHANNEL_ID, text=header + f"« {message.text} »", parse_mode="Markdown")
        
    await bot.send_message(chat_id=ADMIN_ID, text=f"📢 **بیانیه جدید منتشر شد**\n👤 فرستنده: {message.from_user.first_name}")
    await message.answer("بیانیه شما با موفقیت در کانال بازی طنین‌انداز شد. 📢", reply_markup=get_main_menu_keyboard())
    await state.set_state(GameStates.main_menu)

# ==================== مدیریت دکمه‌های شیشه‌ای کانال ====================
@dp.callback_query(F.data.startswith("chan_back:"))
async def handle_inline_back(callback: types.CallbackQuery):
    action_id = callback.data.split(":")[1]
    action = active_actions.get(action_id)
    if not action: return await callback.answer("این عملیات قدیمی شده یا یافت نشد.", show_alert=True)
    if callback.from_user.id != action["owner_id"]: return await callback.answer("❌ این ارتش متعلق به شما نیست!", show_alert=True)
        
    await bot.edit_message_caption(chat_id=CHANNEL_ID, message_id=action["msg_id"], caption="❌ **[ این لشکرکشی لغو و عقب‌نشینی شد ]**", reply_markup=None)
    await bot.send_message(chat_id=CHANNEL_ID, text=f"🔙 **عقب‌نشینی:** نیروهای تحت امر فرمانده {callback.from_user.first_name} به پادگان‌های خود بازگشتند.")
    await bot.send_message(chat_id=ADMIN_ID, text=f"📯 **گزارش لغو:** {callback.from_user.first_name} ارتش خود را عقب کشید.")
    await callback.answer("دستور عقب‌نشینی صادر شد.")

@dp.callback_query(F.data.startswith("chan_redir:"))
async def handle_inline_redirect(callback: types.CallbackQuery, state: FSMContext):
    action_id = callback.data.split(":")[1]
    action = active_actions.get(action_id)
    if not action or callback.from_user.id != action["owner_id"]: return await callback.answer("❌ این ارتش متعلق به شما نیست!", show_alert=True)
        
    await callback.answer()
    await bot.send_message(chat_id=callback.from_user.id, text=f"🔄 ارتش شما در مسیر جابجایی است.\n📍 **مقصد جدید** را وارد کنید:", reply_markup=get_back_keyboard())
    await state.update_data(current_action_id=action_id)
    await state.set_state(GameStates.redirect_target)

@dp.message(GameStates.redirect_target)
async def process_redir_target(message: types.Message, state: FSMContext):
    await state.update_data(new_dest=message.text)
    await message.answer("⏳ **زمان رسیدن جدید** را وارد کنید:")
    await state.set_state(GameStates.redirect_time)

@dp.message(GameStates.redirect_time)
async def process_redir_time(message: types.Message, state: FSMContext):
    data = await state.get_data()
    action_id = data["current_action_id"]
    
    chan_text = f"🔄 **[ تغییر مسیر ناگهانی ]**\n\n🚨 ارتش در حال حرکت، مسیر خود را به سمت مقصد جدید **{data['new_dest']}** تغییر داد!\n⏳ **زمان رسیدن جدید:** {message.text}"
    await bot.send_message(chat_id=CHANNEL_ID, text=chan_text)
    await bot.send_message(chat_id=ADMIN_ID, text=f"🔄 **تغییر مسیر:** {message.from_user.first_name} ارتش خود را به {data['new_dest']} هدایت کرد.")
    await message.answer("مسیر ارتش تغییر یافت.", reply_markup=get_main_menu_keyboard())
    await state.set_state(GameStates.main_menu)

@dp.callback_query(F.data.startswith("chan_ambush:"))
async def handle_inline_ambush(callback: types.CallbackQuery, state: FSMContext):
    action_id = callback.data.split(":")[1]
    action = active_actions.get(action_id)
    if action and callback.from_user.id == action["owner_id"]: return await callback.answer("❌ شما نمی‌توانید به ارتش خودتان کمین بزنید!", show_alert=True)
        
    await callback.answer()
    await bot.send_message(chat_id=callback.from_user.id, text="🪓 **طرح‌ریزی کمین:**\n📊 آمار نیروهای مهاجم خود برای کمین را وارد کنید:", reply_markup=get_back_keyboard())
    await state.update_data(ambush_target_action=action_id)
    await state.set_state(GameStates.ambush_stats)

@dp.message(GameStates.ambush_stats)
async def process_ambush(message: types.Message, state: FSMContext):
    data = await state.get_data()
    action_id = data["ambush_target_action"]
    action = active_actions[action_id]
    
    await bot.send_message(chat_id=CHANNEL_ID, text=f"🪓 **[ شبیخون و کمین! ]**\n\n💥 نیروهای ناشناس در مسیر حرکت به سمت ارتش کشور کمین زدند! نبرد سنگینی در جریان است!")
    
    asyncio.create_task(send_timer_notification(action["owner_id"], message.from_user.id, action_id, message.text))
    await message.answer("کمین با موفقیت ثبت شد. منتظر دستورات ادمین باشید.", reply_markup=get_main_menu_keyboard())
    await state.set_state(GameStates.main_menu)

async def send_timer_notification(defender_id, attacker_id, action_id, attacker_stats):
    msg = "🚨 **اعلام وضعیت اضطراری نبرد**\n\n⚔️ نیروهای شما درگیر یک نبرد کمین شده‌اند! شما **۳۰ دقیقه** فرصت دارید تا «سناریوی دفاع یا تهاجم» خود را به همینجا ارسال کنید. در غیر این صورت شکست خواهید خورد."
    try:
        await bot.send_message(chat_id=defender_id, text=msg)
        await bot.send_message(chat_id=attacker_id, text=msg)
    except Exception: pass
    
    adm_report = f"🪓 **گزارش وقوع کمین نظامی**\n\n🛡 مدافع: ID `{defender_id}`\n⚔️ مهاجم کمین‌زننده: ID `{attacker_id}`\n📊 آمار ارتش کمین‌زننده: {attacker_stats}"
    await bot.send_message(chat_id=ADMIN_ID, text=adm_report)

@dp.callback_query(F.data.startswith("chan_cancelwar:"))
async def handle_cancel_war(callback: types.CallbackQuery):
    action_id = callback.data.split(":")[1]
    action = active_actions.get(action_id)
    if not action or callback.from_user.id != action["owner_id"]: return await callback.answer("❌ این دستور جنگ متعلق به شما نیست!", show_alert=True)
    if time.time() - action["time_created"] > 600: return await callback.answer("⏳ مهلت ۱۰ دقیقه‌ای لغو این دستور به پایان رسیده است!", show_alert=True)
        
    await bot.edit_message_caption(chat_id=CHANNEL_ID, message_id=action["msg_id"], caption="🛡️ **[ این دستور جنگ لغو گردید ]**", reply_markup=None)
    await bot.send_message(chat_id=ADMIN_ID, text=f"🛡️ **لغو جنگ:** {callback.from_user.first_name} فرمان جنگ را لغو کرد.")
    await callback.answer("فرمان جنگ لغو شد.")

@dp.callback_query(F.data.startswith("chan_cancelsiege:"))
async def handle_cancel_siege(callback: types.CallbackQuery):
    action_id = callback.data.split(":")[1]
    action = active_actions.get(action_id)
    if not action or callback.from_user.id != action["owner_id"]: return await callback.answer("❌ این محاصره متعلق به شما نیست!", show_alert=True)
        
    await bot.edit_message_caption(chat_id=CHANNEL_ID, message_id=action["msg_id"], caption="⛓ **[ محاصره این شهر شکسته و پایان یافت ]**", reply_markup=None)
    await bot.send_message(chat_id=ADMIN_ID, text=f"🧱 **لغو محاصره:** {callback.from_user.first_name} به محاصره پایان داد.")
    await callback.answer("محاصره لغو شد.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
