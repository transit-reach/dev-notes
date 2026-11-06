"""量測 Nominatim：收集地名與正確座標，每個地名拿 5 個候選存起來（只查一次，之後離線比較檢查方法）

dev：X／Y／Z 三批題目裡系統實際送出的起點名稱（資料庫認不得、會交給 Nominatim 的），正確座標用標註
holdout：data/landmarks.json 的正式名稱與簡稱，正確座標用地標座標（人工確認過）
"""
import glob
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, ".")
from dotenv import load_dotenv  # noqa: E402

load_dotenv(".env")
from app.ask import known_place  # noqa: E402
from app.geocode import NOMINATIM_URL, TAIPEI_VIEWBOX, USER_AGENT, geocode  # noqa: E402
from app.reach import connect  # noqa: E402

OUT = sys.argv[1]
EXP = os.path.expanduser("~/projects/dev-notes/experiments/simulated-2026-11-06")
questions = {q["id"]: q for q in json.load(open("scripts/eval_questions.json", encoding="utf-8"))["questions"]}

items = {}   # query → {"set", "expect": (lng, lat) 或 "out_of_range", "from"}
expected_cache = {}


def expected_point(e):
    key = (e.get("street"), e.get("place"))
    if key not in expected_cache:
        with connect() as conn:
            p = known_place(conn, e["place"]) if e.get("place") else None
        if p is None:
            time.sleep(1.1)
            p = geocode(street=e.get("street"), place=e.get("place"))
        expected_cache[key] = (p["lng"], p["lat"])
    return expected_cache[key]


# dev：各次執行裡系統送出的起點名稱
for path in glob.glob(f"{EXP}/*/[XYZ]*.json"):
    qid = os.path.basename(path)[:-5]
    q = questions.get(qid)
    if q is None:
        continue
    r = json.load(open(path))
    for call in r.get("tool_calls", []):
        name = (call.get("args") or {}).get("place")
        if not name or name in items:
            continue
        with connect() as conn:
            if known_place(conn, name) is not None:
                continue   # 資料庫認得，不會問 Nominatim
        e = q["expect"]
        if e == "out_of_range":
            items[name] = {"set": "dev", "expect": "out_of_range", "from": qid}
        elif isinstance(e, dict) and (e.get("place") or e.get("street")):
            items[name] = {"set": "dev", "expect": expected_point(e), "from": qid}

# holdout：地標正式名稱與簡稱
for lm in json.load(open("data/landmarks.json", encoding="utf-8")):
    for name in [lm["name"]] + lm.get("aliases", []):
        if name not in items:
            items[name] = {"set": "holdout", "expect": (lm["lng"], lm["lat"]), "from": lm["name"]}

print({s: sum(v["set"] == s for v in items.values()) for s in ("dev", "holdout")}, flush=True)
for name, item in items.items():
    params = {"format": "jsonv2", "limit": 5, "countrycodes": "tw", "viewbox": TAIPEI_VIEWBOX, "namedetails": 1,
              "addressdetails": 1, "q": name}
    req = urllib.request.Request(f"{NOMINATIM_URL}?{urllib.parse.urlencode(params)}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as res:
        item["candidates"] = json.load(res)
    time.sleep(1.1)
json.dump(items, open(OUT, "w"), ensure_ascii=False, indent=1)
print("done", len(items))
