"""Run: python -m pytest -q   (or python test_app.py)"""
import checkin
from app import app


def c():
    checkin.reset()
    return app.test_client()


def test_pages_and_state():
    cl = c()
    assert cl.get("/").status_code == 200
    s = cl.get("/api/state?day=142").get_json()
    assert len(s["checkin"]["items"]) == 7 and s["checkin"]["score"] == 100


def test_checkin_levels_and_bodymap():
    cl = c()
    r = cl.post("/api/checkin", json={"values": {"hr": 130, "sleep": 5}}).get_json()
    lv = {i["key"]: i["level"] for i in r["checkin"]["items"]}
    assert lv["hr"] == "critical" and lv["sleep"] == "warning" and r["checkin"]["escalate"]
    s = cl.get("/api/state?day=142").get_json()
    assert {m["id"]: m["level"] for m in s["markers"]}["heart"] == "critical"


def test_typo_guard_and_voice():
    cl = c()
    assert cl.post("/api/checkin", json={"values": {"hr": 7000}}).status_code == 400
    r = cl.post("/api/nova", json={"text": "my heart rate is 72", "day": 142}).get_json()
    assert r["nav"] == "checkin" and "logged" in r["reply"]


def test_streak_and_lonely_safety():
    cl = c()
    cl.post("/api/checkin", json={"values": {k: s["base"] for k, s in checkin.SPEC.items()}})
    assert cl.get("/api/state").get_json()["checkin"]["streak"] == 7
    cl.post("/api/checkin", json={"values": {"mood": 3}})
    assert "flight surgeon" in cl.post("/api/nova", json={"text": "I feel lonely"}).get_json()["reply"]


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
