# MarketPulse — Telegram 美股快訊推送

自動抓取 Yahoo Finance / MarketWatch 等財經 RSS，有新快訊即時推送到你的 Telegram。
完全免費，靠 GitHub Actions 運行，唔需要自己開電腦或伺服器。

---

## 設置步驟（約 10 分鐘）

### 第一步：建立 Telegram Bot

1. 打開 Telegram，搜尋 **@BotFather**
2. 傳送 `/newbot`
3. 跟指示設置 Bot 名稱和 username
4. BotFather 會給你一個 **Bot Token**（格式：`7123456789:AAF_xxxx`）→ **記錄下來**

### 第二步：取得你的 Chat ID

1. 先傳訊息給你剛建立的 Bot（搜尋 username，按 Start）
2. 瀏覽器打開：
   ```
   https://api.telegram.org/bot你的TOKEN/getUpdates
   ```
3. 在結果裡找 `"id"` 那個數字（例如 `123456789`）→ **記錄下來**

### 第三步：建立 GitHub Repository

1. 去 [github.com](https://github.com) 登入（沒有帳號免費註冊）
2. 按右上角 **+** → **New repository**
3. Repository name：`market-push`
4. 設為 **Private**（推薦）
5. 按 **Create repository**

### 第四步：上傳檔案

把這個資料夾裡的所有檔案上傳到你的 repo：
- `push.py`
- `.github/workflows/push.yml`
- `README.md`

**方法 A（網頁上傳）：**
- 在 repo 頁面按 `Add file` → `Upload files`
- 注意：`.github/workflows/push.yml` 要先建立 `.github/workflows/` 資料夾
  - 按 `Add file` → `Create new file`
  - 檔案名輸入：`.github/workflows/push.yml`
  - 貼上 push.yml 的內容

**方法 B（用 Git）：**
```bash
git clone https://github.com/你的用戶名/market-push.git
# 把所有檔案複製進去
git add .
git commit -m "init"
git push
```

### 第五步：設置 Secrets（最重要！）

1. 在你的 repo 頁面，按頂部 **Settings**
2. 左邊側欄找 **Secrets and variables** → **Actions**
3. 按 **New repository secret**，加入以下兩個：

| Name | Value |
|------|-------|
| `TG_BOT_TOKEN` | 你在第一步取得的 Bot Token |
| `TG_CHAT_ID` | 你在第二步取得的 Chat ID |

### 第六步：測試

1. 在 repo 頁面按頂部 **Actions**
2. 左邊找 **MarketPulse Telegram Push**
3. 按 **Run workflow** → **Run workflow**
4. 等約 30 秒，你的 Telegram 應該收到第一批快訊！

---

## 推送頻率

| 時段 | 頻率 |
|------|------|
| 週一至五 美股交易時段（港時 21:30–04:00） | 每 15 分鐘 |
| 週一至五 非交易時段 | 每 30 分鐘 |
| 週末 | 每 1 小時 |

---

## 自訂設置

編輯 `push.py` 頂部的設定：

```python
# 修改 RSS 來源
RSS_FEEDS = [
    ("Yahoo Finance",    "https://finance.yahoo.com/news/rssindex"),
    ("MarketWatch",      "https://feeds.marketwatch.com/marketwatch/topstories/"),
    # 可以加更多...
]
```

---

## 常見問題

**Q：收不到訊息？**
- 確認已傳過訊息給 Bot（必須先 /start）
- 確認 Secrets 名稱正確（區分大小寫）
- 在 Actions 頁面查看執行 log

**Q：收到太多訊息？**
- 修改 `push.yml` 裡的 cron 時間，改長間隔
- 修改 `push.py` 裡 `to_push = list(new_items)[:10]` 的數字

**Q：GitHub Actions 免費額度？**
- 免費帳號每月 2000 分鐘，此腳本每次約 30 秒，完全夠用
