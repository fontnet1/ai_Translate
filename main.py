from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from translate import Translator
import logging

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

# مدیریت حالت‌های کاربران
WAITING = {}
ACTIVE_CHATS = {}  # {user1_id: user2_id, user2_id: user1_id}
USER_LANG = {}  # {user_id: 'fa' یا 'uk'}

# ذخیره ارتباط پیام‌ها برای پشتیبانی از ریپلای
MESSAGE_MAP = {}

# توکن ربات خود را اینجا وارد کنید
TOKEN = "6494401860:AAGbVTYH2L-uSIhMCJj7bbujuBSr4q_wCV4"

# دیکشنری ترجمه کلمات کوتاه برای بهبود کیفیت
SHORT_TRANSLATIONS = {
    ("uk", "fa"): {
        "Бувай": "خداحافظ",
        "Привіт": "سلام",
        "Дякую": "متشکرم",
        "Так": "بله",
        "Ні": "خیر",
        "Доброго ранку": "صبح بخیر",
        "Добрий день": "روز بخیر",
        "Добрий вечір": "عصر بخیر",
        "Як справи?": "حالتان چطور است؟",
        "Що нового?": "چه خبر؟"
    },
    ("fa", "uk"): {
        "خداحافظ": "Бувай",
        "سلام": "Привіт",
        "متشکرم": "Дякую",
        "بله": "Так",
        "خیر": "Ні",
        "صبح بخیر": "Доброго ранку",
        "روز بخیر": "Добрий день",
        "عصر بخیر": "Добрий вечір",
        "حالتان چطور است؟": "Як справи?",
        "چه خبر؟": "Що нового?"
    }
}


def translate_message(text, src_lang, dest_lang):
    """ترجمه متن با استفاده از کتابخانه translate"""
    try:
        # بررسی ترجمه کلمات کوتاه از دیکشنری
        key = (src_lang, dest_lang)
        if text in SHORT_TRANSLATIONS.get(key, {}):
            return SHORT_TRANSLATIONS[key][text]

        # ترجمه با کتابخانه translate
        translator = Translator(
            from_lang=src_lang,
            to_lang=dest_lang,
            provider='mymemory'  # بهترین گزینه برای فارسی-اوکراینی
        )

        # انجام ترجمه
        translated = translator.translate(text)

        # اگر ترجمه خالی بود، متن اصلی را برگردان
        return translated if translated.strip() else text

    except Exception as e:
        logger.error(f"خطای ترجمه: {str(e)}")
        return text


def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    update.message.reply_text(
        "👋 به ربات چت دو نفره خوش آمدید!\n\n"
        "1. ابتدا زبان خود را با /setlang تنظیم کنید.\n"
        "2. برای یافتن کاربر دیگر از /connect استفاده کنید.\n"
        "3. برای قطع ارتباط از /disconnect استفاده کنید.\n\n"
        "✨ پشتیبانی از: متن، استیکر، عکس، ویدیو، گیف، فایل، لینک و ریپلای")


