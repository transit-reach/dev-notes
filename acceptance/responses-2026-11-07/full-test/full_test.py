"""8080 完整測試：網頁檔案、/reach、/suggest、/ask（正常題＋邊界題），結果寫到 out 資料夾

11/5 版（由 responses-2026-11-04/final-full-test 複製修改）：
- 「和查詢無關」改檢查 guide（11/5 起 Gemini 會呼叫 explain，原本檢查「沒有呼叫工具」）
- 新增：/suggest、百貨商場／電影院分頁、店家問題（不呼叫 Gemini）、分頁直接帶參數
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://localhost:8080"
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
results = []


def check(name, ok, detail=""):
    results.append((ok, name, detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail else ""), flush=True)


def get(path):
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(BASE + path, timeout=200) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read(), time.perf_counter() - t
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read(), time.perf_counter() - t


def ask(q):
    req = urllib.request.Request(BASE + "/api/ask", data=json.dumps({"question": q}).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=200) as r:
            return r.status, json.loads(r.read()), time.perf_counter() - t
    except urllib.error.HTTPError as e:
        return e.code, None, time.perf_counter() - t


# ---------- 網頁檔案 ----------
status, ctype, body, _ = get("/")
html = body.decode()
check("首頁 200", status == 200)
check("標題 OneRide", "<title>OneRide｜不換車，能去哪？</title>" in html)
for tag in ['rel="manifest"', 'rel="apple-touch-icon"', 'name="theme-color"', 'rel="icon"']:
    check(f"index.html 有 {tag}", tag in html)
status, ctype, body, _ = get("/manifest.webmanifest")
m = json.loads(body)
check("manifest 類型", "application/manifest+json" in ctype, ctype)
check("manifest 名稱", m["short_name"] == "OneRide" and m["display"] == "standalone")
for icon in m["icons"]:
    s, c, b, _ = get(icon["src"])
    check(f"圖示 {icon['src']}", s == 200 and len(b) > 500 and ("png" in c or "svg" in c), f"{s} {c} {len(b)} B")
s, c, b, _ = get("/apple-touch-icon.png")
check("apple-touch-icon", s == 200 and "png" in c)
s, c, b, _ = get("/no/such/page")
check("不存在的網址回首頁（SPA）", s == 200 and b"OneRide" in b)
s, c, b, _ = get("/preview.html")
check("preview.html 沒有打包進正式版", "OneRide 樣式預覽".encode() not in b)

# ---------- /reach ----------
POINTS = {"興隆路二段218號": (121.55236183957491, 25.001343763104394, 375),
          "台北101": (121.5645, 25.03383, 480),
          "羅斯福路四段1號": (121.535973, 25.015101, 798)}
for name, (lng, lat, expect) in POINTS.items():
    times = []
    for _ in range(3):
        s, c, b, t = get(f"/api/reach?lng={lng}&lat={lat}")
        times.append(t)
    d = json.loads(b)
    ids = {x["station_id"] for x in d["boarding"]}
    names = {x["station_id"]: x["stop_name"] for x in d["boarding"]}
    routes = [r for x in d["destinations"] for r in x["routes"]]
    bad = [r for r in routes if r.get("board_station_id") not in ids or names[r["board_station_id"]] != r["board_stop"]]
    check(f"/reach {name} 下車站數", d["count"] == expect, f"{d['count']}（預期 {expect}）")
    check(f"/reach {name} 上車站 ID 都對得上", not bad, f"{len(routes)} 筆路線，不符 {len(bad)}")
    check(f"/reach {name} 1 秒內", max(times) < 1, f"最慢 {max(times):.2f} 秒")
for label, q in [("經度範圍外", "lng=120.0&lat=25.0"), ("緯度範圍外", "lng=121.5&lat=26.0"),
                 ("缺少 lat", "lng=121.5"), ("radius 太小", "lng=121.55&lat=25.0&radius_m=10")]:
    s, c, b, _ = get(f"/api/reach?{q}")
    check(f"/reach {label} → 422", s == 422, str(s))
s, c, b, _ = get("/api/reach?lng=121.58&lat=25.19")   # 陽明山山區
d = json.loads(b)
check("/reach 附近沒有站牌的點", s == 200 and d["boarding"] == [] and d["count"] == 0, f"boarding {len(d['boarding'])}")

# ---------- /suggest ----------
s, c, b, _ = get("/api/suggest?" + urllib.parse.urlencode({"q": "台科"}))
items = json.loads(b)["items"]
check("/suggest 台科 → 第一個是國立臺灣科技大學", s == 200 and items and items[0]["label"] == "國立臺灣科技大學")
s, c, b, _ = get("/api/suggest?" + urllib.parse.urlencode({"q": "台科大能到哪"}))
check("/suggest 問句不給建議", s == 200 and json.loads(b)["items"] == [])

# ---------- /ask：不需要 Gemini 的檢查 ----------
for label, q in [("空白問題", ""), ("201 字", "興" * 201)]:
    s, d, t = ask(q)
    check(f"/ask {label} → 422", s == 422, str(s))


def ask_args(q, args):
    req = urllib.request.Request(BASE + "/api/ask", data=json.dumps({"question": q, "args": args}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=200) as r:
        return r.status, json.loads(r.read())


# 分頁（引導按鈕）直接帶參數，不經規則或 Gemini；11/5 新類別
for cat, expect in [("百貨商場", 18), ("電影院", None), ("夜市", None)]:
    s, d = ask_args(f"能到哪些{cat}？", {"intent": "category", "street": "興隆路二段 218號", "category": cat})
    n = len(d["view"].get("places", []))
    check(f"/ask 分頁 {cat}", s == 200 and d["args"]["category"] == cat and n > 0 and (expect is None or n == expect),
          f"{n} 個" + (f"（預期 {expect}）" if expect else ""))
s, d = ask_args("能到哪裡？", {"intent": "overview", "street": "興隆路二段 218號"})
cats = [g["category"] for g in d["view"]["groups"]]
check("/ask 能到哪 有百貨商場、電影院", "百貨商場" in cats and "電影院" in cats, "、".join(cats))
# 店家：規則直接回說明，不呼叫 Gemini
for q in ["台科大能到哪些咖啡廳？", "附近有便利商店嗎"]:
    s, d, t = ask(q)
    check(f"/ask 店家：{q}", s == 200 and d["view"]["type"] == "guide" and d["view"]["kind"] == "no_data"
          and d["metrics"]["gemini_calls"] == 0, d["view"]["summary"])

# ---------- /ask：Gemini ----------
STANDARD = [
    "臺北市文山區興業里興隆路二段218號附近的公車站有哪些公車經過？",
    "從興隆國小站搭673公車往大鵬新城方向，之後會經過哪些站?",
    "從臺北市文山區興業里興隆路二段218號搭公車，不換車能到士林夜市嗎？",
    "從臺北市文山區興業里興隆路二段218號不換車能搭到哪些地方？",
    "從萬芳醫院站搭捷運不換車能到哪些站？",
    "從興隆路二段218號搭公車，不換車能到銘傳大學嗎？",
    "興隆路二段218號附近 10 站以內能到哪裡",
    "士林夜市附近 5 站以內能到哪裡",
    "從台北101搭車不用轉車可以到士林夜市嗎？",
    "興隆路二段218號附近，不換車能到哪些夜市？",
    "我住在羅斯福路四段1號，不換車能到哪些醫院？",
    "我在捷運萬芳醫院站，只搭捷運能到哪裡？",
    "從101搭公車不用轉車可以到松山機場嗎",
    "我在興隆路二段218號，可以直接搭車到興隆國小嗎？",
    "從桃園機場不換車能到哪裡？",
    # 歡迎卡片的範例
    "興隆路二段218號能到哪些夜市？",
    "從台北101能直達士林夜市嗎？",
    "萬芳醫院站搭捷運能到哪？",
]
EDGE = [
    ("和查詢無關", "今天天氣如何？", lambda d: d["reach"] is None and (d["view"] or {}).get("type") == "guide"),
    ("沒說起點", "不換車能到士林夜市嗎？", lambda d: d["reach"] is None and d["view"]["kind"] == "no_origin"),
    ("新類別：電影院", "台科大能到哪些電影院？", lambda d: d["view"]["type"] == "places" and d["args"]["category"] == "電影院"),
    ("新類別：百貨公司的說法", "從台北101能到哪些百貨公司？", lambda d: d["args"]["category"] == "百貨商場"),
    ("找不到的地點", "從火星基地不換車能到哪裡？", lambda d: d["reach"] is None),
    ("附近沒有捷運站卻只搭捷運", "從興隆路二段218號只搭捷運能到哪裡？",
     lambda d: "沒有捷運站" in d["answer"]),
    ("附近有哪些捷運站", "台北101附近有哪些捷運站？", lambda d: d["view"] and d["view"]["type"] == "nearby"),
    ("不存在的路線", "從興隆國小站搭999公車之後會經過哪些站？", lambda d: "沒有 999" in d["answer"]),
    ("類別＋站數條件", "從臺大醫院 10 站以內能到哪些夜市？", lambda d: d["view"] and d["view"]["type"] == "places"),
    ("站數條件下到不了", "從興隆路二段218號 10 站以內能到士林夜市嗎？", lambda d: "10 站以內" in d["answer"]),
    ("大範圍地標（台大）", "從國立臺灣大學不換車能到哪裡？", lambda d: d["reach"] is not None and d["reach"]["count"] > 0),
]

timings = []


def check_answer(label, d):
    """回答結構：segments 接起來＝answer、沒有殘留標記、清單和連結的站都在結果裡"""
    a = d["answer"]
    check(f"{label}：沒有殘留標記字元", not any(ch in a for ch in "\x01\x02\x1f"))
    if d.get("segments"):
        check(f"{label}：segments 接起來等於 answer", "".join(x["text"] for x in d["segments"]) == a)
    if d.get("reach"):
        ids = {x["station_id"] for x in d["reach"]["destinations"]} | {x["station_id"] for x in d["reach"]["boarding"]}
        rows = (d.get("view") or {}).get("rows", [])
        bad = [r for r in rows if r.get("station_id") and r["station_id"] not in ids]
        bad += [l for l in d.get("links", []) if l["station_id"] not in ids]
        check(f"{label}：清單、連結的站都在結果裡", not bad, f"不符 {len(bad)}")


n = 0
for q in STANDARD:
    n += 1
    s, d, t = ask(q)
    timings.append(t)
    json.dump(d, open(OUT / f"std{n:02d}.json", "w"), ensure_ascii=False)
    summary = (d.get("view") or {}).get("summary") or d["answer"][:40]
    check(f"/ask 標準 {n:02d} 回 200", s == 200, f"{t:.1f} 秒｜{summary}")
    check_answer(f"標準 {n:02d}", d)
    time.sleep(25)
for i, (label, q, ok) in enumerate(EDGE, 1):
    s, d, t = ask(q)
    timings.append(t)
    json.dump(d, open(OUT / f"edge{i:02d}.json", "w"), ensure_ascii=False)
    check(f"/ask 邊界：{label}", s == 200 and ok(d), f"{t:.1f} 秒｜{d['answer'][:60].replace(chr(10), ' ')}")
    check_answer(f"邊界 {label}", d)
    time.sleep(25)

timings.sort()
print(f"\n/ask {len(timings)} 題：中位數 {timings[len(timings) // 2]:.1f} 秒、最大 {timings[-1]:.1f} 秒、超過 10 秒 {sum(t > 10 for t in timings)} 題")
fails = [r for r in results if not r[0]]
print(f"合計 {len(results)} 項檢查，失敗 {len(fails)} 項")
for _, name, detail in fails:
    print("  FAIL", name, detail)
