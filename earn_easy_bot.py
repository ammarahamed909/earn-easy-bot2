import logging
import requests
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8263620123:AAEslo1rbEeqCDCkxz1iX_21XzcugPvXhvE"
SHRINKEARN_API = "a92843ecf51915018be63e04fd74664724a935e5"
BOT_USERNAME = "EarnEasyOnlineBot"  # غير ده لـ username البوت بتاعك
ADMIN_ID = 6766597560
MIN_WITHDRAWAL = 5.00
POINTS_PER_DOLLAR = 1000

users_db = {}
# tokens_db: {token: user_id} عشان نعرف مين جه من الرابط
tokens_db = {}
# user_tokens: {user_id: {"token": "...", "short_url": "...", "clicks": 0}}
user_tokens = {}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def get_user(user_id, name=""):
    if user_id not in users_db:
        users_db[user_id] = {"name": name, "points": 0, "withdrawn": 0.0}
    return users_db[user_id]

def points_to_dollars(points):
    return points / POINTS_PER_DOLLAR

def shorten_link(url, alias=""):
    try:
        params = {"api": SHRINKEARN_API, "url": url, "format": "json"}
        if alias:
            params["alias"] = alias
        r = requests.get("https://shrinkearn.com/api", params=params, timeout=15)
        data = r.json()
        if data.get("status") == "success":
            return data.get("shortenedUrl", "").replace("\\/", "/")
    except Exception as e:
        logging.error(f"ShrinkEarn error: {e}")
    return ""

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 رابطي الخاص", callback_data="my_link"),
         InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("💸 سحب", callback_data="withdraw"),
         InlineKeyboardButton("📊 إحصائياتي", callback_data="mystats")],
        [InlineKeyboardButton("❓ مساعدة", callback_data="help")]
    ])

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.first_name)

    # لو جه من رابط مختصر
    if context.args and context.args[0].startswith("reward_"):
        parts = context.args[0].split("_")
        if len(parts) == 3:
            token = parts[2]
            referrer_id = int(parts[1])

            # تأكد إن مش نفس الشخص
            if referrer_id != user.id and token in tokens_db:
                # احسب النقاط
                referrer_data = get_user(referrer_id)
                referrer_data["points"] += 10  # 10 نقاط لكل كليك حقيقي

                # سجل الكليك
                if referrer_id in user_tokens:
                    user_tokens[referrer_id]["clicks"] += 1

                # ابعت إشعار لصاحب الرابط
                try:
                    await context.bot.send_message(
                        referrer_id,
                        f"🎉 *حد ضغط على رابطك!*\n\n+10 نقاط تم إضافتها لرصيدك!",
                        parse_mode="Markdown"
                    )
                except:
                    pass

                await update.message.reply_text(
                    f"✅ *أهلاً {user.first_name}!*\n\nلقد وصلت عبر رابط مميز!\nابدأ وأنشئ رابطك الخاص واكسب أنت كمان! 🚀",
                    parse_mode="Markdown",
                    reply_markup=main_menu()
                )
                return

    await update.message.reply_text(
        f"🌟 *أهلاً {user.first_name} في Earn Easy Online!*\n\n"
        "💡 *كيف تكسب؟*\n"
        "1️⃣ اضغط 'رابطي الخاص'\n"
        "2️⃣ شارك الرابط المختصر مع الناس\n"
        "3️⃣ لما حد يضغط عليه ويفتح البوت تكسب نقاط!\n\n"
        "💰 *1000 نقطة = $1*\n"
        f"📌 الحد الأدنى للسحب: ${MIN_WITHDRAWAL}",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ========== MY LINK ==========
async def my_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    get_user(user.id, user.first_name)

    # لو عنده رابط قديم
    if user.id in user_tokens:
        info = user_tokens[user.id]
        await query.edit_message_text(
            f"🔗 *رابطك الخاص:*\n\n`{info['short_url']}`\n\n"
            f"📊 عدد الكليكات: *{info['clicks']}*\n"
            f"💰 نقاطك من الرابط: *{info['clicks'] * 10}*\n\n"
            "شارك الرابط ده مع أصحابك وأكسب نقاط على كل كليك!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تجديد الرابط", callback_data="renew_link")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
            ])
        )
        return

    await query.edit_message_text(
        "⏳ جاري إنشاء رابطك الخاص...",
    )

    # توليد token فريد
    token = secrets.token_hex(8)
    reward_url = f"https://t.me/{BOT_USERNAME}?start=reward_{user.id}_{token}"

    # اختصار الرابط عبر ShrinkEarn
    short_url = shorten_link(reward_url)

    if not short_url:
        await query.edit_message_text(
            "❌ حدث خطأ! حاول تاني.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])
        )
        return

    # حفظ التوكن
    tokens_db[token] = user.id
    user_tokens[user.id] = {"token": token, "short_url": short_url, "clicks": 0}

    await query.edit_message_text(
        f"✅ *تم إنشاء رابطك الخاص!*\n\n"
        f"🔗 رابطك:\n`{short_url}`\n\n"
        "📢 شارك الرابط ده مع أصحابك!\n"
        "💰 هتكسب *10 نقاط* على كل شخص يفتح الرابط!\n\n"
        "⚡ الناس هتشوف إعلان الأول وبعدين يوصلوا للبوت!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 إحصائياتي", callback_data="mystats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
        ])
    )

