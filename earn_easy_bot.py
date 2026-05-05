import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ========== SETTINGS ==========
BOT_TOKEN = "8263620123:AAEslo1rbEeqCDCkxz1iX_21XzcugPvXhvE"
SHRINKEARN_API = "a92843ecf51915018be63e04fd74664724a935e5"
ADMIN_ID = 123456789  # غير ده لـ ID بتاعك على تليجرام

# Payment info
MIN_WITHDRAWAL = 5.00  # الحد الأدنى للسحب بالدولار

# Earning rates per click (USD)
TIER1_RATE = 0.010  # USA, UK, Canada
TIER2_RATE = 0.004  # Egypt, Middle East, Europe
TIER3_RATE = 0.001  # Other countries

# ========== DATABASE (بسيط في الذاكرة) ==========
# في الإنتاج استخدم قاعدة بيانات حقيقية زي SQLite أو MongoDB
users_db = {}
# مثال: {user_id: {"name": "Ahmed", "balance": 0.0, "links": 0, "joined": "2026-05-04"}}

# ========== LOGGING ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ========== SHRINKEARN API ==========
def shorten_link(url: str) -> str:
    """Shorten a URL using ShrinkEarn API"""
    try:
        response = requests.get(
            "https://shrinkearn.com/api",
            params={
                "api": SHRINKEARN_API,
                "url": url,
                "format": "json"
            },
            timeout=10
        )
        data = response.json()
        if data.get("status") == "success":
            return data.get("shortenedUrl", "")
        return ""
    except Exception as e:
        logging.error(f"ShrinkEarn API error: {e}")
        return ""

# ========== HELPERS ==========
def get_user(user_id: int, name: str = "") -> dict:
    """Get or create user"""
    if user_id not in users_db:
        users_db[user_id] = {
            "name": name,
            "balance": 0.0,
            "links": 0,
            "referrals": 0,
            "joined": "2026-05-04"
        }
    return users_db[user_id]

def add_earnings(user_id: int, amount: float):
    """Add earnings to user balance"""
    if user_id in users_db:
        users_db[user_id]["balance"] += amount

