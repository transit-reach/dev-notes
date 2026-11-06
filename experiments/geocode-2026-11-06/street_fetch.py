"""門牌路名檢查的量測資料：台北市內隨機點反查（OSM 確定有的門牌）＋已知門牌，各自正向查一次，存原始結果

用法（在 backend 資料夾）：uv run python <本檔> <輸出.json> [隨機點數]
"""
import json
import random
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, ".")
from app.geocode import NOMINATIM_URL, TAIPEI_VIEWBOX, USER_AGENT  # noqa: E402

OUT = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 100


def call(path, params):
    url = f"{NOMINATIM_URL.replace('/search', path)}?{urllib.parse.urlencode(params)}"
    for _ in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=20) as r:
                return json.load(r)
        except OSError as e:
            print("retry", e, flush=True)
            time.sleep(10)
        finally:
            time.sleep(1.1)
    return None


def forward(street):
    # 和 app/geocode.py 的門牌查詢相同的參數（limit 1）
    return call("/search", {"format": "jsonv2", "limit": 1, "countrycodes": "tw", "viewbox": TAIPEI_VIEWBOX,
                            "addressdetails": 1, "namedetails": 1, "street": street, "city": "臺北市"})


items = []
# 已知門牌（題目與地標裡的）：正確的路名就是查詢的路名
for s in ["興隆路二段 218號", "羅斯福路四段 1號", "信義路五段 7號", "市府路 1號", "中華路二段 33號",
          "新光路二段 30號", "敦化北路 340號"]:
    items.append({"set": "known", "query": s, "result": forward(s)})

# 隨機點反查：拿到 OSM 有的「路名＋門牌」，再用它正向查
random.seed(7)
got = 0
while got < N:
    lat, lng = random.uniform(24.97, 25.13), random.uniform(121.48, 121.62)
    r = call("/reverse", {"format": "jsonv2", "lat": lat, "lon": lng, "zoom": 18, "addressdetails": 1})
    a = (r or {}).get("address", {})
    if "臺北市" not in (r or {}).get("display_name", "") or not a.get("road") or not a.get("house_number"):
        continue
    number = a["house_number"]
    query = f"{a['road']} {number}{'' if number.endswith('號') else '號'}"
    items.append({"set": "reverse", "query": query, "truth": {"road": a["road"], "lat": r["lat"], "lon": r["lon"]},
                  "result": forward(query)})
    got += 1
    print(got, query, flush=True)

json.dump(items, open(OUT, "w"), ensure_ascii=False, indent=1)
print("done", len(items))
