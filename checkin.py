"""ASTRABIO check-in engine: manual measurements, personal baselines, status bands, guidance, score, streak.
RANGES ARE PLACEHOLDERS (general adult references). Replace with NASA HRP / flight-surgeon approved ranges (see GAPS.md)."""
import math, re

ORDER = ["normal", "watch", "warning", "critical"]
PEN = {"normal": 0, "watch": 5, "warning": 15, "critical": 30}
SRC = "PLACEHOLDER range: replace with a NASA HRP / flight surgeon source."

# n = normal range, w = watch range, c = warning range; outside c = critical. lim = typo guard.
SPEC = {
    "hr": dict(label="Resting heart rate", unit="bpm", n=(50, 90), w=(45, 100), c=(40, 120), lim=(20, 250), base=62, amp=2,
        why="Fluid shifts and deconditioning in microgravity change heart rate; stress and radiation can too.",
        how="Wrist sensor, or two fingers on the neck for 30 s (double it), after 5 min of rest.",
        act=("Keep up your exercise routine.", "Rest, drink water, and re-measure in 30 minutes.",
             "Rest 10 minutes and re-measure. If it stays out of range, contact the flight surgeon.")),
    "sys": dict(label="Blood pressure (systolic)", unit="mmHg", n=(90, 120), w=(85, 130), c=(80, 140), lim=(50, 250), base=112, amp=3,
        why="Blood pressure shifts as fluids move toward the head and the heart adapts to microgravity.",
        how="Upper-arm cuff, seated and rested for 5 minutes, arm at heart level.",
        act=("Keep up your exercise routine.", "Rest, reduce salt at the next meal, and re-measure in 30 minutes.",
             "Re-measure after 10 minutes of rest. If still out of range, contact the flight surgeon.")),
    "dia": dict(label="Blood pressure (diastolic)", unit="mmHg", n=(60, 80), w=(55, 85), c=(50, 90), lim=(30, 150), base=74, amp=2,
        why="Together with systolic pressure it shows how hard the heart and vessels are working in space.",
        how="Same reading as systolic: upper-arm cuff, seated, rested for 5 minutes.",
        act=("Keep up your exercise routine.", "Rest and re-measure in 30 minutes.",
             "Re-measure after 10 minutes of rest. If still out of range, contact the flight surgeon.")),
    "glucose": dict(label="Blood sugar", unit="mg/dL", n=(70, 100), w=(65, 125), c=(55, 180), lim=(20, 600), base=88, amp=4,
        why="Diet changes, stress and less activity can shift blood sugar on long missions.",
        how="Finger-prick meter before eating, with a fresh lancet and test strip.",
        act=("Keep balanced meals.", "Review recent meals, drink water, and re-test before the next meal.",
             "Re-test. If still out of range, contact the flight surgeon.")),
    "temp": dict(label="Body temperature", unit="C", n=(36.1, 37.2), w=(35.8, 37.8), c=(35.0, 38.5), lim=(30, 43), base=36.6, amp=0.15,
        why="Immune changes and infections in a closed habitat can show up first as a temperature change.",
        how="Forehead or ear thermometer, away from air vents, after 10 minutes of rest.",
        act=("Nothing needed.", "Rest, drink water, and re-measure in 1 hour. Limit close contact with crewmates.",
             "Isolate from crewmates if possible and contact the flight surgeon.")),
    "sleep": dict(label="Sleep last night", unit="hours", n=(7, 9), w=(6, 10), c=(4.5, 12), lim=(0, 24), base=7.3, amp=0.4,
        why="Light cycles, noise and isolation disrupt sleep, which affects mood, immunity and performance.",
        how="Wearable sleep tracker, or a sleep log. Enter last night's total hours.",
        act=("Keep your sleep schedule.", "Follow the circadian lighting schedule and a wind-down routine tonight.",
             "Tell the crew medical officer; the flight surgeon can review sleep support options.")),
    "mood": dict(label="Mood", unit="/10", n=(6, 10), w=(5, 10), c=(3.5, 10), lim=(1, 10), base=7.5, amp=0.5,
        why="Isolation and confinement affect mood, and low mood is a behavioral health warning sign.",
        how="Rate your mood from 1 (very low) to 10 (very good).",
        act=("Keep regular contact with crew and Earth.", "Try a breathing exercise or call someone from home.",
             "Please speak with a crew member and your flight surgeon soon.")),
}
# check-in indicator -> body marker id, and -> hazard module
LINK = {"heart": ["hr", "sys", "dia"], "brain": ["sleep", "mood"], "skin": ["temp"], "gut": ["glucose"]}
HAZ = {"gravity": ["hr", "sys", "dia"], "immune": ["temp", "glucose"], "mind": ["sleep", "mood"]}
VOICE = {"hr": r"(?:heart rate|pulse)\D{0,12}(\d+(?:\.\d+)?)", "glucose": r"(?:glucose|blood sugar)\D{0,12}(\d+(?:\.\d+)?)",
         "temp": r"temperature\D{0,12}(\d+(?:\.\d+)?)", "sleep": r"(?:slept|sleep)\D{0,12}(\d+(?:\.\d+)?)",
         "mood": r"mood\D{0,12}(\d+(?:\.\d+)?)"}

LOGS, TODAY, STREAK = {}, set(), [6, False]


def reset():
    LOGS.clear(); TODAY.clear(); STREAK[:] = [6, False]
    for k, s in SPEC.items():
        LOGS[k] = [round(s["base"] + s["amp"] * math.sin(i * 1.3 + len(k)), 1) for i in range(13)] + [s["base"]]


def band(v, s):
    inr = lambda r: r[0] <= v <= r[1]
    return "normal" if inr(s["n"]) else "watch" if inr(s["w"]) else "warning" if inr(s["c"]) else "critical"


def item(k):
    s, ser = SPEC[k], LOGS[k]
    v, base = ser[-1], sum(ser[:10]) / 10
    dev = round((v - base) / base * 100, 1)
    lv = band(v, s)
    if lv == "normal" and abs(dev) >= 15:
        lv = "watch"  # personal baseline shift
    act = s["act"][0 if lv == "normal" else 1 if lv == "watch" else 2]
    if lv == "watch" and dev and abs(dev) >= 15 and band(v, s) == "normal":
        act = f"This is {abs(dev)}% away from your own baseline. " + s["act"][1]
    return dict(key=k, label=s["label"], unit=s["unit"], value=v, level=lv, series=ser[-14:], n=s["n"], src=SRC, why=s["why"],
                how=s["how"], action=act, escalate=lv in ("warning", "critical"), logged=k in TODAY, baseline=round(base, 1), dev=dev)


def log_value(k, v):
    if k not in SPEC:
        return False, f"{k}: unknown indicator"
    lo, hi = SPEC[k]["lim"]
    if not lo <= v <= hi:
        return False, f"{SPEC[k]['label']}: {v} looks like a typing error (expected {lo}-{hi} {SPEC[k]['unit']})."
    LOGS[k][-1] = v
    TODAY.add(k)
    if len(TODAY) == len(SPEC) and not STREAK[1]:
        STREAK[0] += 1; STREAK[1] = True
    return True, ""


def voice_parse(text):
    t = text.lower()
    return [(k, float(m.group(1))) for k, p in VOICE.items() if (m := re.search(p, t))]


def checkin_state():
    items = [item(k) for k in SPEC]
    score = max(0, 100 - sum(PEN[i["level"]] for i in items))
    return dict(items=items, score=score, streak=STREAK[0], due=[i["label"] for i in items if not i["logged"]],
                escalate=any(i["escalate"] for i in items))


reset()
