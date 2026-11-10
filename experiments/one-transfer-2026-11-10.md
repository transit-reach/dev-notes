# 轉一次車能到多少站（11/10）

簡報「專案範圍」頁說明為什麼不做轉乘：轉一次車，能到的站多 7 倍。這裡記錄怎麼算的。

## 結果

起點：興隆路二段 218 號（經度 121.55236183957491，緯度 25.001343763104394），上車站為 300 m 內的站牌。資料庫是 8080 的 `transit-reach-db-1`（backend `2433f79` 匯入的固定版本）。

| | 能到的站位（`station_id`） |
| --- | --- |
| 不換車 | 383 |
| 轉一次車（含不換車） | 2,785 |
| 台北全部站位（公車＋捷運） | 5,497 |

- 2,785 ÷ 383 ≈ 7.3 倍，超過全部站位的一半。
- 383 和 `/reach` 的 375 個下車站不同：這裡用 `station_id` 直接去重、沒有排除上車站本身，算法比 `/reach` 粗；只用來估倍數。
- **只算在同一個站位換車**（下車的站位就是上車的站位）。走到對面或附近站牌換車沒有算，實際能到的只會更多。
- 不考慮班次、時間，只看站序。

## 查詢

```sql
WITH origin AS (SELECT ST_SetSRID(ST_MakePoint(121.55236183957491,25.001343763104394),4326)::geography g),
board AS (            -- 300 m 內每個子路線方向最早的上車站
  SELECT rs.subroute_uid, rs.direction, min(rs.stop_sequence) seq
  FROM route_stops rs JOIN stops s USING (stop_uid), origin
  WHERE ST_DWithin(s.geom, origin.g, 300) GROUP BY 1,2),
direct AS (           -- 不換車：同方向、站序在後面的站位
  SELECT DISTINCT s.station_id FROM board b
  JOIN route_stops rs ON rs.subroute_uid=b.subroute_uid AND rs.direction=b.direction AND rs.stop_sequence>b.seq
  JOIN stops s USING (stop_uid)),
board2 AS (           -- 在不換車能到的站位換車
  SELECT rs.subroute_uid, rs.direction, min(rs.stop_sequence) seq
  FROM route_stops rs JOIN stops s USING (stop_uid) JOIN direct d ON d.station_id=s.station_id GROUP BY 1,2),
one AS (
  SELECT DISTINCT s.station_id FROM board2 b
  JOIN route_stops rs ON rs.subroute_uid=b.subroute_uid AND rs.direction=b.direction AND rs.stop_sequence>b.seq
  JOIN stops s USING (stop_uid))
SELECT (SELECT count(*) FROM direct) direct_stations,
       (SELECT count(*) FROM (SELECT station_id FROM direct UNION SELECT station_id FROM one) u) with_one_transfer,
       (SELECT count(DISTINCT station_id) FROM stops) all_stations;
```
