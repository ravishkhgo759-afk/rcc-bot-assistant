import os
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

TOKEN = os.getenv("8510228134:AAF1aCVc_RolYFFRLeKTtc3-AaUFeewebbo")

CHOOSING, ANALYZING_SINGLY, ANALYZING_DOUBLY, DESIGNING_SINGLY = range(4)

# ---------------- RCC FUNCTIONS ---------------- #

def analyze_singly_reinforced(b, d, Ast, fck, fy):
    xu = (0.87 * fy * Ast) / (0.36 * fck * b)

    if fy == 250: km = 0.53
    elif fy == 415: km = 0.48
    else: km = 0.46

    xu_max = km * d

    if xu <= xu_max:
        section = "Under-Reinforced"
        term = (Ast * fy) / (b * d * fck)
        Mu = 0.87 * fy * Ast * d * (1 - term)
    else:
        section = "Over-Reinforced"
        Mu = 0.36 * fck * b * xu_max * (d - 0.42 * xu_max)

    return section, round(xu, 2), round(Mu / 10**6, 2)

# ---------------- BOT HANDLERS ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Analyze Singly Beam"],
        ["Design Singly Beam"]
    ]
    await update.message.reply_text(
        "RCC Engineering Bot\nSelect Option:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return CHOOSING


async def ask_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter: b, d, Ast, fck, fy\nExample: 230,450,942,20,415",
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


def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                MessageHandler(filters.Regex("^Analyze Singly Beam$"), ask_analyze),
            ],
            ANALYZING_SINGLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, perform_analyze)
            ],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)

    print("Bot Running...")
    application.run_polling()


if __name__ == "__main__":
    main()
