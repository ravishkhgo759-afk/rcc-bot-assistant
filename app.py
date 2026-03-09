from flask import Flask, request
import requests
import math
from PIL import Image, ImageDraw

TOKEN = "8510228134:AAE4u90gkmAx-K72f7FzodPzkZJgfaGjRJY"

app = Flask(__name__)
user_data = {}
 
 # ---------------- IMAGE GENERATOR ----------------

def create_beam_diagram(result_text,b,d,d_dash,Ast,Asc,fck,fy):

    img = Image.new("RGB",(900,550),"white")
    draw = ImageDraw.Draw(img)

    # Result text
    y = 20
    for line in result_text.split("\n"):
        draw.text((30,y),line,fill="black")
        y += 30

    # Beam coordinates
    x1 = 420
    y1 = 140
    x2 = 780
    y2 = 420

    # 3D beam
    draw.rectangle((x1+10,y1+10,x2+10,y2+10),fill="#cfcfcf")
    draw.rectangle((x1,y1,x2,y2),outline="black",width=3,fill="#eeeeee")

    # Stirrup
    draw.rectangle((x1+20,y1+20,x2-20,y2-20),outline="green",width=3)

    # Compression steel
    if Asc > 0:
        draw.ellipse((x1+120,y1+25,x1+140,y1+45),fill="blue")
        draw.ellipse((x2-140,y1+25,x2-120,y1+45),fill="blue")
        draw.text((x1+80,y1-30),"Compression Steel",fill="blue")
        draw.text((x1+80,y1-10),"Asc = "+str(Asc)+" mm2",fill="blue")

    # Tension steel
    bar_y = y2-35
    bars = [80,150,220,290]

    for pos in bars:
        draw.ellipse((x1+pos,bar_y,x1+pos+20,bar_y+20),fill="red")

    draw.text((x1+110,y2+10),"Tension Steel",fill="red")
    draw.text((x1+110,y2+30),"Ast = "+str(Ast)+" mm2",fill="red")

    # Width dimension
    draw.line((x1,y2+60,x2,y2+60),fill="black",width=2)
    draw.text((x1+120,y2+70),"b = "+str(b)+" mm",fill="black")

    # Depth dimension
    draw.line((x2+60,y1,x2+60,y2),fill="black",width=2)
    draw.text((x2+70,(y1+y2)/2),"d = "+str(d)+" mm",fill="black")

    # Cover d'
    draw.line((x2+120,y1,x2+120,y1+d_dash),fill="black",width=2)
    draw.text((x2+130,y1+10),"d' = "+str(d_dash)+" mm",fill="black")

    # Material properties
    draw.text((x1+100,y1+100),"fck = "+str(fck)+" MPa",fill="black")
    draw.text((x1+100,y1+130),"fy = "+str(fy)+" MPa",fill="black")

    path = "result.png"
    img.save(path)

    return path
# ---------------- RCC FUNCTIONS ----------------

