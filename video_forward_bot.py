"""
ربات تلگرام (نسخه‌ی دوم):

روند کار:
1. کاربر ویدیویی توی گروه مشخص می‌فرستد یا فوروارد می‌کند.
2. ربات کپشن قبلی ویدیو را نادیده می‌گیرد و روی همان پیام ریپلای می‌کند:
   "کپشن خود را وارد کنید"
3. کاربر روی همان پیام ریپلای می‌کند و کپشن دلخواهش را می‌نویسد.
4. ربات ویدیو را با همان کپشن + تگ (به‌صورت نقل‌قول/blockquote) توی کانال پست می‌کند.

روی Railway اجرا می‌شود (به‌صورت Worker با polling - نیازی به وب‌هوک نیست).
"""

import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============ تنظیمات ============
# روی Railway این مقادیر را از بخش Variables ست کنید (پایین توضیح داده شده)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
SOURCE_GROUP_ID = int(os.environ.get("SOURCE_GROUP_ID", "-1001234567890"))
TARGET_CHANNEL_ID = int(os.environ.get("TARGET_CHANNEL_ID", "-1009876543210"))

# کلمه‌ی اول تگ (بولد می‌شود) و مقدار بعد از آن
TAG_LABEL = os.environ.get("TAG_LABEL", "ID")
TAG_VALUE = os.environ.get("TAG_VALUE", "@HiromiyaStudio")

# ===================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# نگهداری موقت: message_id پیام «کپشن خود را وارد کنید» -> file_id ویدیو
pending_videos: dict[int, str] = {}


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if update.effective_chat.id != SOURCE_GROUP_ID:
        return
    if not message.video:
        return

    # کپشن قبلی ویدیو (اگر بود) عمداً نادیده گرفته می‌شود
    prompt = await message.reply_text("لطفاً کپشن خود را وارد کنید (با ریپلای روی همین پیام).")

    pending_videos[prompt.message_id] = message.video.file_id
    logger.info(f"ویدیو دریافت شد و منتظر کپشن ماند. prompt_id={prompt.message_id}")


async def handle_caption_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if update.effective_chat.id != SOURCE_GROUP_ID:
        return
    if not message.reply_to_message:
        return

    prompt_id = message.reply_to_message.message_id
    if prompt_id not in pending_videos:
        return  # این ریپلای مربوط به درخواست کپشن ما نیست

    file_id = pending_videos.pop(prompt_id)
    user_caption = message.text or ""

    # تگ به‌صورت نقل‌قول (blockquote) با کلمه‌ی اول بولد - از HTML استفاده می‌کنیم
    tag_html = f"<blockquote><b>{TAG_LABEL}</b> : {TAG_VALUE}</blockquote>"
    final_caption = f"{user_caption}\n\n{tag_html}"

    try:
        await context.bot.send_video(
            chat_id=TARGET_CHANNEL_ID,
            video=file_id,
            caption=final_caption,
            parse_mode="HTML",
        )
        await message.reply_text("✅ ویدیو با موفقیت در کانال پست شد.")
        logger.info("ویدیو با کپشن نهایی به کانال ارسال شد.")
    except Exception as e:
        logger.error(f"خطا در ارسال ویدیو به کانال: {e}")
        await message.reply_text(f"❌ خطا در ارسال: {e}")


def main():
    if BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("لطفاً BOT_TOKEN را به‌عنوان Environment Variable ست کنید.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_caption_reply))

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
