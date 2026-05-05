import logging
import requests
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- الإعدادات ---
# ملاحظة: يفضل وضع التوكن في Variables على Railway واستدعائه بـ os.getenv
BOT_TOKEN = "8263620123:AAEslo1rbEeqCDCkxz1iX_21XzcugPvXhvE"
SHRINKEARN_API = "a92843ecf51915018be63e04fd74664724a935e5"
MIN_WITHDRAWAL = 5.00

# تنبيه: هذه البيانات تضيع عند إعادة تشغيل السيرفر (تحتاج قاعدة بيانات SQLite لاحقاً)
users_db = {}

# إعداد السجلات (Logs) لمعرفة الأخطاء
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- الوظائف المساعدة ---
def shorten_link(url):
    try:
        r = requests.get(
            "https://shrinkearn.com", 
            params={"api": SHRINKEARN_API, "url": url, "format": "json"}, 
            timeout=15
        )
        data = r.json()
        if data.get("status") == "success":
            return data.get("shortenedUrl", "")
    except Exception as e:
        logger.error(f"Error shortening link: {e}")
    return ""

def get_user(user_id, name=""):
    if user_id not in users_db:
        users_db[user_id] = {"name": name, "balance": 0.0, "links": 0}
    return users_db[user_id]

# --- معالجات الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.first_name)
    
    keyboard = [
        [InlineKeyboardButton("🔗 Shorten Link", callback_data="shorten"), InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"), InlineKeyboardButton("💳 Payments", callback_data="payments")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    
    await update.message.reply_text(
        f"🌟 *Welcome to Earn Easy Online!*\n\nHello {user.first_name}! 👋\n\n"
        "💡 Send any link → get short link → share → earn!\n\n"
        f"📌 Min withdrawal: ${MIN_WITHDRAWAL}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    
    if text.startswith("http://") or text.startswith("https://"):
        msg = await update.message.reply_text("⏳ Shortening...")
        short_url = shorten_link(text)
        
        if short_url:
            get_user(user.id, user.first_name)["links"] += 1
            await msg.edit_text(f"✅ *Done!*\n\n🔗 `{short_url}`\n\nShare and earn!", parse_mode="Markdown")
        else:
            await msg.edit_text("❌ Failed to shorten. Please try again later.")
    else:
        await update.message.reply_text("📌 Please send a valid URL starting with http:// or https://")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = get_user(user.id, user.first_name)
    b = data["balance"]

    if query.data == "balance":
        msg = (f"💰 *Balance*\n\n💵 ${b:.2f}\n🔗 Links: {data['links']}\n\n"
               f"{'✅ Can withdraw!' if b >= MIN_WITHDRAWAL else f'❌ Need ${MIN_WITHDRAWAL - b:.2f} more'}")
        await query.edit_message_text(msg, parse_mode="Markdown")
        
    elif query.data == "shorten":
        await query.edit_message_text("🔗 Send me any link now!\n\nExample: https://google.com")
        
    elif query.data == "withdraw":
        if b < MIN_WITHDRAWAL:
            await query.edit_message_text(f"❌ Balance: ${b:.2f}\nNeed ${MIN_WITHDRAWAL - b:.2f} more to withdraw.")
        else:
            keyboard = [
                [InlineKeyboardButton("💚 USDT TRC20", callback_data="pay_usdt")],
                [InlineKeyboardButton("💜 Polygon", callback_data="pay_polygon")],
                [InlineKeyboardButton("❤️ Vodafone Cash", callback_data="pay_vodafone")]
            ]
            await query.edit_message_text(f"💸 Choose payment method:\nYour Balance: ${b:.2f}", reply_markup=InlineKeyboardMarkup(keyboard))
            
    elif query.data == "payments":
        await query.edit_message_text("💳 *Payment Methods*\n\n• USDT TRC20\n• Polygon\n• Vodafone Cash\n\nMinimum Withdrawal: $5.00", parse_mode="Markdown")
        
    elif query.data == "help":
        await query.edit_message_text("❓ How it works:\n1. Send link\n2. Get shortened link\n3. Share it\n4. Earn money when people click!")
        
    elif query.data in ["pay_usdt", "pay_polygon", "pay_vodafone"]:
        methods = {"pay_usdt": "USDT TRC20 wallet address", "pay_polygon": "Polygon wallet address", "pay_vodafone": "Vodafone Cash number"}
        await query.edit_message_text(f"💸 Please send your {methods[query.data]}:")

# --- تشغيل البوت ---
def main():
    # بناء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()

    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    
    # التشغيل بطريقة تمنع التوقف المفاجئ
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