def get_fsc_interpolated(strain_sc, fy):

    if fy == 250:
        return 0.87 * fy

    tables = {
        415: [
            (0.00144, 288.7),
            (0.00163, 306.7),
            (0.00192, 324.8),
            (0.00241, 342.8),
            (0.00276, 351.8),
            (0.00380, 360.9)
        ],
        500: [
            (0.00174, 347.8),
            (0.00195, 369.6),
            (0.00226, 391.3),
            (0.00277, 413.0),
            (0.00312, 423.9),
            (0.00417, 434.8)
        ]
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
        x1, y1 = data[i+1]
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


def analyze_doubly_reinforced(b, d, d_dash, Ast, Asc, fck, fy):

    if fy == 250:
        km = 0.53
    elif fy == 415:
        km = 0.48
    else:
        km = 0.46

    xu_max = km * d
    fcc = 0.446 * fck

    fsc_assumed = 0.87 * fy
    xu = xu_max

    for _ in range(50):

        if xu == 0:
            break

        strain_sc = 0.0035 * (1 - (d_dash / xu))
        if strain_sc < 0:
            strain_sc = 0

        fsc_calc = get_fsc_interpolated(strain_sc, fy)

        if abs(fsc_calc - fsc_assumed) <= 0.5:
            fsc_final = fsc_calc
            break

        fsc_assumed = (fsc_assumed + fsc_calc) / 2

        num = 0.87 * fy * Ast - (fsc_assumed - fcc) * Asc
        den = 0.36 * fck * b

        if den == 0:
            break

        xu = num / den

    else:
        fsc_final = fsc_calc

    if xu > xu_max:
        section = "Over-Reinforced (Limiting)"
        xu = xu_max
        strain_sc = 0.0035 * (1 - (d_dash / xu))
        fsc_final = get_fsc_interpolated(strain_sc, fy)
    else:
        section = "Under-Reinforced / Balanced"

    Mu1 = 0.36 * fck * b * xu * (d - 0.42 * xu)
    Mu2 = (fsc_final - fcc) * Asc * (d - d_dash)

    return section, round(xu, 2), round(fsc_final, 2), round((Mu1 + Mu2) / 10**6, 2)


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

    if d_provided < 100:
        d_provided = 100

    term = 1 - (4.6 * Mu) / (fck * b * d_provided**2)

    if term < 0:
        return "Doubly Reinforced Required", d_provided, 0

    Ast = (0.5 * fck / fy) * (1 - math.sqrt(term)) * b * d_provided

    Ast_min = (0.85 * b * d_provided) / fy
    if Ast < Ast_min:
        Ast = Ast_min

    return "Singly Reinforced", d_provided, round(Ast)


# ---------------- NEW FUNCTIONS ----------------

def design_doubly_reinforced(Mu_kNm,b,d,d_dash,fck,fy):

    Mu = Mu_kNm*10**6

    if fy == 250:
        km = 0.53
    elif fy == 415:
        km = 0.48
    else:
        km = 0.46

    xu_max = km*d

    Mulim = 0.36*fck*b*xu_max*(d-0.42*xu_max)

    if Mu <= Mulim:

        Ast = Mu/(0.87*fy*d)
        Asc = 0

    else:

        Ast1 = Mulim/(0.87*fy*d)

        Mu2 = Mu-Mulim

        Asc = Mu2/(0.87*fy*(d-d_dash))

        Ast = Ast1 + Asc

    return round(Ast,2),round(Asc,2)


def design_shear(Vu_kN,b,d,fck):

    Vu = Vu_kN*1000

    tau_v = Vu/(b*d)

    tau_c = 0.62*math.sqrt(fck)

    if tau_v <= tau_c:

        stirrup = "Minimum Shear Reinforcement"
        spacing = 0.75*d

    else:

        stirrup = "Shear Reinforcement Required"
        spacing = 0.5*d

    return round(tau_v,3),stirrup,round(spacing,2)


# ---------------- WEBHOOK LOGIC ----------------

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json()

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    if chat_id not in user_data:
        user_data[chat_id] = {"step": 0}

    step = user_data[chat_id]["step"]

    try:

        if text == "/start":
            user_data[chat_id]["step"] = 1
            reply = (
                "RCC ENGINEERING BOT\n\n"
                "1. Analyze Singly Beam\n"
                "2. Analyze Doubly Beam\n"
                "3. Design Singly Beam\n"
                "4. Design Doubly Beam\n"
                "5. Design Beam for Shear\n\n"
                "Reply with 1 / 2 / 3 / 4 / 5"
            )

        elif step == 1:

            if text == "1":
                user_data[chat_id] = {"step": 2, "module": "singly"}
                reply = "Enter b, d, Ast, fck, fy"

            elif text == "2":
                user_data[chat_id] = {"step": 2, "module": "doubly"}
                reply = "Enter b, d, d', Ast, Asc, fck, fy"

            elif text == "3":
                user_data[chat_id] = {"step": 2, "module": "design"}
                reply = "Enter Mu(kNm), b, fck, fy"

            elif text == "4":
                user_data[chat_id] = {"step": 2, "module": "doubly_design"}
                reply = "Enter Mu(kNm), b, d, d', fck, fy"

            elif text == "5":
                user_data[chat_id] = {"step": 2, "module": "shear"}
                reply = "Enter Vu(kN), b, d, fck"

            else:
                reply = "Reply 1 / 2 / 3 / 4 / 5"


        elif user_data[chat_id]["module"] == "singly":

            params = [float(x.strip()) for x in text.split(",")]
            section, xu, Mu = analyze_singly_reinforced(*params)

            result = f"Type: {section}\nxu: {xu} mm\nMu: {Mu} kNm"

            img = create_result_image(result)

            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": chat_id, "caption": result},
                files={"photo": open(img,"rb")}
            )

            user_data[chat_id] = {"step": 0}
            return "ok"


        elif user_data[chat_id]["module"] == "doubly":

            params = [float(x.strip()) for x in text.split(",")]
            section, xu, fsc, Mu = analyze_doubly_reinforced(*params)

            result = f"Type: {section}\nxu: {xu} mm\nfsc: {fsc}\nMu: {Mu} kNm"
img = create_beam_diagram(result,*params)

            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": chat_id, "caption": result},
                files={"photo": open(img,"rb")}
            )

            user_data[chat_id] = {"step": 0}
            return "ok"


        elif user_data[chat_id]["module"] == "design":

            params = [float(x.strip()) for x in text.split(",")]
            result_type, d_prov, Ast_req = design_singly_reinforced(*params)

            if result_type == "Doubly Reinforced Required":
                result = f"Too small section.\nMin depth: {d_prov} mm"
            else:
                result = f"d_required: {d_prov} mm\nAst_required: {Ast_req} mm²"

            img = create_result_image(result)

            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": chat_id, "caption": result},
                files={"photo": open(img,"rb")}
            )

            user_data[chat_id] = {"step": 0}
            return "ok"


        elif user_data[chat_id]["module"] == "doubly_design":

            params = [float(x.strip()) for x in text.split(",")]
            Ast, Asc = design_doubly_reinforced(*params)

            result = f"Ast tension: {Ast} mm2\nAsc compression: {Asc} mm2"

            img = create_result_image(result)

            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": chat_id, "caption": result},
                files={"photo": open(img,"rb")}
            )

            user_data[chat_id] = {"step": 0}
            return "ok"


        elif user_data[chat_id]["module"] == "shear":

            params = [float(x.strip()) for x in text.split(",")]
            tau_v, stirrup, spacing = design_shear(*params)

            result = f"tau_v: {tau_v}\n{stirrup}\nSpacing: {spacing} mm"

            img = create_result_image(result)

            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={"chat_id": chat_id, "caption": result},
                files={"photo": open(img,"rb")}
            )

            user_data[chat_id] = {"step": 0}
            return "ok"


        else:
            reply = "Type /start"

    except:
        reply = "Invalid Input. Follow correct format."
        user_data[chat_id] = {"step": 0}

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": reply}
    )

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
