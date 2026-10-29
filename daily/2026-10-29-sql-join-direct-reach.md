# 2026-10-29 SQL JOIN 與直達查詢

## 今日目標

- [x] JOIN 查詢：找出經過附近站牌的路線，與 Citymapper 比對
- [x] 直達查詢：同子路線、同方向、站序在上車站之後；同路線同方向只留最近的上車站
- [ ] 到興隆國小站實測雙北 AI 公車站長（移到明天）
- [ ] 更新提案競品比較表（移到明天）

## 1. JOIN 查詢：從站牌找到路線與下游站

**問題**：提案的查詢邏輯 D～F 要跨 4 張表（`stops`、`route_stops`、`route_patterns`、`routes`）才能從站牌查到路線、方向與站序，需要先學會 JOIN。

**參考**：`db/init/01_schema.sql` 的主鍵與外鍵、固定測試資料（Citymapper 的興隆國小 16 條路線、606 到銘傳大學 30 站）。

**行動**：SQL 寫成檔案放在 backend repo 的 `sql/practice/`，從單表開始，一次加一張表。

| 檔案 | 做什麼 | 新語法 | 結果 |
| --- | --- | --- | --- |
| 00 | 站名「興隆國小」的 `stop_uid` | `SELECT / FROM / WHERE` | 30 個 |
| 01 | `stops` + `route_stops` | `JOIN ... ON` | 36 列 |
| 02 | 再加 `route_patterns`（兩欄主鍵） | `ON ... AND ...` | 36 列 |
| 03 | 再加 `routes`，列出不重複路線名 | `DISTINCT` | 16 條，與 Citymapper 一致 |
| 04 | 起點 300 m 內的站牌與距離 | `ST_Distance` | 6 個站名、11 個站位 |
| 05 | 興隆國小搭 606 的下游站 | 同一張表 JOIN 兩次 | 銘傳大學 30 站 |

SQL 在 VM 上、psql 在容器裡，所以用 stdin 送進去：

```bash
docker compose exec -T db psql -U transit -d transit < sql/practice/05_downstream.sql
# -T：不配置互動式終端機，讓 < 能把檔案內容送進容器
# < ：把檔案內容當作 psql 的輸入
```

**結果**：

- 03 的 16 條路線和 Citymapper 的清單逐條比對，沒有多也沒有少。
- 05 的 606 到銘傳大學 30 站，與測試資料一致。

## 2. 直達查詢（E、F）

**問題**：附近好幾個站牌常停同一條線，要在「同一子路線、同一方向」只保留最近的上車站，再接上它的下游站。

**行動**：

- 06：用 `DISTINCT ON (subroute_uid, direction)` 每個子路線方向只留最近的上車站，共 49 列。其中 9 條路線（237、294、295、295副、298、611、棕12、棕22、綠18）不經過興隆國小，在興隆路口(辛亥)或中國科技大學(辛亥)上車。
- 07：把 06 當成 `WITH boarding` 暫存結果，再 JOIN 同子路線、同方向、`stop_sequence` 較大的站。

<details>
<summary>07_direct_reach.sql</summary>

```sql
WITH boarding AS (
    SELECT DISTINCT ON (up.subroute_uid, up.direction)
           r.route_name,
           up.subroute_uid,
           up.direction,
           s.stop_name,
           up.stop_sequence,
           round(ST_Distance(s.geom, ST_MakePoint(121.55236183957491, 25.001343763104394)::geography)) AS distance_m
    FROM stops AS s
    JOIN route_stops    AS up ON s.stop_uid = up.stop_uid
    JOIN route_patterns AS rp ON up.subroute_uid = rp.subroute_uid
                             AND up.direction = rp.direction
    JOIN routes         AS r  ON rp.route_uid = r.route_uid
    WHERE ST_DWithin(s.geom, ST_MakePoint(121.55236183957491, 25.001343763104394)::geography, 300)
    ORDER BY up.subroute_uid, up.direction, distance_m
)
SELECT b.route_name,
       b.direction,
       b.stop_name AS up_stop,
       b.distance_m,
       s2.stop_name AS down_stop,
       down.stop_sequence - b.stop_sequence AS n_stops
FROM boarding AS b
JOIN route_stops  AS down ON b.subroute_uid = down.subroute_uid
                         AND b.direction = down.direction
                         AND down.stop_sequence > b.stop_sequence
JOIN stops          AS s2 ON down.stop_uid = s2.stop_uid
WHERE s2.stop_name = '銘傳大學'
ORDER BY n_stops;
```

</details>

**結果**：不篩下車站時共 1,010 列；只看銘傳大學：

```
 route_name | direction | up_stop  | distance_m | down_stop | n_stops 
------------+-----------+----------+------------+-----------+---------
 109        |         0 | 興隆國小 |         70 | 銘傳大學  |      27
 606        |         0 | 興隆國小 |         70 | 銘傳大學  |      30
 606通勤    |         0 | 興隆國小 |         70 | 銘傳大學  |      30
(3 rows)
```

**最重要的發現：109 也能直達銘傳大學，而且比 606 少 3 站**

原本的測試資料只記錄 606（30 站）。查詢多找出 109（27 站）和 606通勤（30 站）。用 Bus+ 確認 109 確實經過興隆國小與銘傳大學；27 這個站數只來自資料庫，沒有逐站核對。站數少不代表比較快，時間未驗證。已更新測試資料。

## 3. 踩坑與學到的觀念

| 問題 | 原因 | 怎麼確認 |
| --- | --- | --- |
| 02 只比對 `subroute_uid`，結果是 71 列，不是 36 列 | 同一子路線的去程與返程互相配對，多出錯誤組合（不是重複資料） | 把兩邊的 `direction` 都印出來，看到去程配到返程 |
| `psql -f` 讀不到 VM 的檔案 | `psql` 在容器裡執行，看不到 VM 的路徑 | 改用 `-T` 加 `<` 送進容器 |
| `DISTINCT ON` 留下的不是最近的站 | 留哪一列由 `ORDER BY` 的最後一個欄位決定，要最近就得用距離排序；用站序排會留下站序最小的站 | 606 返程留成興德國小（211 m），正確是興隆國小（99 m）；49 列中有 22 列不同 |
| CLAUDE.md 寫「300 m 內 6 站」，查詢卻有 11 列 | 6 是站名數，實際有 11 個站位（`station_id`） | 兩個興隆國小站位相距 39 m、方向分布相反，推測是馬路兩側，未實地確認 |

**學到的觀念**：JOIN 條件要對應主鍵的所有欄位，少一欄不會報錯，只會悄悄多出資料。每加一張表就檢查筆數，才抓得到。

## 明日計畫

- 到興隆國小站實測雙北 AI 公車站長，更新提案的競品比較表
- 把 07 的結果依下車站整理成「目的地 → 可搭路線、最少站數」，同一條路線號碼會因子路線不同而重複出現，需要去重
- 匯入捷運站序
