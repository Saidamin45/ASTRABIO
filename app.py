"""ASTRABIO - Flask backend with deterministic demo data and the "Nova" agent."""
import math, os
from checkin import SPEC, HAZ, LINK, checkin_state, item, log_value, reset as reset_checkin, voice_parse
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
TOTAL_DAYS, DEFAULT_DAY = 180, 142
ORDER = ["normal", "watch", "warning", "critical"]


def lvl(v, w, o, c, hb=True):
    if not hb:
        v, w, o, c = -v, -w, -o, -c
    return "critical" if v >= c else "warning" if v >= o else "watch" if v >= w else "normal"


def mk(label, f, unit, w, o, c, hb=True, dp=1, day=1):
    s = [round(f(d) + 0.02 * math.sin(d * 1.7) * abs(f(d)) * 0.1, dp) for d in range(max(1, day - 13), day + 1)]
    return dict(label=label, value=s[-1], unit=unit, series=s, level=lvl(s[-1], w, o, c, hb))


def markers(day):
    # id, name, pos, hazards, label, f(d), unit, w, o, c, higher_is_bad, explanation
    D = [
        ("brain", "Brain", (0, 1.74, .08), ["radiation", "mind"], "Brain dose", lambda d: 5 + .9 * d, "mSv", 100, 200, 300, True,
         "Cosmic rays pass through the skull. Dose is tracked closely and sleep quality helps the brain recover."),
        ("spine", "Spine", (0, 1.22, -.06), ["radiation", "gravity"], "Lower-spine bone density", lambda d: 100 - .06 * d, "% of baseline", 92, 88, 82, False,
         "Without gravity loading, bones slowly lose mineral. I'm seeing reduced bone density markers in your lower spine."),
        ("marrow", "Bone marrow", (.11, .93, .08), ["radiation"], "Marrow dose", lambda d: 3 + 1.2 * d, "mSv", 150, 250, 350, True,
         "Bone marrow makes blood cells and is sensitive to radiation, so we keep its dose well under the limit."),
        ("legs", "Legs", (.11, .62, .08), ["gravity"], "Leg muscle mass", lambda d: 100 - .1 * d, "% of baseline", 95, 88, 80, False,
         "Legs do less work in microgravity, so muscle shrinks without resistance exercise."),
        ("heart", "Heart", (.08, 1.4, .1), ["gravity"], "Resting heart rate", lambda d: 58 + .03 * d, "bpm", 65, 72, 85, True,
         "Fluids shift toward the head in space and the heart adapts. Your rate is within a healthy range."),
        ("gut", "Gut", (0, 1.06, .12), ["immune", "habitat"], "Microbiome diversity", lambda d: 4.2 - .008 * d, "index", 3.4, 2.8, 2.2, False,
         "Gut bacteria shift in a closed habitat, which can affect immunity. Diversity is dipping slightly."),
        ("skin", "Skin", (.2, 1.3, .1), ["immune", "habitat"], "Inflammation marker (CRP)", lambda d: 1 + .02 * d, "mg/L", 4, 6, 10, True,
         "Skin is the front line of immunity. Dry air and dust can raise inflammation a little."),
        ("eyes", "Eyes", (0, 1.77, .13), ["radiation", "gravity"], "Optic disc swelling", lambda d: 1.1 * d, "um", 160, 200, 300, True,
         "Head-ward fluid shift can swell the back of the eye and blur near vision. Worth watching."),
    ]
    out = []
    for i, name, pos, hz, label, f, unit, w, o, c, hb, text in D:
        m = mk(label, f, unit, w, o, c, hb, 2 if unit == "index" else 1, day)
        out.append(dict(id=i, name=name, pos=pos, hazards=hz, text=text, **m))
    return out


def worst(levels):
    return max(levels, key=ORDER.index) if levels else "normal"


def chip(level):
    return "stable" if level == "normal" else "watch" if level == "watch" else "alert"


