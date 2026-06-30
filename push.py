#!/usr/bin/env python3
"""
MarketPulse Telegram Bot
每次執行只推送「上次未見過」的新快訊
"""

import os, json, hashlib, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ── 設定 ──────────────────────────────────────────
BOT_TOKEN = os.environ["TG_BOT_TOKEN"]   # 從 GitHub Secret 讀取
CHAT_ID   = os.environ["TG_CHAT_ID"]     # 從 GitHub Secret 讀取
SEEN_FILE = "seen_ids.json"              # 記錄已推送過的新聞 ID

RSS_FEEDS = [
    ("Yahoo Finance",    "https://finance.yahoo.com/news/rssindex"),
    ("Yahoo US Markets", "https://finance.yahoo.com/rss/topstories"),
    ("MarketWatch",      "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
]

# 分類關鍵字
CATEGORIES = {
    "📊 業績":   ["earnings","revenue","profit","eps","quarter","guidance","beat","miss","results"],
    "🏦 聯儲局": ["fed","federal reserve","interest rate","inflation","fomc","powell","rate hike","rate cut"],
    "💻 科技":   ["apple","microsoft","google","amazon","meta","nvidia","ai","semiconductor","chip","openai"],
    "📈 市場":   ["dow","s&p","nasdaq","market","wall street","index","rally","selloff","bull","bear"],
    "₿ 加密":   ["bitcoin","ethereum","crypto","btc","eth","coinbase","blockchain"],
}

# ── 工具函數 ──────────────────────────────────────
def fetch_rss(url: str, source: str) -> list[dict]:
    """抓 RSS feed，返回新聞列表"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = []

        # RSS 2.0
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            guid  = (item.findtext("guid")  or link).strip()
            if title and link:
                items.append({"id": hashlib.md5(guid.encode()).hexdigest(),
                              "title": title, "link": link, "source": source})

        # Atom
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
            link_el = entry.find("atom:link", ns)
            link  = (link_el.get("href") if link_el is not None else "").strip()
            guid  = (entry.findtext("atom:id", namespaces=ns) or link).strip()
            if title and link:
                items.append({"id": hashlib.md5(guid.encode()).hexdigest(),
                              "title": title, "link": link, "source": source})
        return items

    except Exception as e:
        print(f"  ⚠️  {source} 抓取失敗：{e}")
        return []


def categorize(title: str) -> str:
    txt = title.lower()
    for cat, kws in CATEGORIES.items():
        if any(k in txt for k in kws):
            return cat
    return "📰 一般"


def load_seen() -> set:
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_seen(ids: set):
    # 只保留最新 500 條，避免檔案無限增長
    trimmed = list(ids)[-500:]
    with open(SEEN_FILE, "w") as f:
        json.dump(trimmed, f)


def translate_to_zh(text: str) -> str:
    """嘗試多個免費翻譯服務，將英文轉做繁體中文"""

    # 方案一：Google 翻譯（免費端口）
    try:
        url = ("https://translate.googleapis.com/translate_a/single"
               "?client=gtx&sl=en&tl=zh-TW&dt=t&q=" + urllib.parse.quote(text))
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        result = "".join(seg[0] for seg in data[0])
        if result and result.strip() != text.strip():
            return result
    except Exception as e:
        print(f"    ⚠️ Google翻譯失敗：{e}")

    # 方案二：MyMemory 翻譯（免費，無需key）
    try:
        url = ("https://api.mymemory.translated.net/get"
               "?q=" + urllib.parse.quote(text) + "&langpair=en|zh-TW")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        result = data.get("responseData", {}).get("translatedText", "")
        if result and result.strip() != text.strip():
            return result
    except Exception as e:
        print(f"    ⚠️ MyMemory翻譯失敗：{e}")

    print(f"    ⚠️ 所有翻譯方案都失敗，使用英文原文")
    return text


def send_telegram(text: str):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    body = json.dumps({
        "chat_id":    CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        resp = json.loads(r.read())
    if not resp.get("ok"):
        raise RuntimeError(f"Telegram 返回錯誤：{resp}")


def format_message(item: dict) -> str:
    cat = categorize(item["title"])
    title_zh = translate_to_zh(item["title"])
    return (
        f"{cat}  <b>{item['source']}</b>\n"
        f"{title_zh}\n"
        f"🔗 <a href=\"{item['link']}\">閱讀詳情</a>"
    )


# ── 主流程 ────────────────────────────────────────
def main():
    print(f"\n🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} 開始檢查快訊…\n")

    seen = load_seen()
    print(f"📂 已記錄 {len(seen)} 條歷史快訊\n")

    # 抓取所有 feed
    all_items = []
    for source, url in RSS_FEEDS:
        items = fetch_rss(url, source)
        print(f"  ✅ {source}：{len(items)} 條")
        all_items.extend(items)

    # 去重
    unique = {i["id"]: i for i in all_items}.values()

    # 篩出新快訊
    new_items = [i for i in unique if i["id"] not in seen]
    print(f"\n🆕 新快訊：{len(new_items)} 條（共 {len(list(unique))} 條）\n")

    if not new_items:
        print("✅ 沒有新快訊，不推送。")
        return

    # 推送（最多一次推 10 條，避免刷屏）
    to_push = list(new_items)[:10]
    pushed  = 0

    for item in to_push:
        try:
            msg = format_message(item)
            send_telegram(msg)
            seen.add(item["id"])
            pushed += 1
            print(f"  📤 已推送：{item['title'][:60]}…")
        except Exception as e:
            print(f"  ❌ 推送失敗：{e}")

    # 如果新快訊超過 10 條，加一條彙總提示
    remaining = len(new_items) - pushed
    if remaining > 0:
        try:
            send_telegram(f"📋 另有 <b>{remaining}</b> 條快訊，請到網頁版查看完整列表。")
        except Exception:
            pass

    save_seen(seen)
    print(f"\n✅ 完成，本次推送 {pushed} 條。")


if __name__ == "__main__":
    main()
