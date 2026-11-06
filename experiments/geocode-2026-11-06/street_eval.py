"""離線比較門牌查詢的檢查方法：R0 現在（直接採用）、R1 路名一樣、R2 路名＋門牌號碼都一樣"""
import json
import math
import re
import sys

items = json.load(open(sys.argv[1]))
verbose = "-v" in sys.argv
LIMIT = 300   # 附近站牌的範圍；大範圍地點（動物園）同一門牌的點可能差幾百公尺
NUM = {str(i): c for i, c in enumerate("零一二三四五六七八九十")}


def norm_road(s):
    s = re.sub(r"\s", "", s or "").replace("台", "臺")
    return re.sub(r"(\d+)段", lambda m: NUM.get(m.group(1), m.group(1)) + "段", s)


def split(query):
    """「路名 門牌號」：查詢在門牌前有空格（app/geocode.py 也會補），用最後一個空格切開"""
    road, _, number = query.strip().rpartition(" ")
    return norm_road(road), re.sub(r"號$", "", number)


def number_of(r):
    return re.sub(r"號$", "", ((r or {}).get("address") or {}).get("house_number", ""))


def meters(a, b):
    lng1, lat1, lng2, lat2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def accept(rule, query, r):
    if not r:
        return False
    if rule == "R0":
        return True
    road, number = split(query)
    same_road = norm_road((r.get("address") or {}).get("road")) == road
    return same_road and (rule == "R1" or number_of(r) == number)


def outcome(item, r):
    """reverse 組有正確座標：50 m 內算對；known 組沒有座標，路名一樣＋號碼一樣算對"""
    if not r:
        return "找不到"
    if item["set"] == "reverse":
        d = meters((float(r["lon"]), float(r["lat"])), (float(item["truth"]["lon"]), float(item["truth"]["lat"])))
        return "對" if d <= LIMIT else f"錯（差 {d:.0f} m）"
    road, number = split(item["query"])
    ok = norm_road((r.get("address") or {}).get("road")) == road and number_of(r) == number
    return "對" if ok else "錯（" + (r.get("address") or {}).get("road", "?") + number_of(r) + "號）"


for s in ("known", "reverse"):
    subset = [it for it in items if it["set"] == s]
    print(f"\n== {s}（{len(subset)} 個門牌）")
    for rule in ("R0", "R1", "R2"):
        res = []
        for it in subset:
            r = (it["result"] or [None])[0]
            res.append((it["query"], outcome(it, r if accept(rule, it["query"], r) else None)))
        right = sum(o == "對" for _, o in res)
        wrong = sum(o.startswith("錯") for _, o in res)
        nf = sum(o == "找不到" for _, o in res)
        print(f"{rule}  對 {right}  錯 {wrong}  找不到 {nf}")
        if verbose:
            for q, o in res:
                if o != "對":
                    print("     ", o, q)
