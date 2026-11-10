# 大眾運輸直達地圖｜開發筆記

輸入一個地點，顯示從這裡**不換車**能直達哪些地方，以及要搭哪一條公車或捷運、往哪個方向。

- 作者：賴冠廷
- 專題提案：[proposal.md](proposal.md)
- 系統架構（實作後的做法）：[design/architecture.md](design/architecture.md)；LLM 的角色與取捨：[design/llm-design.md](design/llm-design.md)；資料庫：[design/database.md](design/database.md)

## 每日技術筆記

| 日期 | 主題 |
| --- | --- |
| 2026-10-21 | [選題與可行性分析](daily/2026-10-21-project-proposal.md) |
| 2026-10-22 | [通用 AI 基準實驗與提案調整](daily/2026-10-22-llm-baseline-experiment.md) |
| 2026-10-24 | [開發環境建置與第一次呼叫 TDX API](daily/2026-10-24-dev-environment.md) |
| 2026-10-25 | [讀懂 TDX 取資料腳本](daily/2026-10-25-tdx-script-review.md) |
| 2026-10-26 | [驗證 TDX API 與分析公車資料](daily/2026-10-26-tdx-data-analysis.md) |
| 2026-10-27 | [資料庫設計與資料匯入](daily/2026-10-27-database-import.md) | schema 定案、PostGIS 匯入公車資料、空間查詢與 Bus+ 6/6 吻合 |
| 2026-10-28 | [ER 圖與 AI 交通工具調查](daily/2026-10-28-competitor-survey.md) |
| 2026-10-29 | [SQL JOIN 與直達查詢](daily/2026-10-29-sql-join-direct-reach.md) |
| 2026-10-30 | [雙北 AI 公車站長實測與直達查詢 API](daily/2026-10-30-bus-agent-test-and-api.md) |
| 2026-11-01 | [前端地圖：點地圖顯示附近站牌與直達站](daily/2026-11-01-frontend-map.md) |
| 2026-11-02 | [Docker 整合測試與自然語言查詢](daily/2026-11-02-docker-and-llm-query.md) |
| 2026-11-03 | [捷運匯入、地標對應與驗收開始](daily/2026-11-03-metro-and-landmarks.md) |
| 2026-11-04 | [驗收完成、OneRide 介面改版、System 1／System 2](daily/2026-11-04-acceptance-and-oneride.md) |
| 2026-11-05 | [步行到地標、互動原則與統一版型、百貨商場與電影院、部署演練與報告準備](daily/2026-11-05-unified-layout-and-guide-answers.md) |

## 實驗

| 日期 | 實驗 |
| --- | --- |
| 2026-10-22 | [通用 AI 回答大眾運輸直達問題的侷限性與涵蓋率](experiments/llm-baseline.md) |
| 2026-11-04 | [System 1（規則＋LLM 備援）34 題](experiments/system1-2026-11-04/C-log.txt) |
| 2026-11-09 | [新題目 30 題的 B／C 對照：各跑 3 次，打平](experiments/simulated-2026-11-09/README.md) |

## 相關 Repository

| Repository | 內容 | 狀態 |
| --- | --- | --- |
| dev-notes | 技術筆記、提案、設計文件、會議紀錄 | 本 repo |
| backend | 後端 API（FastAPI）、資料庫與資料匯入程式 | 私人，開發中 |
| frontend | 前端網頁（Vue 3 + Vite + Leaflet + OpenStreetMap） | 私人，開發中 |
| deploy | 整合測試的 docker compose，填好 `.env` 後一行指令啟動 | 私人 |

## 資料夾說明

```
dev-notes/
├── README.md       本頁，筆記索引
├── proposal.md     專題提案
├── daily/          每日技術筆記（YYYY-MM-DD-主題.md）
├── design/         設計文件：系統架構、資料庫結構
├── acceptance/     驗收紀錄與測試回應
├── experiments/    實驗
├── report/         最終報告草稿（大綱、展示流程、AI 改動對照表、限制）
├── meetings/       會議紀錄
└── images/         筆記中的截圖，依筆記檔名分資料夾
```
