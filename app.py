import os
import math
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# --- TOKEN from Environment Variable ---
TOKEN = os.getenv("8510228134:AAE4u90gkmAx-K72f7FzodPzkZJgfaGjRJY")

if not TOKEN:
    raise ValueError("No TOKEN found. Set TOKEN as environment variable.")

# --- Conversation States ---
CHOOSING, ANALYZING_SINGLY, ANALYZING_DOUBLY, DESIGNING_SINGLY = range(4)

# --- RCC FUNCTIONS ---

def get_fsc_interpolated(strain_sc, fy):
    if fy == 250:
        return 0.87 * fy

    tables = {
        415: [(0.00144, 288.7), (0.00163, 306.7), (0.00192, 324.8),
              (0.00241, 342.8), (0.00276, 351.8), (0.00380, 360.9)],
        500: [(0.00174, 347.8), (0.00195, 369.6), (0.00226, 391.3),
              (0.00277, 413.0), (0.00312, 423.9), (0.00417, 434.8)]
    }

    if fy not in tables:
        return 0.87 * fy

    data = tables[fy]

    if strain_sc < data[0][0]:
        return strain_sc * 2 * 10**5

    if strain_sc >= data[-1][0]:
        return data[-1][1]

    for i in range(len(data) - 1):
        x0, y0 = data[i]
        x1, y1 = data[i + 1]
        if x0 <= strain_sc < x1:
            return y0 + (strain_sc - x0) * (y1 - y0) / (x1 - x0)

    return 0.87 * fy


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
        section = "Over-Reinforced (Limited to xu_max)"
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
        return "Doubly Reinforced Required", d_provided, 0

    Ast = (0.5 * fck / fy) * (1 - math.sqrt(term)) * b * d_provided

    Ast_min = (0.85 * b * d_provided) / fy
    if Ast < Ast_min:
        Ast = Ast_min

    return "Singly Reinforced", d_provided, round(Ast)


# --- BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Analyze Singly Beam"],
        ["Design Singly Beam"]
    ]
    await update.message.reply_text(
        "Civil Engineering RCC Bot\nSelect module:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return CHOOSING


async def ask_analyze_singly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter: b, d, Ast, fck, fy\nExample:\n230, 450, 942, 20, 415",
        reply_markup=ReplyKeyboardRemove()
    )
    return ANALYZING_SINGLY


async def perform_analyze_singly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        params = [float(x.strip()) for x in update.message.text.split(',')]
        section, xu, Mu = analyze_singly_reinforced(*params)
        await update.message.reply_text(
            f"Type: {section}\n"
            f"xu: {xu} mm\n"
            f"Mu: {Mu} kNm"
        )
    except:
        await update.message.reply_text("Invalid format.")
    return ConversationHandler.END


async def ask_design_singly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Enter: Mu(kNm), b(mm), fck, fy\nExample:\n150, 230, 20, 415",
        reply_markup=ReplyKeyboardRemove()
    )
    return DESIGNING_SINGLY


async def perform_design_singly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        params = [float(x.strip()) for x in update.message.text.split(',')]
        result_type, d_prov, Ast_req = design_singly_reinforced(*params)

        if result_type == "Doubly Reinforced Required":
            msg = f"Section too small.\nRequired Depth: {d_prov} mm"
        else:
            bars = math.ceil(Ast_req / 201)
            msg = (
                f"Effective Depth: {d_prov} mm\n"
                f"Total Depth ≈ {d_prov + 30} mm\n"
                f"Ast Required: {Ast_req} mm²\n"
                f"Provide {bars} bars of 16mm"
            )

        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("Invalid format.")
        return DESIGNING_SINGLY

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. Type /start")
    return ConversationHandler.END


async def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                MessageHandler(filters.Regex("^Analyze Singly Beam$"), ask_analyze_singly),
                MessageHandler(filters.Regex("^Design Singly Beam$"), ask_design_singly),
            ],
            ANALYZING_SINGLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, perform_analyze_singly)
            ],
            DESIGNING_SINGLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, perform_design_singly)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("Bot Running...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
