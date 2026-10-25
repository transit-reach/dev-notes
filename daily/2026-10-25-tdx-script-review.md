# 2026-10-25 讀懂 TDX 取資料腳本

## 今日目標

- [x] 讀完取資料腳本剩下的段落（呼叫 API、重試、存檔、主流程）
- [ ] 修改練習：用已下載的資料算出路線數、子路線數（移到明天）

## 1. 腳本整體流程

```
main()
 ├─ get_token()              用 Client ID / Secret 換 token（POST）
 ├─ fetch(token, 公車站序)    帶著 token 呼叫 API（GET），遇到 429 重試，存成 JSON
 ├─ 等 12 秒                 避開每分鐘 5 次的頻率限制
 ├─ fetch(token, 捷運站序)
 └─ 印出第一筆公車資料的欄位
```

## 2. 理解的重點

### 呼叫 API 時，token 為什麼放在 header？

換 token 和使用 token 依循的規範不同：

| | 換 token | 呼叫 API |
| --- | --- | --- |
| HTTP 方法 | POST | GET |
| 憑證放在哪 | 請求本體（表單格式） | `Authorization: Bearer <token>` header |

GET 請求沒有本體，放在網址裡又會留在伺服器紀錄中，所以 `Authorization` header 是呼叫 API 時放憑證的標準位置。`Bearer` 的意思是「持有者」，誰拿著 token 誰就能用，因此 token 要保護好，且設有效期限。

### `Accept-Encoding: gzip` 的作用

告訴伺服器「我可以接受 gzip 壓縮的回應」。伺服器壓縮後再傳，`requests` 收到會自動解壓縮。傳輸量變小、下載變快；存到硬碟的檔案是解壓縮後的原始大小（約 20 MB）。

### 重試機制：`for ... else`

```python
for attempt in range(3):
    resp = requests.get(...)
    if resp.status_code == 429:   # 超過頻率限制
        time.sleep(15)
        continue                  # 進入下一輪重試
    resp.raise_for_status()
    break                         # 成功，跳出迴圈（也跳過 else）
else:
    raise RuntimeError(...)       # 三輪都沒有 break，宣告失敗
```

`for ... else` 的 `else` 只在迴圈**沒有被 break、正常跑完**時執行，在這裡代表「三次都失敗」。

**發現的問題**：第三次遇到 429 時，程式仍會先等 15 秒才報錯，但之後已經沒有下一次重試，這 15 秒是白等的。

### 兩個 timeout 為什麼不同

換 token 只回傳一小段文字（30 秒）；抓整個台北市的公車站序約 20 MB（60 秒）。`requests` 的 timeout 不是整個下載的總時間，而是連線與「每次等待下一段資料」的上限，資料持續傳輸時不會被中斷。

### 其他

| 寫法 | 作用 |
| --- | --- |
| `mkdir(parents=True, exist_ok=True)` | `parents`：上層資料夾不存在時一起建立；`exist_ok`：資料夾已存在時不報錯。兩者都不會刪除既有檔案 |
| `dict["key"]` 與 `dict.get("key")` | 欄位不存在時，前者直接出錯，後者回傳 `None` 或指定的預設值。必要欄位用前者（盡早發現問題），探索資料或選填欄位用後者 |
| `if __name__ == "__main__":` | 直接執行檔案時才呼叫 `main()`；被其他檔案匯入時不執行。之後 backend 若要重用 `fetch()`，匯入時不會意外觸發下載 |

## 明日計畫

- 修改練習：用已下載的 JSON 算出總筆數、路線號碼數、子路線數、各方向筆數，驗證「每筆資料 ＝ 一個子路線的一個方向」
- 修正「第三次 429 白等 15 秒」的問題
- 設計資料庫 schema
