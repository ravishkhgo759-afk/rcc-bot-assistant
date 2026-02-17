from flask import Flask, request
import requests
import math

TOKEN = "YOUR_NEW_TELEGRAM_TOKEN"

app = Flask(__name__)

# Temporary user storage
user_data = {}

# Conversation Steps
CHOOSING = 0
ANALYZE_SINGLY = 1
ANALYZE_DOUBLY = 2
DESIGN_SINGLY = 3


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
        Mu = 0.87 * fy * Ast * d * (1 - (Ast * fy) / (b * d * fck))
    else:
        section = "Over-Reinforced (Limited)"
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
    d_prov = math.ceil(d_req / 10) * 10

    term = 1 - (4.6 * Mu) / (fck * b * d_prov**2)
    if term < 0:
        return "Doubly Required", d_prov, 0

    Ast = (0.5 * fck / fy) * (1 - math.sqrt(term)) * b * d_prov
    return "Singly Reinforced", d_prov, round(Ast)


# ---------------- WEBHOOK ---------------- #

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    if chat_id not in user_data:
        user_data[chat_id] = {"step": CHOOSING}

    step = user_data[chat_id]["step"]

    try:

        if step == CHOOSING:
            user_data[chat_id]["step"] = CHOOSING
            reply = (
                "Select Option:\n"
                "1. Analyze Singly Beam\n"
                "2. Design Singly Beam\n\n"
                "Reply with 1 or 2"
            )

            if text == "1":
                user_data[chat_id]["step"] = ANALYZE_SINGLY
                reply = "Enter: b, d, Ast, fck, fy\nExample: 230,450,942,20,415"

            elif text == "2":
                user_data[chat_id]["step"] = DESIGN_SINGLY
                reply = "Enter: Mu(kNm), b, fck, fy\nExample: 150,230,20,415"

        elif step == ANALYZE_SINGLY:
            params = [float(x.strip()) for x in text.split(",")]
            section, xu, Mu = analyze_singly_reinforced(*params)

            reply = (
                f"--- RCC REPORT ---\n"
                f"Type: {section}\n"
                f"xu: {xu} mm\n"
                f"Mu: {Mu} kNm"
            )

            user_data[chat_id]["step"] = CHOOSING

        elif step == DESIGN_SINGLY:
            params = [float(x.strip()) for x in text.split(",")]
            result, d, Ast = design_singly_reinforced(*params)

            if result == "Doubly Required":
                reply = f"Section too small.\nMinimum Depth: {d} mm"
            else:
                reply = (
                    f"--- DESIGN RESULT ---\n"
                    f"Effective Depth: {d} mm\n"
                    f"Total Depth: {d+30} mm\n"
                    f"Steel Required: {Ast} mm²"
                )

            user_data[chat_id]["step"] = CHOOSING

        else:
            reply = "Type anything to start RCC calculation."
            user_data[chat_id]["step"] = CHOOSING

    except:
        reply = "Invalid Input. Use correct numeric format."
        user_data[chat_id]["step"] = CHOOSING

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": reply}
    )

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