def state(day=DEFAULT_DAY):
    day = max(1, min(TOTAL_DAYS, int(day)))
    mk_ = lambda *a, **k: mk(*a, day=day, **k)
    ms = markers(day)
    ck = checkin_state()
    byk = {i["key"]: i for i in ck["items"]}
    for m in ms:  # real check-in values raise the body-map status
        fl = [byk[k] for k in LINK.get(m["id"], []) if byk[k]["level"] != "normal"]
        if fl:
            m["level"] = worst([m["level"]] + [f["level"] for f in fl])
            m["text"] += " Today's check-in: " + ", ".join(f"{f['label']} {f['value']} {f['unit']} ({f['level']})" for f in fl) + "."
    anomalies = [a for d, a in [
        (100, "Greenhouse bay humidity drifting +8%"),
        (130, "Port scrubber efficiency down 6%"),
        (140, "CO2 spike in sleep pod 2: 1,150 ppm for 12 min")] if day >= d]
    spe = 138 <= day <= 148
    mods = {
        "radiation": dict(title="Radiation Guardian", hazard="radiation", ask="Explain my radiation level", askLabel="Ask Nova about radiation",
            metrics=[mk_("Cumulative dose", lambda d: 1.8 * d, "mSv", 300, 450, 550),
                     mk_("Dose rate (transit)", lambda d: 1.8 + .05 * math.sin(d / 3), "mSv/day", 2.5, 4, 6, dp=2),
                     mk_("Dose rate (surface)", lambda d: .67 + .03 * math.sin(d / 5), "mSv/day", 1, 2, 4, dp=2)],
            insight="Radiation can damage DNA in cells. Your body repairs most of it, but we track the total so it stays under your mission limit."),
        "gravity": dict(title="Gravity Health", hazard="gravity", ask="Start a guided workout", askLabel="Start voice-guided workout",
            metrics=[mk_("Muscle mass", lambda d: 100 - .1 * d, "% of baseline", 95, 88, 80, False),
                     mk_("Bone density", lambda d: 100 - .06 * d, "% of baseline", 92, 88, 82, False),
                     mk_("Resting heart rate", lambda d: 58 + .03 * d, "bpm", 65, 72, 85)],
            insight="Muscles and bones need load to stay strong. Resistance sessions are the best way to slow the loss, so consistency matters more than intensity."),
        "immune": dict(title="Immune Shield", hazard="immune", ask="How is my immune system?", askLabel="Ask Nova about immunity",
            metrics=[mk_("Inflammation (CRP)", lambda d: 1 + .02 * d, "mg/L", 4, 6, 10),
                     mk_("Lymphocyte count", lambda d: 2.2 - .004 * d, "x10^9/L", 1.5, 1.2, .9, False, dp=2),
                     mk_("Microbiome diversity", lambda d: 4.2 - .008 * d, "index", 3.4, 2.8, 2.2, False, dp=2),
                     mk_("Infection risk", lambda d: 4 + .05 * d, "%", 15, 25, 40)],
            insight="Space stress can make immune cells less alert. A varied diet, sleep and clean air help your defences stay balanced."),
        "mind": dict(title="MindSpace", hazard="mind", ask="I feel lonely", askLabel="Tell Nova how you feel",
            metrics=[mk_("Sleep", lambda d: 7.2 - .012 * d, "h/night", 6.5, 5.5, 4.5, False),
                     mk_("Stress level", lambda d: 30 + .15 * d, "/100", 55, 70, 85),
                     mk_("Mood", lambda d: 7.5 - .01 * d, "/10", 5.5, 4.5, 3.5, False),
                     mk_("Days since live Earth call", lambda d: 3 + (d % 9), "days", 8, 12, 18, dp=0)],
            insight="Long missions can feel isolating. Short, regular check-ins and a steady sleep routine make a big difference."),
        "habitat": dict(title="Habitat Health", hazard="habitat", ask="How is the habitat air?", askLabel="Ask Nova about the habitat",
            metrics=[mk_("CO2", lambda d: 780 + 1.5 * d, "ppm", 1000, 2000, 5000, dp=0),
                     mk_("Oxygen", lambda d: 20.9 - .002 * d, "%", 20, 19.5, 18, False, dp=2),
                     mk_("Temperature", lambda d: 22.4 + .3 * math.sin(d), "C", 25, 28, 32),
                     mk_("Humidity", lambda d: 45 + 2 * math.sin(d / 4), "%", 60, 70, 80, dp=0),
                     mk_("Microbial load", lambda d: 120 + .8 * d, "CFU/m3", 300, 500, 800, dp=0)],
            insight="The habitat is a closed loop: every breath and surface matters. Small drifts are caught early so they never become problems.",
            anomalies=anomalies),
    }
    for k, m in mods.items():
        lv = [x["level"] for x in m["metrics"]] + [x["level"] for x in ms if k in x["hazards"]]
        lv += [byk[x]["level"] for x in HAZ.get(k, [])]
        if k == "habitat" and len(anomalies) >= 2:
            lv.append("watch")
        m["level"] = worst(lv)
        m["chip"] = chip(m["level"])
    attention = sum(1 for m in mods.values() if m["chip"] == "alert")
    return dict(astronaut="Cdr. Amara Okafor", day=day, total=TOTAL_DAYS, markers=ms, modules=mods, attention=attention,
        rad=dict(limit=600, spe=spe, spe_text="Solar particle event: elevated protons for the next ~10 h. Move to the storm shelter if the rate exceeds 6 mSv/day."),
        adherence=[int((day - 6 + i) * 7 % 5 != 0) for i in range(7)],
        messages=["Mum: 'Proud of you. The garden is blooming.' (6 min delay)", "Mission Control: 'Great work on the EVA prep, Amara.'", "Sam: 'Football finals tonight, I saved you a seat.'"],
        counter=COUNTER, checkin=ck)


