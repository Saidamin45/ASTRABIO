# ASTRABIO: what is missing, and how to solve it

Priority: **P1** = the challenge or judges will test it, **P2** = strengthens the entry, **P3** = nice to have.

| # | Priority | Gap | Why it matters | Proposed solution |
|---|---|---|---|---|
| 1 | P1 | **Sourced health ranges.** All normal, watch and warning ranges in `checkin.py` are placeholder adult references. | The challenge asks when a result needs the crew or a flight surgeon. Unsourced thresholds undermine trust. | Find ranges in NASA Human Research Program material and NASA's human-system standard (NASA-STD-3001). Ask a mentor, doctor or flight-surgeon contact to review. Put the source in each `SPEC` entry and show it in the UI. |
| 2 | P1 | **Escalation is only a toast.** "Contact flight surgeon" does nothing real. | The challenge wants guidance on when and how to act. | Generate a one-page summary of recent readings (printable HTML or CSV) and a message template for the flight surgeon. Add a "delayed comms" note (send now, reply in N minutes). |
| 3 | P1 | **Simulated module data duplicates real check-in inputs.** Sleep, mood and heart rate exist in both the 9 demo screens and the check-in. | Two sources of truth confuse the demo. | Make module screens read from check-in history. Keep simulated data only for what cannot be entered (radiation dose, habitat sensors, bone density). |
| 4 | P1 | **No real NASA data feed.** Radiation values are invented. Curiosity RAD and NASA DONKI are not connected. | Judges expect NASA data. It is also the cheapest real-data win. | Add `radiation_feed.py`: fetch DONKI solar events (api.nasa.gov key) and RAD surface dose values, cache to JSON for offline use. Show source and date on the Radiation screen. |
| 5 | P1 | **Radiation dose limit is a demo number (600 mSv).** | Wrong limits would be misleading. | Verify against the current NASA standard and cite it. |
| 6 | P2 | **"Offline" claim is not true yet.** The app loads Three.js and a font from CDNs, and browser speech recognition usually needs internet. The header badge now says "Local demo mode". | Offline-first was a planned differentiator. | Vendor Three.js and the font locally. For offline voice, try Vosk or Whisper (WASM) and keep typed input as fallback. |
| 7 | P2 | **Data is lost on restart.** Check-ins live in memory. | A tracker needs history and multiple days. | Store readings in SQLite with a date per reading. Add per-day editing and multiple astronauts. |
| 8 | P2 | **Reminders are only a card.** No scheduled prompt. | The challenge suggests prompting astronauts to take measurements. | Add a schedule per indicator, a timer that makes Nova speak a reminder, and snooze. |
| 9 | P2 | **LLM safety.** With `ANTHROPIC_API_KEY` set, Nova's reply comes from the LLM and only a system prompt limits it. | It could give medical advice or contradict the escalation rules. | Keep status and escalation decided by the rule engine. Give the LLM only the computed status, forbid diagnoses and drug advice, and add test prompts that check it. |
| 10 | P2 | **Body map realism and mapping.** Procedural shapes, only 8 markers, and a coarse indicator-to-part mapping. | The statement suggests a clickable human figure with function and status per part. | Use a free GLB body model (check the license) with named meshes. Add a short "what this organ does" text for each part. |
| 11 | P2 | **Manual input only.** No camera or sensor input. | The statement allows camera images and other input. | Optional: read a pulse from the camera, or photograph a glucose meter and read the value. Otherwise state clearly that input is manual. |
| 12 | P2 | **No environment mode.** | The statement mentions spacecraft, station, rover and planetary base. | Add a mode switch that changes which indicators and tips are shown (for example habitat air checks for a base). |
| 13 | P3 | **Gamification is thin.** Only a health score and a streak. | Optional in the statement, but it helps engagement. | Add badges, a weekly exercise challenge, and a crew leaderboard (opt-in). |
| 14 | P3 | **Companion is rule-based.** Fixed replies for loneliness, music, stories and games. | It is our differentiator. | Use the LLM for open conversation inside the safety rules from #9. Add a real check-in flow with mood trends over several days. |
| 15 | P3 | **Accessibility and mobile.** Not tested on small screens or with a screen reader. | Judges may try it on a phone. | Test at tablet and phone sizes, add labels and keyboard control to the body map. |
| 16 | P3 | **Privacy note.** | Health data is sensitive. | Add a short statement on what is stored, where, and that demo data is simulated. |
| 17 | P2 | **Pitch material.** | Judges see the demo and the story first. | Rehearse the 3-minute demo script, record a backup video, and cite sources on a final slide. |

## Already fixed in this version
- `index.html` was not in a `templates/` folder, so Flask could not find it. It is now in `templates/`.
- Added the daily check-in: blood pressure (systolic and diastolic), heart rate, blood sugar, body temperature, sleep and mood.
- Each result has a color status, personal-baseline comparison, why it matters in space, how to measure, what to do, and an escalation flag.
- Check-in results change the body map and the module status chips.
- Added voice logging ("my heart rate is 72"), a typo guard, health score, streak and a due-today card.
- The companion now suggests the flight surgeon when mood or sleep is low.
- Added `test_app.py`.
