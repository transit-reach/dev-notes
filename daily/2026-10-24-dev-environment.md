# 2026-10-24 開發環境建置與第一次呼叫 TDX API

## 今日目標

- [x] 提案加入產品定位與驗收標準
- [x] 建立 Ubuntu Server VM，從 VS Code Remote-SSH 連線
- [x] VM 設定 SSH key 連上 GitHub
- [x] 安裝 uv、Docker
- [x] 第一次呼叫 TDX API

## 1. 提案更新

在 [proposal.md](../proposal.md) 加入產品定位與驗收標準：

- **產品定位**：目標使用者、核心價值、不做什麼；用「四步驟拆解圖」與「產品定位地圖」說明和現有工具的差異。
- **驗收標準**：9 項，分為功能正確性、自然語言查詢、效能與部署三類，每項都有驗收方式與通過標準（待學長確認）。

## 2. 開發環境

| 項目 | 結果 |
| --- | --- |
| VM | VMware Workstation Pro，Ubuntu Server 24.04，4 核、8 GB 記憶體、40 GB 磁碟 |
| 連線 | Windows → SSH → VM；VS Code Remote-SSH 直接在 VM 上編輯與執行 |
| GitHub | VM 產生 ed25519 SSH key，`ssh -T git@github.com` 驗證成功 |
| Python | uv |
| 容器 | Docker（官方套件來源）、docker compose |

**決策：Ubuntu 選 Server 版**。開發時從 Windows 透過 SSH 連進 VM，用不到桌面；Server 版資源需求較低，也和實際部署的伺服器環境一致。

<!-- 貼上：VS Code Remote-SSH 連線畫面 -->

## 3. 踩坑紀錄

### 3-1. 安裝 Ubuntu 時，系統只分配到一半的磁碟

**問題**：虛擬磁碟設定 40 GB，但安裝程式預設只把一半分配給系統。

**原因**：Ubuntu Server 預設使用 LVM，只從磁碟池切出約一半給根目錄（`ubuntu-lv`），其餘保留未分配。

**行動**：在 Storage configuration 畫面把 `ubuntu-lv` 的大小改成最大值。

**驗證**：

```bash
$ df -h /
Filesystem                         Size  Used Avail Use% Mounted on
/dev/mapper/ubuntu--vg-ubuntu--lv   38G   ...
```

### 3-2. 加入 docker 群組後，執行 docker 仍然權限不足

**問題**：執行 `sudo usermod -aG docker $USER` 並重新連線後，仍然出現：

```
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

<!-- 貼上：permission denied 截圖 -->

**原因**：Linux 的群組權限在**登入時**才載入。使用 VS Code Remote-SSH 時，關掉視窗不會真的登出，VM 裡的 VS Code Server 繼續執行，新開的終端機沿用舊的身分，所以還沒有 docker 群組。

**診斷**：

```bash
groups              # 目前終端機的群組：沒有 docker
getent group docker # 系統紀錄：docker 群組裡已經有 scott
```

**解法**：F1 → `Remote-SSH: Kill VS Code Server on Host...` 關掉 VS Code Server，再重新連線。

**驗證**：`docker run hello-world` 不加 sudo 也能成功執行。

### 3-3. VS Code 滑鼠移到函式上，沒有顯示說明

**問題**：在 VM 上打開 Python 檔，滑鼠移到函式名稱上沒有任何提示，`import requests` 也找不到套件。

**原因**：Remote-SSH 的擴充套件分成本機與遠端兩邊，負責分析程式碼的 Python 擴充套件（Pylance）必須安裝在 **VM 上**；另外 VS Code 不知道這個專案要用 `.venv` 裡的 Python。

**解法**：

1. 擴充功能搜尋 Python → **Install in SSH: 192.168.254.129**
2. File → Open Folder 開啟專案資料夾
3. F1 → `Python: Select Interpreter` → 選 `./.venv/bin/python`

**驗證**：滑鼠移到函式上會顯示 docstring，移到 `requests.post` 上會顯示套件說明。

## 4. 學到的觀念

- **SSH 主機指紋**：第一次連線時記錄對方的指紋到 `known_hosts`，之後每次連線都會比對，防止連到冒充的機器。
- **SSH 公鑰與私鑰**：公鑰（`.pub`）交給 GitHub，私鑰留在 VM 上證明身分，私鑰絕不外流。
- **`apt update` 與 `apt upgrade`**：`update` 只更新套件清單，`upgrade` 才依清單安裝新版本，所以要先 update。
- **docker 群組**：加入 docker 群組等於擁有管理員層級的權限，在個人開發 VM 上可以，共用伺服器要謹慎。

## 5. 第一次呼叫 TDX API

在 VM 建立 `tdx-explore` 資料夾，用 uv 安裝 `requests`、`python-dotenv`，金鑰只放在 `.env`，並將 `.env`、`.venv/`、`data/` 加入 `.gitignore`。

取資料腳本以 AI 產生初版，再逐段確認每一行的用途與原理，並以實際執行結果驗證。目前已完成環境變數與 OAuth2 認證流程兩段，HTTP 請求、重試機制與存檔的部分明天繼續。

```bash
$ uv run tdx_fetch.py
取得 token 成功
抓台北市公車站序 ...
  已存 data/raw/bus_stop_of_route_taipei.json：1241 筆，20046 KB
抓台北捷運站序 ...
  已存 data/raw/metro_station_of_line_trtc.json：5 筆，32 KB
```

<!-- 貼上：執行結果截圖 -->

**觀察：為什麼台北市公車有 1241 筆？**

每一筆是「一個子路線的一個方向」的站序，不是一條路線：

- `Direction`：0 為去程、1 為返程，各一筆。
- `SubRoute`：同一個路線號碼底下，可能有區間車、繞駛等不同跑法，各自有站序。

**對資料庫設計的影響**：直達計算的單位應該是「子路線 ＋ 方向」，只有在同一個子路線、同一個方向上，站序才有意義。

## 明日計畫

- 讀完取資料腳本剩下的段落，並自己修改做練習
- 分析資料：實際算出路線數、子路線數，確認欄位內容
- 設計資料庫 schema
- 建立 `backend` repo
