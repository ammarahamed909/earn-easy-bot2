import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8263620123:AAEslo1rbEeqCDCkxz1iX_21XzcugPvXhvE"
ADMIN_ID = 6766597560 # غير ده لـ ID بتاعك
MIN_WITHDRAWAL = 5.00  # الحد الأدنى للسحب
POINTS_PER_DOLLAR = 1000  # 1000 نقطة = $1

users_db = {}
# links_db: {link_id: {"url": "...", "title": "...", "points": 10}}
links_db = {}
link_counter = 1

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def get_user(user_id, name=""):
    if user_id not in users_db:
        users_db[user_id] = {"name": name, "points": 0, "withdrawn": 0.0, "joined": True}
    return users_db[user_id]

def points_to_dollars(points):
    return points / POINTS_PER_DOLLAR

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 روابط متاحة", callback_data="browse_links"),
         InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("💸 سحب", callback_data="withdraw"),
         InlineKeyboardButton("❓ مساعدة", callback_data="help")]
    ])

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.first_name)
    await update.message.reply_text(
        f"🌟 *أهلاً {user.first_name}!*\n\n"
        "💡 *كيف تكسب؟*\n"
        "1️⃣ اضغط على رابط\n"
        "2️⃣ شاهد الإعلان وانتظر\n"
        "3️⃣ اضغط تخطي\n"
        "4️⃣ تكسب نقاط!\n\n"
        f"💰 *1000 نقطة = $1*\n"
        f"📌 الحد الأدنى للسحب: ${MIN_WITHDRAWAL}",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ========== BROWSE LINKS ==========
async def browse_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not links_db:
        await query.edit_message_text(
            "😔 مفيش روابط متاحة دلوقتي!\nرجع تاني بعد شوية.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])
        )
        return

    keyboard = []
    for lid, link in links_db.items():
        keyboard.append([InlineKeyboardButton(
            f"🔗 {link['title']} (+{link['points']} نقطة)",
            callback_data=f"link_{lid}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])

    await query.edit_message_text(
        "🎯 *الروابط المتاحة:*\n\nاضغط على أي رابط واحصل على نقاط!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== CLICK LINK ==========
async def click_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = get_user(user.id, user.first_name)

    lid = int(query.data.split("_")[1])
    if lid not in links_db:
        await query.edit_message_text("❌ الرابط مش موجود!")
        return

    link = links_db[lid]
    points = link["points"]

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 فتح الرابط", url=link["url"])],
        [InlineKeyboardButton(f"✅ تخطي (+{points} نقطة)", callback_data=f"skip_{lid}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="browse_links")]
    ])

    await query.edit_message_text(
        f"🔗 *{link['title']}*\n\n"
        f"1️⃣ اضغط 'فتح الرابط'\n"
        f"2️⃣ انتظر الإعلان\n"
        f"3️⃣ اضغط 'تخطي' لتحصل على *{points} نقطة*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# ========== SKIP LINK (earn points) ==========
async def skip_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = get_user(user.id, user.first_name)

    lid = int(query.data.split("_")[1])
    if lid not in links_db:
        await query.edit_message_text("❌ الرابط مش موجود!")
        return

    points = links_db[lid]["points"]
    data["points"] += points
    total = data["points"]
    dollars = points_to_dollars(total)

    await query.edit_message_text(
        f"✅ *تم! كسبت {points} نقطة!*\n\n"
        f"📊 رصيدك الكلي: *{total} نقطة*\n"
        f"💵 = ${dollars:.2f}\n\n"
        f"{'✅ يمكنك السحب الآن!' if dollars >= MIN_WITHDRAWAL else f'تحتاج {POINTS_PER_DOLLAR * MIN_WITHDRAWAL - total:.0f} نقطة للسحب'}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 روابط أكثر", callback_data="browse_links")],
            [InlineKeyboardButton("💰 رصيدي", callback_data="balance")]
        ])
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

    methods = {
        "pay_usdt": "USDT TRC20",
        "pay_polygon": "Polygon (MATIC)",
        "pay_vodafone": "فودافون كاش"
    }
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
        await handle_admin_command(update, context)
        return

    method = context.user_data["withdraw_method"]
    amount = context.user_data["withdraw_amount"]
    wallet = update.message.text

    # Send to admin
    if ADMIN_ID != 0:
        await context.bot.send_message(
            ADMIN_ID,
            f"💸 *طلب سحب جديد!*\n\n"
            f"👤 المستخدم: {user.first_name}\n"
            f"🆔 ID: {user.id}\n"
            f"💵 المبلغ: ${amount:.2f}\n"
            f"💳 الطريقة: {method}\n"
            f"🏦 المحفظة: {wallet}",
            parse_mode="Markdown"
        )

    # Deduct points
    data = get_user(user.id, user.first_name)
    data["points"] = 0
    context.user_data.clear()

    await update.message.reply_text(
        f"✅ *تم إرسال طلب السحب!*\n\n"
        f"💵 المبلغ: ${amount:.2f}\n"
        f"💳 الطريقة: {method}\n"
        f"🏦 المحفظة: {wallet}\n\n"
        f"⏳ سيتم المراجعة والتحويل خلال 24 ساعة.",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ========== ADMIN COMMANDS ==========
async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # Not admin
    if user.id != ADMIN_ID and ADMIN_ID != 0:
        await update.message.reply_text("📌 ابعت رابط يبدأ بـ https://")
        return

    await update.message.reply_text(
        "⚙️ *أوامر الأدمن:*\n\n"
        "/addlink - إضافة رابط جديد\n"
        "/links - عرض كل الروابط\n"
        "/users - عرض المستخدمين\n"
        "/dellink [id] - حذف رابط",
        parse_mode="Markdown"
    )

async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global link_counter
    user = update.effective_user

    if user.id != ADMIN_ID and ADMIN_ID != 0:
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ الاستخدام:\n/addlink [رابط] [نقاط] [العنوان]\n\n"
            "مثال:\n/addlink https://example.com 50 موقع رائع"
        )
        return

    url = args[0]
    points = int(args[1])
    title = " ".join(args[2:])

    links_db[link_counter] = {"url": url, "title": title, "points": points}
    link_counter += 1

    await update.message.reply_text(
        f"✅ *تم إضافة الرابط!*\n\n"
        f"🔗 {title}\n"
        f"⭐ النقاط: {points}\n"
        f"🆔 ID: {link_counter - 1}",
        parse_mode="Markdown"
    )

async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID and ADMIN_ID != 0:
        return

    if not links_db:
        await update.message.reply_text("مفيش روابط!")
        return

    text = "🔗 *الروابط الحالية:*\n\n"
    for lid, link in links_db.items():
        text += f"ID: {lid} | {link['title']} | {link['points']} نقطة\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID and ADMIN_ID != 0:
        return

    if not users_db:
        await update.message.reply_text("مفيش مستخدمين!")
        return

    text = "👥 *المستخدمين:*\n\n"
    for uid, udata in users_db.items():
        dollars = points_to_dollars(udata["points"])
        text += f"👤 {udata['name']} | ID: {uid} | {udata['points']} نقطة (${dollars:.2f})\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def del_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID and ADMIN_ID != 0:
        return

    args = context.args
    if not args:
        await update.message.reply_text("❌ /dellink [id]")
        return

    lid = int(args[0])
    if lid in links_db:
        del links_db[lid]
        await update.message.reply_text(f"✅ تم حذف الرابط {lid}")
    else:
        await update.message.reply_text("❌ الرابط مش موجود!")

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
    app.add_handler(CommandHandler("addlink", add_link))
    app.add_handler(CommandHandler("links", list_links))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("dellink", del_link))
    app.add_handler(CallbackQueryHandler(browse_links, pattern="^browse_links$"))
    app.add_handler(CallbackQueryHandler(click_link, pattern="^link_"))
    app.add_handler(CallbackQueryHandler(skip_link, pattern="^skip_"))
    app.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(pay_method, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))
    print("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