def set_lang(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    keyboard = [[InlineKeyboardButton("فارسی 🇮🇷", callback_data='fa')],
                [InlineKeyboardButton("اوکراینی 🇺🇦", callback_data='uk')]]
    update.message.reply_text("زبان خود را انتخاب کنید:",
                              reply_markup=InlineKeyboardMarkup(keyboard))


def lang_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    lang = query.data
    USER_LANG[user_id] = lang
    query.answer()
    query.edit_message_text(
        f"✅ زبان شما به {'فارسی' if lang == 'fa' else 'اوکراینی'} تنظیم شد!")


def connect(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_id not in USER_LANG:
        update.message.reply_text(
            "❌ ابتدا زبان خود را با /setlang تنظیم کنید!")
        return

    if user_id in ACTIVE_CHATS or user_id in WAITING:
        update.message.reply_text(
            "⚠️ شما در حال حاضر در چت فعال هستید یا در انتظار اتصال!")
        return

    WAITING[user_id] = True
    update.message.reply_text("🔎 در جستجوی کاربر دیگر...")

    # جستجوی کاربر دوم
    for other_id in list(WAITING.keys()):
        if other_id != user_id and other_id not in ACTIVE_CHATS:
            # اتصال دو کاربر
            del WAITING[user_id]
            del WAITING[other_id]
            ACTIVE_CHATS[user_id] = other_id
            ACTIVE_CHATS[other_id] = user_id

            context.bot.send_message(
                user_id,
                f"✅ متصل شدید! زبان طرف مقابل: {'اوکراینی 🇺🇦' if USER_LANG[other_id] == 'uk' else 'فارسی 🇮🇷'}\n"
                "هر نوع محتوایی ارسال کنید (متن، استیکر، عکس، ...)")
            context.bot.send_message(
                other_id,
                f"✅ متصل شدید! زبان طرف مقابل: {'اوکراینی 🇺🇦' if USER_LANG[user_id] == 'uk' else 'فارسی 🇮🇷'}\n"
                "هر نوع محتوایی ارسال کنید (متن، استیکر، عکس, ...)")
            return

    update.message.reply_text("⏳ لطفاً منتظر بمانید...")


def disconnect(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_id in ACTIVE_CHATS:
        other_id = ACTIVE_CHATS[user_id]
        del ACTIVE_CHATS[user_id]
        del ACTIVE_CHATS[other_id]
        update.message.reply_text("❌ ارتباط قطع شد.")
        context.bot.send_message(other_id, "❌ کاربر مقابل ارتباط را قطع کرد.")
    elif user_id in WAITING:
        del WAITING[user_id]
        update.message.reply_text("❌ جستجو متوقف شد.")
    else:
        update.message.reply_text("⚠️ شما در حال چت نیستید!")


def store_message_mapping(user_id: int, user_msg_id: int, bot_msg: Message):
    """ذخیره ارتباط بین پیام کاربر و پیام ارسال شده توسط ربات"""
    MESSAGE_MAP[(bot_msg.chat_id, bot_msg.message_id)] = (user_id, user_msg_id)


def handle_reply(update: Update, context: CallbackContext, other_id: int):
    """پردازش ریپلای‌ها و ارسال آن‌ها به همراه متن اصلی"""
    reply_to = update.message.reply_to_message

    # یافتن پیام اصلی که کاربر به آن ریپلای کرده
    if reply_to and (reply_to.chat.id, reply_to.message_id) in MESSAGE_MAP:
        original_sender_id, original_msg_id = MESSAGE_MAP[(
            reply_to.chat.id, reply_to.message_id)]

        # دریافت متن اصلی
        try:
            original_msg = context.bot.get_chat(
                original_sender_id).get_message(original_msg_id)
            original_text = original_msg.text

            # ترجمه متن اصلی
            src_lang = USER_LANG.get(original_sender_id, 'fa')
            dest_lang = USER_LANG.get(update.message.from_user.id, 'uk')
            translated_original = translate_message(original_text, src_lang,
                                                    dest_lang)

            # ترجمه ریپلای فعلی
            current_text = update.message.text
            src_lang_current = USER_LANG.get(update.message.from_user.id, 'fa')
            dest_lang_current = USER_LANG.get(other_id, 'uk')
            translated_current = translate_message(current_text,
                                                   src_lang_current,
                                                   dest_lang_current)

            # ارسال ریپلای با نمایش متن اصلی و ترجمه شده
            response = (f"↩️ در پاسخ به:\n"
                        f"🔤 {translated_original}\n\n"
                        f"💬 پاسخ شما:\n"
                        f"🔤 {translated_current}\n\n"
                        f"---\n"
                        f"✏️ متن اصلی پاسخ: {current_text}\n"
                        f"✏️ متن اصلی پیام: {original_text}")

            context.bot.send_message(chat_id=other_id, text=response)
            return True

        except Exception as e:
            logger.error(f"خطا در پردازش ریپلای: {e}")

    return False


def handle_all_messages(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # بررسی اتصال کاربر
    if user_id not in ACTIVE_CHATS:
        update.message.reply_text(
            "⚠️ ابتدا با /connect به یک کاربر متصل شوید!")
        return

    other_id = ACTIVE_CHATS[user_id]
    src_lang = USER_LANG.get(user_id, 'fa')
    dest_lang = USER_LANG.get(other_id, 'uk')

    # 1. پردازش ریپلای‌ها
    if update.message.reply_to_message:
        if handle_reply(update, context, other_id):
            return

    # 2. پردازش متن ساده
    if update.message.text:
        text = update.message.text
        translated = translate_message(text, src_lang, dest_lang)

        # اگر ترجمه با متن اصلی متفاوت است، هر دو را نمایش بده
        if translated != text:
            response = f"🔤 {translated}\n\n---\n✏️ متن اصلی: {text}"
        else:
            response = text

        sent_message = context.bot.send_message(chat_id=other_id,
                                                text=response)
        store_message_mapping(user_id, update.message.message_id, sent_message)

    # 3. پردازش استیکر
    elif update.message.sticker:
        sent_message = context.bot.send_sticker(
            chat_id=other_id, sticker=update.message.sticker.file_id)
        store_message_mapping(user_id, update.message.message_id, sent_message)

    # 4. پردازش عکس (با کپشن)
    elif update.message.photo:
        photo = update.message.photo[-1].file_id  # بزرگترین سایز
        caption = update.message.caption

        if caption:
            translated_caption = translate_message(caption, src_lang,
                                                   dest_lang)
            sent_message = context.bot.send_photo(chat_id=other_id,
                                                  photo=photo,
                                                  caption=translated_caption)
        else:
            sent_message = context.bot.send_photo(chat_id=other_id,
                                                  photo=photo)

        store_message_mapping(user_id, update.message.message_id, sent_message)

    # 5. پردازش ویدیو (با کپشن)
    elif update.message.video:
        video = update.message.video.file_id
        caption = update.message.caption

        if caption:
            translated_caption = translate_message(caption, src_lang,
                                                   dest_lang)
            sent_message = context.bot.send_video(chat_id=other_id,
                                                  video=video,
                                                  caption=translated_caption)
        else:
            sent_message = context.bot.send_video(chat_id=other_id,
                                                  video=video)

        store_message_mapping(user_id, update.message.message_id, sent_message)

    # 6. پردازش گیف/انیمیشن
    elif update.message.animation:
        sent_message = context.bot.send_animation(
            chat_id=other_id, animation=update.message.animation.file_id)
        store_message_mapping(user_id, update.message.message_id, sent_message)

    # 7. پردازش فایل‌های مستند
    elif update.message.document:
        sent_message = context.bot.send_document(
            chat_id=other_id, document=update.message.document.file_id)
        store_message_mapping(user_id, update.message.message_id, sent_message)

    # 8. پردازش ویس
    elif update.message.voice:
        sent_message = context.bot.send_voice(
            chat_id=other_id, voice=update.message.voice.file_id)
        store_message_mapping(user_id, update.message.message_id, sent_message)

    # 9. پردازش لینک‌ها
    elif update.message.entities and any(e.type == "url"
                                         for e in update.message.entities):
        sent_message = context.bot.send_message(chat_id=other_id,
                                                text=update.message.text)
        store_message_mapping(user_id, update.message.message_id, sent_message)

    # 10. انواع دیگر محتوا
    else:
        sent_message = context.bot.send_message(
            chat_id=other_id,
            text="🔔 کاربر مقابل محتوایی ارسال کرد که قابل نمایش نیست")
        store_message_mapping(user_id, update.message.message_id, sent_message)


def error(update: Update, context: CallbackContext):
    logger.warning(f'Update {update} caused error {context.error}')


def main():
    # ایجاد آپدیتور با توکن مستقیم
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # دستورات
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("setlang", set_lang))
    dp.add_handler(CommandHandler("connect", connect))
    dp.add_handler(CommandHandler("disconnect", disconnect))

    # هندلر همه انواع پیام (غیر از دستورات)
    dp.add_handler(
        MessageHandler(Filters.all & ~Filters.command & ~Filters.status_update,
                       handle_all_messages))

    # کال‌بک‌ها
    dp.add_handler(CallbackQueryHandler(lang_callback))

    # هندلر خطا
    dp.add_error_handler(error)

    # شروع ربات
    logger.info("✅ ربات در حال اجراست...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
