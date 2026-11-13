# ASTRABIO (Flask)
Voice-first astronaut health self-assessment for long missions. NASA Space Apps 2026 challenge: *Create Health Monitoring Software for Astronauts*.

    pip install -r requirements.txt
    python app.py          # open http://127.0.0.1:5000 in Chrome or Edge
    python test_app.py     # run the checks

## What it does
- **Check-in:** enter blood pressure, heart rate, blood sugar, temperature, sleep and mood. Each gets a color status (own baseline plus normal range), why it matters in space, how to measure it, what to do, and an escalation flag.
- **Body map:** interactive 3D body. Affected parts glow and pulse. Check-in results update it.
- **ASTRA voice agent:** speak or type. Try: "my heart rate is 72", "show my body map", "explain my radiation level", "I feel lonely".
- **Module screens:** radiation, gravity, immune, mind, habitat, companion, research (demo data).
- Set `ANTHROPIC_API_KEY` to let an LLM write ASTRA's replies. Without it, built-in rules are used.

## Important
All values are demo data and all health ranges are **placeholders** (see `checkin.py`). The app gives guidance only, not diagnosis.

## Files
- `app.py` Flask backend and ASTRA rules
- `checkin.py` check-in engine (ranges, baselines, status, guidance, score, streak)
- `templates/index.html` the whole interface
- `test_app.py`, `GAPS.md`
