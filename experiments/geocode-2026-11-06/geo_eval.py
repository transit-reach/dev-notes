"""離線比較 Nominatim 結果的挑法：V0 現在（第 1 個）、V1 名稱檢查、V2 雙向名稱檢查、V3 名稱檢查＋優先台北"""
import json
import math
import re
import sys

items = json.load(open(sys.argv[1]))
verbose = "-v" in sys.argv
only = [a for a in sys.argv[2:] if a.startswith("V")]   # 只看這幾種（例如 V0 V4），不給就全部


def norm(s):
    return re.sub(r"[\s・·（）()「」,，]", "", s or "").replace("台", "臺").lower()


def subseq(short, long):
    it = iter(long)
    return bool(short) and all(c in it for c in short)


def cand_name(r):
    return r.get("name") or r["display_name"].split(",")[0]


def in_range(r):
    lng, lat = float(r["lon"]), float(r["lat"])
    return 121.3 <= lng <= 121.8 and 24.9 <= lat <= 25.3 and "臺北市" in r["display_name"]


def meters(a, b):
    lng1, lat1, lng2, lat2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def v0(q, cs):
    return cs[0] if cs else None


def v1(q, cs):
    return next((c for c in cs if subseq(norm(q), norm(cand_name(c)))), None)


def v2(q, cs):
    return next((c for c in cs if subseq(norm(q), norm(cand_name(c))) or subseq(norm(cand_name(c)), norm(q))), None)


def v3(q, cs):
    ok = [c for c in cs if subseq(norm(q), norm(cand_name(c)))]
    return next((c for c in ok if in_range(c)), ok[0] if ok else None)


def all_names(r):
    """候選的所有名字：name 加上 namedetails（別名、正式名稱、舊名、各語言）"""
    names = {cand_name(r)} | set((r.get("namedetails") or {}).values())
    return [norm(n) for n in names if n]


def v4(q, cs):
    nq = norm(q)
    return next((c for c in cs if any(subseq(nq, n) or (len(n) >= 3 and subseq(n, nq)) for n in all_names(c))), None)


def v5(q, cs):
    nq = norm(q)
    return next((c for c in cs if any(subseq(nq, n) for n in all_names(c))), None)


def outcome(item, r):
    """對／看得出的錯（範圍外）／看不出的錯（台北市內但位置錯）／找不到"""
    if r is None:
        return "找不到"
    if item["expect"] == "out_of_range":
        return "看不出的錯" if in_range(r) else "對"
    if not in_range(r):
        return "看得出的錯"
    return "對" if meters((float(r["lon"]), float(r["lat"])), item["expect"]) <= 500 else "看不出的錯"


KINDS = ["對", "看得出的錯", "找不到", "看不出的錯"]
for s in ("dev", "holdout"):
    subset = {q: it for q, it in items.items() if it["set"] == s}
    print(f"\n== {s}（{len(subset)} 個地名）")
    print("     " + "  ".join(f"{k:>5}" for k in KINDS))
    for name, f in (("V0", v0), ("V1", v1), ("V2", v2), ("V3", v3), ("V4", v4), ("V5", v5)):
        if only and name not in only:
            continue
        res = {q: outcome(it, f(q, it["candidates"])) for q, it in subset.items()}
        print(f"{name}   " + "  ".join(f"{sum(v == k for v in res.values()):>6}" for k in KINDS))
        if verbose:
            for q, v in res.items():
                if v != "對":
                    r = f(q, subset[q]["candidates"])
                    print(f"      {v} {q} → {cand_name(r) if r else '-'} {r['display_name'][-20:] if r else ''}")
