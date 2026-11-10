# 新題目的 B／C 對照（11/9）

用修正規則時沒看過的 30 題（`simulated_new`，Z1～Z30，出題與標註見 [../external-questions.md](../external-questions.md)），比較 B（一律交給 LLM）和 C（規則 → LLM）。線上版本 backend `2433f79`，兩組交錯、各跑 3 次，因為 Gemini 結果不固定。

```bash
docker exec -w /app transit-reach-api-1 python scripts/eval_modes.py llm  /tmp/z-compare/B1 --only Z1,...,Z30
docker exec -w /app transit-reach-api-1 python scripts/eval_modes.py auto /tmp/z-compare/C1 --only Z1,...,Z30
```

## 結果

| 輪次 | 正確 | Gemini 呼叫 | 耗時中位數 |
| --- | --- | --- | --- |
| B1／B2／B3 | 21／21／20 | 34／33／33 | 1.4／1.3／1.6 秒 |
| C1／C2／C3 | 20／19／20 | 29／29／29 | 1.8／1.3／1.2 秒 |

**打平**：差 1 題，和同一組每輪之間的波動一樣大。耗時也分不出差別，因為這批題目 26 題走 Gemini。

- 規則接手 4 題（Z2、Z7、Z14、Z21）：C 每次對 3 題，錯 Z2（「捷運直達」沒抓到）；B 對 3～4 題，Z7 三次錯兩次（漏掉捷運條件）。規則和 Gemini 各輸一題。
- 兩組每次都錯 7 題：Z1、Z10、Z22、Z23、Z24 起點定位；Z28、Z30 回答方式和標註不同。
- 同題不同次結果不同：Z4、Z6、Z9、Z26、Z7（B）。

## 怎麼解讀

- 走 Gemini 的題目，兩組答案本質相同，所以 C 的正確率不會明顯高於 B；C 的價值是少呼叫 Gemini、規則接手的問法結果固定。
- Z 在規則修正（PR #16）時沒看過，但地名檢查（PR #17）和 Gemini 參數檢查（PR #18）是看過 Z 的錯誤之後做的，絕對分數偏樂觀，兩組的相對比較仍公平。
- 11/7 記錄的 C「19 → 22」是用存好的回應重新計分；這次重新呼叫 Gemini，C 是 19～20。以這次為準。

| 檔案 | 內容 |
| --- | --- |
| `B1.json`～`C3.json` | 每輪每題的解析結果、對錯、耗時、呼叫次數 |