# ========== RENEW LINK ==========
async def renew_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    await query.edit_message_text("⏳ جاري تجديد رابطك...")

    token = secrets.token_hex(8)
    reward_url = f"https://t.me/{BOT_USERNAME}?start=reward_{user.id}_{token}"
    short_url = shorten_link(reward_url)

    if not short_url:
        await query.edit_message_text("❌ حدث خطأ! حاول تاني.")
        return

    old_clicks = user_tokens.get(user.id, {}).get("clicks", 0)
    tokens_db[token] = user.id
    user_tokens[user.id] = {"token": token, "short_url": short_url, "clicks": old_clicks}

    await query.edit_message_text(
        f"✅ *تم تجديد رابطك!*\n\n`{short_url}`\n\nشاركه مع أصحابك! 🚀",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])
    )

# ========== BALANCE ==========
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = get_user(user.id, user.first_name)
    points = data["points"]
    dollars = points_to_dollars(points)

    await query.edit_message_text(
        f"💰 *رصيدك*\n\n"
        f"⭐ النقاط: *{points}*\n"
        f"💵 بالدولار: *${dollars:.2f}*\n"
        f"📌 الحد الأدنى: ${MIN_WITHDRAWAL}\n\n"
        f"{'✅ يمكنك السحب!' if dollars >= MIN_WITHDRAWAL else f'❌ تحتاج ${MIN_WITHDRAWAL - dollars:.2f} أكثر'}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 سحب", callback_data="withdraw")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
        ])
    )

# ========== MY STATS ==========
async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = get_user(user.id, user.first_name)
    clicks = user_tokens.get(user.id, {}).get("clicks", 0)

    await query.edit_message_text(
        f"📊 *إحصائياتك*\n\n"
        f"🔗 كليكات الرابط: *{clicks}*\n"
        f"⭐ إجمالي النقاط: *{data['points']}*\n"
        f"💵 بالدولار: *${points_to_dollars(data['points']):.2f}*\n"
        f"💸 تم سحبه: *${data['withdrawn']:.2f}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])
    )

# ========== WITHDRAW ==========
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = get_user(user.id, user.first_name)
    dollars = points_to_dollars(data["points"])

    if dollars < MIN_WITHDRAWAL:
        await query.edit_message_text(
            f"❌ رصيدك ${dollars:.2f}\nتحتاج ${MIN_WITHDRAWAL - dollars:.2f} أكثر للسحب",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])
        )
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💚 USDT TRC20", callback_data="pay_usdt")],
        [InlineKeyboardButton("💜 Polygon", callback_data="pay_polygon")],
        [InlineKeyboardButton("❤️ فودافون كاش", callback_data="pay_vodafone")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ])
    await query.edit_message_text(
        f"💸 *طلب سحب*\n\nرصيدك: *${dollars:.2f}*\n\nاختار طريقة الدفع:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def pay_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = get_user(user.id, user.first_name)
    dollars = points_to_dollars(data["points"])

    methods = {"pay_usdt": "USDT TRC20", "pay_polygon": "Polygon (MATIC)", "pay_vodafone": "فودافون كاش"}
    method = methods[query.data]
    context.user_data["withdraw_method"] = method
    context.user_data["withdraw_amount"] = dollars

    await query.edit_message_text(
        f"💸 *{method}*\n\nالمبلغ: ${dollars:.2f}\n\nابعت رقم المحفظة أو رقم الهاتف:",
        parse_mode="Markdown"
    )

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if "withdraw_method" not in context.user_data:
        await update.message.reply_text(
            "📌 استخدم الأزرار في القائمة!",
            reply_markup=main_menu()
        )
        return

    method = context.user_data["withdraw_method"]
    amount = context.user_data["withdraw_amount"]
    wallet = update.message.text

    if ADMIN_ID != 0:
        await context.bot.send_message(
            ADMIN_ID,
            f"💸 *طلب سحب جديد!*\n\n"
            f"👤 {user.first_name}\n"
            f"🆔 {user.id}\n"
            f"💵 ${amount:.2f}\n"
            f"💳 {method}\n"
            f"🏦 {wallet}",
            parse_mode="Markdown"
        )

    data = get_user(user.id, user.first_name)
    data["points"] = 0
    data["withdrawn"] += amount
    context.user_data.clear()

    await update.message.reply_text(
        f"✅ *تم إرسال طلب السحب!*\n\n"
        f"💵 ${amount:.2f} عبر {method}\n"
        f"⏳ سيتم التحويل خلال 24 ساعة.",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ========== ADMIN ==========
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not users_db:
        await update.message.reply_text("مفيش مستخدمين!")
        return
    text = "👥 *المستخدمين:*\n\n"
    for uid, udata in users_db.items():
        clicks = user_tokens.get(uid, {}).get("clicks", 0)
        dollars = points_to_dollars(udata["points"])
        text += f"👤 {udata['name']} | {udata['points']}⭐ (${dollars:.2f}) | {clicks} كليك\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "❓ *كيف يعمل البوت؟*\n\n"
        "1️⃣ اضغط 'رابطي الخاص'\n"
        "2️⃣ البوت هيعملك رابط مختصر فريد\n"
        "3️⃣ شارك الرابط مع أصحابك\n"
        "4️⃣ لما حد يضغط عليه هيشوف إعلان\n"
        "5️⃣ بعدين هيوصل للبوت وأنت تكسب 10 نقاط!\n\n"
        "💰 *1000 نقطة = $1*\n"
        f"📌 الحد الأدنى للسحب: ${MIN_WITHDRAWAL}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])
    )

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = get_user(user.id, user.first_name)
    await query.edit_message_text(
        f"🌟 *Earn Easy Online*\n\n⭐ نقاطك: {data['points']}\n💵 ${points_to_dollars(data['points']):.2f}",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CallbackQueryHandler(my_link, pattern="^my_link$"))
    app.add_handler(CallbackQueryHandler(renew_link, pattern="^renew_link$"))
    app.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(mystats, pattern="^mystats$"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(pay_method, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(help_cmd, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    print("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
