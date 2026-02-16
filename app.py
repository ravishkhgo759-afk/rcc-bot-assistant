import math
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# 🔴 YOUR TOKEN ADDED
TOKEN = "8510228134:AAF1aCVc_RolYFFRLeKTtc3-AaUFeewebbo"

CHOOSING, ANALYZING_SINGLY, DESIGNING_SINGLY = range(3)

# ---------------- RCC FUNCTIONS ---------------- #

def analyze_singly_reinforced(b, d, Ast, fck, fy):
    xu = (0.87 * fy * Ast) / (0.36 * fck * b)

    if fy == 250:
        km = 0.53
    elif fy == 415:
        km = 0.48
    else:
        km = 0.46

    xu_max = km * d

    if xu <= xu_max:
        section = "Under-Reinforced"
        term = (Ast * fy) / (b * d * fck)
        Mu = 0.87 * fy * Ast * d * (1 - term)
    else:
        section = "Over-Reinforced"
        Mu = 0.36 * fck * b * xu_max * (d - 0.42 * xu_max)

    return section, round(xu, 2), round(Mu / 10**6, 2)


def design_singly_reinforced(Mu_kNm, b, fck, fy):
    Mu = Mu_kNm * 10**6

    if fy == 250:
        Q_lim = 0.148 * fck
    elif fy == 415:
        Q_lim = 0.138 * fck
    else:
        Q_lim = 0.133 * fck

    d_req = math.sqrt(Mu / (Q_lim * b))
    d_provided = math.ceil(d_req / 10) * 10

    term = 1 - (4.6 * Mu) / (fck * b * d_provided**2)
    if term < 0:
        return "Increase depth (Doubly Required)", d_provided, 0

    Ast = (0.5 * fck / fy) * (1 - math.sqrt(term)) * b * d_provided
    return "Singly Reinforced", d_provided, round(Ast)

# ---------------- BOT HANDLERS ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Analyze Singly Beam"],
        ["Design Singly Beam"]
    ]
    await update.message.reply_text(
        "RCC Engineering Bot\nSelect Option:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    return CHOOSING


async def ask_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter: b, d, Ast, fck, fy\nExample: 230, 450, 942, 20, 415",
        reply_markup=ReplyKeyboardRemove()
    )
    return ANALYZING_SINGLY


async def perform_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        params = [float(x.strip()) for x in update.message.text.split(",")]
        section, xu, Mu = analyze_singly_reinforced(*params)
        await update.message.reply_text(
            f"Type: {section}\nxu: {xu} mm\nMoment: {Mu} kNm"
        )
    except:
        await update.message.reply_text("Invalid format.")
    return ConversationHandler.END


async def ask_design(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter: Mu(kNm), b, fck, fy\nExample: 150, 230, 20, 415",
        reply_markup=ReplyKeyboardRemove()
    )
    return DESIGNING_SINGLY


async def perform_design(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        params = [float(x.strip()) for x in update.message.text.split(",")]
        result, d, Ast = design_singly_reinforced(*params)
        await update.message.reply_text(
            f"Result: {result}\nEffective Depth: {d} mm\nSteel Required: {Ast} mm²"
        )
    except:
        await update.message.reply_text("Invalid format.")
    return ConversationHandler.END


def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                MessageHandler(filters.Regex("^Analyze Singly Beam$"), ask_analyze),
                MessageHandler(filters.Regex("^Design Singly Beam$"), ask_design),
            ],
            ANALYZING_SINGLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, perform_analyze)
            ],
            DESIGNING_SINGLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, perform_design)
            ],
        },
        fallbacks=[],
    )

    app.add_handler(conv)

    print("Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