# ========== BOT COMMANDS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - welcome message"""
    user = update.effective_user
    get_user(user.id, user.first_name)

    keyboard = [
        [InlineKeyboardButton("🔗 Shorten Link", callback_data="shorten"),
         InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("💳 Payment Methods", callback_data="payments"),
         InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = f"""
🌟 *Welcome to Earn Easy Online!*

Hello {user.first_name}! 👋

💡 *How it works:*
1. Send any link to the bot
2. Get a shortened link
3. Share it with people
4. Earn money for every click!

💰 *Earnings per 1000 clicks:*
🇺🇸 USA/UK/Canada: up to $10
🌍 Middle East/Europe: up to $4
🌐 Other countries: up to $1

📌 Minimum withdrawal: ${MIN_WITHDRAWAL}

Choose an option below to get started:
    """

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def shorten_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user to send a link"""
    await update.message.reply_text(
        "🔗 *Send me any link to shorten it!*\n\nExample: https://youtube.com",
        parse_mode="Markdown"
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user balance"""
    user = update.effective_user
    data = get_user(user.id, user.first_name)
    balance = data["balance"]
    links = data["links"]

    text = f"""
💰 *Your Balance*

👤 Name: {user.first_name}
💵 Balance: ${balance:.2f}
🔗 Links shortened: {links}
📊 Min withdrawal: ${MIN_WITHDRAWAL}

{"✅ You can withdraw now!" if balance >= MIN_WITHDRAWAL else f"❌ Need ${MIN_WITHDRAWAL - balance:.2f} more to withdraw"}
    """
    await update.message.reply_text(text, parse_mode="Markdown")

async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Withdrawal request"""
    user = update.effective_user
    data = get_user(user.id, user.first_name)
    balance = data["balance"]

    if balance < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"❌ *Insufficient balance!*\n\n"
            f"Your balance: ${balance:.2f}\n"
            f"Minimum withdrawal: ${MIN_WITHDRAWAL}\n"
            f"You need: ${MIN_WITHDRAWAL - balance:.2f} more",
            parse_mode="Markdown"
        )
        return

    keyboard = [
        [InlineKeyboardButton("💚 USDT (TRC20)", callback_data="pay_usdt")],
        [InlineKeyboardButton("💜 Polygon (MATIC)", callback_data="pay_polygon")],
        [InlineKeyboardButton("❤️ Vodafone Cash", callback_data="pay_vodafone")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"💸 *Withdrawal Request*\n\n"
        f"Your balance: *${balance:.2f}*\n\n"
        f"Choose payment method:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot stats (admin only)"""
    user = update.effective_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return

    total_users = len(users_db)
    total_balance = sum(u["balance"] for u in users_db.values())
    total_links = sum(u["links"] for u in users_db.values())

    text = f"""
📊 *Bot Statistics*

👥 Total users: {total_users}
🔗 Total links: {total_links}
💰 Total earnings: ${total_balance:.2f}
    """
    await update.message.reply_text(text, parse_mode="Markdown")

# ========== HANDLE LINKS ==========

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any message - if it's a URL, shorten it"""
    user = update.effective_user
    text = update.message.text.strip()

    # Check if message is a URL
    if text.startswith("http://") or text.startswith("https://"):
        await update.message.reply_text("⏳ Shortening your link...")

        short_url = shorten_link(text)

        if short_url:
            # Update user stats
            data = get_user(user.id, user.first_name)
            data["links"] += 1

            await update.message.reply_text(
                f"✅ *Link shortened successfully!*\n\n"
                f"🔗 Your short link:\n`{short_url}`\n\n"
                f"💡 Share this link and earn money for every click!\n"
                f"💰 Earnings depend on visitor's country",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ Failed to shorten link. Please try again!"
            )
    else:
        await update.message.reply_text(
            "📌 Send me a valid URL starting with http:// or https://\n\n"
            "Example: https://youtube.com"
        )

# ========== CALLBACK HANDLERS ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard buttons"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = get_user(user.id, user.first_name)

    if query.data == "balance":
        balance = data["balance"]
        links = data["links"]
        text = (
            f"💰 *Your Balance*\n\n"
            f"💵 Balance: ${balance:.2f}\n"
            f"🔗 Links shortened: {links}\n"
            f"📊 Min withdrawal: ${MIN_WITHDRAWAL}\n\n"
            f"{'✅ You can withdraw now!' if balance >= MIN_WITHDRAWAL else f'❌ Need ${MIN_WITHDRAWAL - balance:.2f} more'}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == "shorten":
        await query.edit_message_text(
            "🔗 *Send me any link to shorten!*\n\nExample: https://youtube.com",
            parse_mode="Markdown"
        )

    elif query.data == "withdraw":
        balance = data["balance"]
        if balance < MIN_WITHDRAWAL:
            await query.edit_message_text(
                f"❌ *Insufficient balance!*\n\n"
                f"Balance: ${balance:.2f}\n"
                f"Need: ${MIN_WITHDRAWAL - balance:.2f} more",
                parse_mode="Markdown"
            )
        else:
            keyboard = [
                [InlineKeyboardButton("💚 USDT (TRC20)", callback_data="pay_usdt")],
                [InlineKeyboardButton("💜 Polygon (MATIC)", callback_data="pay_polygon")],
                [InlineKeyboardButton("❤️ Vodafone Cash", callback_data="pay_vodafone")],
            ]
            await query.edit_message_text(
                f"💸 *Choose payment method:*\n\nBalance: ${balance:.2f}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data == "payments":
        text = (
            "💳 *Payment Methods*\n\n"
            "💚 *USDT TRC20* - Tether stablecoin\n"
            "💜 *Polygon (MATIC)* - Low fees\n"
            "❤️ *Vodafone Cash* - Egypt only\n\n"
            f"📌 Minimum withdrawal: ${MIN_WITHDRAWAL}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == "stats":
        text = (
            f"📊 *Your Stats*\n\n"
            f"💵 Balance: ${data['balance']:.2f}\n"
            f"🔗 Links: {data['links']}\n"
            f"👥 Referrals: {data['referrals']}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == "help":
        text = (
            "❓ *How to use Earn Easy Online:*\n\n"
            "1️⃣ Send any link to the bot\n"
            "2️⃣ Get a shortened link\n"
            "3️⃣ Share it anywhere\n"
            "4️⃣ Earn money per click!\n\n"
            "💰 *Earning rates:*\n"
            f"🇺🇸 Tier 1: ${TIER1_RATE:.3f}/click\n"
            f"🌍 Tier 2: ${TIER2_RATE:.3f}/click\n"
            f"🌐 Tier 3: ${TIER3_RATE:.3f}/click\n\n"
            f"📌 Min withdrawal: ${MIN_WITHDRAWAL}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data in ["pay_usdt", "pay_polygon", "pay_vodafone"]:
        methods = {
            "pay_usdt": "💚 USDT TRC20\n\nSend your USDT wallet address:",
            "pay_polygon": "💜 Polygon (MATIC)\n\nSend your Polygon wallet address:",
            "pay_vodafone": "❤️ Vodafone Cash\n\nSend your Egyptian phone number:"
        }
        await query.edit_message_text(
            f"💸 *{methods[query.data]}*",
            parse_mode="Markdown"
        )

# ========== MAIN ==========

def main():
    """Run the bot"""
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("shorten", shorten_command))
    app.add_handler(CommandHandler("withdraw", withdraw_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # Buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # Messages (links)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Earn Easy Online Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