COUNTER = {
    "radiation": [("Storm shelter protocols", "Strong", "Operational practice; no known side effects."), ("Antioxidant-rich diet", "Emerging", "Food-based only; supplements are not proven.")],
    "gravity": [("Resistive exercise (ARED-type)", "Strong", "Use correct form; report joint pain."), ("Lower-body negative pressure", "Moderate", "Supervised use only; can cause light-headedness."), ("Vitamin D and calcium review", "Moderate", "Needs blood tests by the flight surgeon.")],
    "immune": [("Sleep and circadian lighting", "Moderate", "Safe; follow the lighting schedule."), ("Diverse fibre and fermented foods", "Emerging", "Check against onboard food allergies.")],
    "mind": [("Guided breathing", "Moderate", "Safe for everyone."), ("Scheduled Earth contact", "Moderate", "Plan around the comms delay."), ("Light therapy", "Emerging", "Avoid late in the day.")],
    "habitat": [("Filter and scrubber maintenance", "Strong", "Follow the lockout procedure."), ("Surface microbial sampling", "Moderate", "Use gloves and sealed swabs.")],
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    return jsonify(state(request.args.get("day", DEFAULT_DAY)))


def lonely_reply():
    bad = ("warning", "critical")
    s = "I'm here with you. Being far from home is hard. Would you like to talk to a crew member or Earth, or try a breathing exercise?"
    if item("mood")["level"] in bad or item("sleep")["level"] in bad:
        s += " Your recent mood and sleep check-ins are low, so please also speak with a crew member and your flight surgeon soon."
    return s


def rule_reply(text, day):
    found = voice_parse(text)
    if found:  # e.g. "my heart rate is 72"
        out = []
        for k, v in found:
            ok, msg = log_value(k, v)
            i = item(k)
            out.append(f"{i['label']} {v} {i['unit']} logged, status {i['level']}. {i['action']}" if ok else msg)
        return dict(reply=" ".join(out), nav="checkin")
    st, t = state(day), text.lower()
    for m in st["markers"]:
        if m["name"].lower() in t or (m["id"] == "spine" and "bone" in t):
            return dict(reply=f"{m['text']} Your {m['label'].lower()} is {m['value']} {m['unit']}. Status: {m['level']}.", nav="body", select=m["id"])
    mo = st["modules"]
    R = [
        (("check-in", "check in", "checkin", "log my"), lambda: "Opening your daily check-in. You can also tell me, for example: my heart rate is 70.", "checkin"),
        (("radiation", "dose", "solar"), lambda: f"Your total dose is {mo['radiation']['metrics'][0]['value']} milli-sieverts of a {st['rad']['limit']} limit. " + ("A solar particle event is active, so stay alert for shelter instructions." if st['rad']['spe'] else "Space weather is calm."), "radiation"),
        (("workout", "exercise", "muscle", "gravity"), lambda: f"Let's train. Your muscle mass is {mo['gravity']['metrics'][0]['value']} percent of baseline. Start with ten squats, then rest for thirty seconds. Ready?", "gravity"),
        (("immune", "infection"), lambda: f"Your infection risk is {mo['immune']['metrics'][3]['value']} percent. That is low to moderate.", "immune"),
        (("habitat", "air", "co2", "oxygen"), lambda: f"CO2 is {mo['habitat']['metrics'][0]['value']:.0f} parts per million and oxygen is {mo['habitat']['metrics'][1]['value']} percent. {len(mo['habitat']['anomalies'])} anomalies are logged.", "habitat"),
        (("lonely", "sad", "alone", "mood", "sleep"), lonely_reply, "companion"),
        (("music", "song"), lambda: "Playing a calm ambient playlist: Earth sounds, rain on leaves.", None),
        (("breath",), lambda: "Let's breathe together. In for four, hold for four, out for six. Again, slowly.", None),
        (("story",), lambda: "Once, a small rover named Dusty found a blue pebble on Mars. It turned out to be a message from a very patient friend...", None),
        (("message", "home"), lambda: "You have three messages: " + " | ".join(st["messages"]), None),
        (("game",), lambda: "Let's play twenty questions. I'm thinking of something found on both Earth and Mars.", None),
        (("body map", "body"), lambda: "Here is your body map. Tap a glowing marker to learn more.", "body"),
        (("research", "countermeasure"), lambda: "Here are research-based countermeasures. Research information only, not a prescription.", "research"),
        (("how am i", "status", "overall", "explain my"), lambda: f"Your overall status is stable. {st['attention']} thing{'s' if st['attention'] != 1 else ''} need attention: " + ", ".join(k for k, m in mo.items() if m['chip'] == 'alert') + ".", "home"),
    ]
    for keys, fn, nav in R:
        if any(k in t for k in keys):
            return dict(reply=fn(), nav=nav)
    return dict(reply="I can explain your radiation, gravity, immune, mind or habitat status, open your body map, or just talk. What would you like?")


@app.route("/api/checkin", methods=["POST"])
def api_checkin():
    vals = (request.get_json(force=True) or {}).get("values", {})
    errs = []
    for k, v in vals.items():
        try:
            ok, msg = log_value(k, float(v))
        except (TypeError, ValueError):
            ok, msg = False, f"{k}: not a number"
        if not ok:
            errs.append(msg)
    return jsonify(ok=not errs, errors=errs, checkin=checkin_state()), (400 if errs else 200)


@app.route("/api/checkin/reset", methods=["POST"])
def api_checkin_reset():
    reset_checkin()
    return jsonify(ok=True)


@app.route("/api/nova", methods=["POST"])
def api_nova():
    j = request.get_json(force=True)
    out = rule_reply(j.get("text", ""), j.get("day", DEFAULT_DAY))
    if os.getenv("ANTHROPIC_API_KEY"):  # optional LLM brain; falls back to rules offline
        try:
            import anthropic
            st = state(j.get("day", DEFAULT_DAY))
            ctx = {k: dict(level=m["level"], metrics=[(x["label"], x["value"], x["unit"]) for x in m["metrics"]]) for k, m in st["modules"].items()}
            r = anthropic.Anthropic().messages.create(model="claude-sonnet-4-6", max_tokens=250,
                system="You are Nova, a calm, kind voice assistant for an astronaut on Mars. Reply in 1-3 short spoken sentences, plain language, no medical diagnoses. Demo data: " + str(ctx),
                messages=[{"role": "user", "content": j.get("text", "")}])
            out["reply"] = r.content[0].text
        except Exception as e:
            print("LLM fallback:", e)
    return jsonify(out)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
