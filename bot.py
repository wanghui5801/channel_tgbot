import time
import feedparser
import cloudscraper
import requests
import certifi

# ============== 需要你自行填写的部分 ==============
TELEGRAM_BOT_TOKEN = ""  # 你的 Telegram 机器人 Token
CHAT_ID = ""             # 你的目标群组ID或用户ID
# ==================================================

# 关键词（默认一些示例值）
KEYWORDS = [
    "ovh", "ksa", "ks-a", "杜甫", "独服", "cc", "cloudcone",
    "rn", "racknerd", "99刀", "斯巴达", "白丝云", "cloudsilk",
    "9929", "联通"
]

# 有关键词匹配需求的 RSS
RSS_FEED_URLS_WITH_KEYWORDS = {
    "https://rss.nodeseek.com/": "nodeseek",
    "https://hostloc.com/forum.php?mod=rss": "hostloc"
}

# 无关键词匹配需求的 RSS
RSS_FEED_URLS_NO_KEYWORDS = {
    "https://lowendtalk.com/categories/offers/feed.rss": "lowendtalk",
    "https://lowendspirit.com/categories/offers.rss": "lowendspirit"
}

# 所有可选的 RSS 源（字典格式：url -> name）
ALL_FEEDS = {**RSS_FEED_URLS_WITH_KEYWORDS, **RSS_FEED_URLS_NO_KEYWORDS}

# 当前正在监控的 feed（字典格式： name -> url ）
monitored_feeds = {
    "nodeseek": "https://rss.nodeseek.com/",
    "hostloc": "https://hostloc.com/forum.php?mod=rss",
    "lowendtalk": "https://lowendtalk.com/categories/offers/feed.rss",
    "lowendspirit": "https://lowendspirit.com/categories/offers.rss"
}

# 记录旧的链接，用于对比新帖子
old_entries = {}

# 记录 getUpdates offset，避免重复拉取
UPDATE_OFFSET = 0


def send_message_to_telegram(message, chat_id=CHAT_ID):
    """
    发送文本消息到 Telegram
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, data=data, verify=certifi.where())
        if resp.status_code != 200:
            print(f"Failed to send message. Status: {resp.status_code}, Resp: {resp.text}")
    except Exception as e:
        print(f"Error sending message: {e}")


def fetch_telegram_updates():
    """
    轮询拉取最新的 Telegram 消息更新
    """
    global UPDATE_OFFSET
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    # offset要比上次+1，这样不会拉到重复的
    params = {"offset": UPDATE_OFFSET + 1, "timeout": 5}
    try:
        resp = requests.get(url, params=params, timeout=10, verify=certifi.where())
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
    except Exception as e:
        print(f"Error fetching Telegram updates: {e}")
    return []


def handle_telegram_command(message_text, chat_id):
    """
    处理在群里/私聊发来的命令:
      /monitor list
      /monitor add <源名称>
      /monitor remove <源名称>

      /keyword list
      /keyword add <关键词>
      /keyword remove <关键词>
    """
    global monitored_feeds, KEYWORDS

    tokens = message_text.strip().split()
    if not tokens:
        return

    cmd = tokens[0].lower()

    # ========== /monitor 命令 ==========
    if cmd == "/monitor":
        if len(tokens) == 1:
            send_message_to_telegram(
                "用法：\n/monitor list\n/monitor add <源名称>\n/monitor remove <源名称>",
                chat_id
            )
            return

        sub_cmd = tokens[1].lower()
        if sub_cmd == "list":
            # 列出目前监控的 feed
            if monitored_feeds:
                feed_list = "\n".join([f"- {name}: {url}" for name, url in monitored_feeds.items()])
                send_message_to_telegram(f"当前监控的 RSS：\n{feed_list}", chat_id)
            else:
                send_message_to_telegram("当前没有监控任何 RSS。", chat_id)

        elif sub_cmd == "add":
            if len(tokens) < 3:
                send_message_to_telegram("用法：/monitor add <源名称>", chat_id)
                return
            feed_name = tokens[2].lower()
            # ALL_FEEDS 是 {url->name}，要反查 name->url
            name_to_url = {v: k for k, v in ALL_FEEDS.items()}
            if feed_name in name_to_url:
                if feed_name not in monitored_feeds:
                    monitored_feeds[feed_name] = name_to_url[feed_name]
                    send_message_to_telegram(f"已添加 {feed_name} 到监控列表。", chat_id)
                else:
                    send_message_to_telegram(f"{feed_name} 已在监控列表中。", chat_id)
            else:
                send_message_to_telegram(
                    f"未找到名为 {feed_name} 的 RSS 源。可选源：{list(name_to_url.keys())}",
                    chat_id
                )

        elif sub_cmd == "remove":
            if len(tokens) < 3:
                send_message_to_telegram("用法：/monitor remove <源名称>", chat_id)
                return
            feed_name = tokens[2].lower()
            if feed_name in monitored_feeds:
                monitored_feeds.pop(feed_name)
                send_message_to_telegram(f"已移除对 {feed_name} 的监控。", chat_id)
            else:
                send_message_to_telegram(f"当前未监控 {feed_name}。", chat_id)

    # ========== /keyword 命令 ==========
    elif cmd == "/keyword":
        if len(tokens) == 1:
            send_message_to_telegram(
                "用法：\n/keyword list\n/keyword add <关键词>\n/keyword remove <关键词>",
                chat_id
            )
            return

        sub_cmd = tokens[1].lower()
        if sub_cmd == "list":
            if KEYWORDS:
                kw_list = "\n".join([f"- {kw}" for kw in KEYWORDS])
                send_message_to_telegram(f"当前关键词列表：\n{kw_list}", chat_id)
            else:
                send_message_to_telegram("当前没有任何关键词。", chat_id)

        elif sub_cmd == "add":
            if len(tokens) < 3:
                send_message_to_telegram("用法：/keyword add <关键词>", chat_id)
                return
            new_kw = tokens[2]
            # 如果想忽略大小写，可以统一 lower
            if new_kw.lower() in [k.lower() for k in KEYWORDS]:
                send_message_to_telegram(f"关键词 '{new_kw}' 已存在。", chat_id)
            else:
                KEYWORDS.append(new_kw)
                send_message_to_telegram(f"已添加关键词：'{new_kw}'", chat_id)

        elif sub_cmd == "remove":
            if len(tokens) < 3:
                send_message_to_telegram("用法：/keyword remove <关键词>", chat_id)
                return
            remove_kw = tokens[2]
            found = False
            for k in KEYWORDS:
                if k.lower() == remove_kw.lower():
                    KEYWORDS.remove(k)
                    found = True
                    send_message_to_telegram(f"已移除关键词：'{remove_kw}'", chat_id)
                    break
            if not found:
                send_message_to_telegram(f"关键词 '{remove_kw}' 不在列表中。", chat_id)


def process_telegram_updates(updates):
    """
    遍历 updates 列表，识别命令并处理
    """
    global UPDATE_OFFSET
    for update in updates:
        update_id = update["update_id"]
        # 记录 offset，避免下次重复获取同样的 update
        UPDATE_OFFSET = update_id

        if "message" not in update:
            continue

        message = update["message"]
        chat_id = message.get("chat", {}).get("id", "")
        text = message.get("text", "")

        if not text or not chat_id:
            continue

        # 如果是 /xxx 命令，则进行处理
        if text.startswith("/"):
            handle_telegram_command(text, chat_id)


def fetch_rss_feeds(feed_dict):
    """
    给定 feed_dict (name->url)，抓取所有 RSS
    返回: {name: [(title, link, desc, author), ...], ...}
    """
    scraper = None
    result = {}
    try:
        # 创建cloudscraper实例
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False},
            delay=10
        )

        common_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        lowendtalk_headers = dict(common_headers)
        lowendtalk_headers["Accept"] = (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
            "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        )
        lowendtalk_headers["Referer"] = "https://www.google.com"

        for name, url in feed_dict.items():
            # lowendtalk 需要特殊 headers
            headers = lowendtalk_headers if name == "lowendtalk" else common_headers

            try:
                resp = scraper.get(url, headers=headers, timeout=20, verify=certifi.where())
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.content)
                    entries = []
                    if "entries" in feed and len(feed.entries) > 0:
                        for entry in feed.entries:
                            title = entry.get("title", "No Title")
                            link = entry.get("link", "No Link")
                            description = entry.get("summary", "")
                            author = entry.get("author") or entry.get("dc_creator", "No Author")
                            entries.append((title, link, description, author))
                    result[name] = entries
                    print(f"[RSS] Fetched '{name}' OK, {len(entries)} entries.")
                else:
                    print(f"[RSS] Failed to fetch '{name}', status = {resp.status_code}")
                    result[name] = []
                resp.close()
            except Exception as e:
                print(f"[RSS] Exception while fetching '{name}': {e}")
                result[name] = []
    finally:
        # 新版 cloudscraper 可能没有 session 属性，如有需要可直接 scraper.close()
        if scraper:
            try:
                scraper.close()
            except:
                pass

    return result


def check_new_posts(feed_data):
    """
    对比新旧数据，发送新帖消息。 feed_data: {name: [(title, link, desc, author), ...]}
    """
    global old_entries, KEYWORDS

    # 根据 RSS_FEED_URLS_WITH_KEYWORDS 构建 name->url 映射，用于判断当前 feed 是否需要关键词筛选
    name_to_url_with_kw = {v: k for k, v in RSS_FEED_URLS_WITH_KEYWORDS.items()}

    for feed_name, entries in feed_data.items():
        new_links = set(e[1] for e in entries)
        old_links = old_entries.get(feed_name, set())

        diff_links = new_links - old_links
        if diff_links:
            for title, link, desc, author in entries:
                if link in diff_links:
                    # 如果 feed_name 在有关键词需求的列表里，则匹配 KEYWORDS
                    if feed_name in name_to_url_with_kw:
                        lower_title = title.lower()
                        if any(keyword.lower() in lower_title for keyword in KEYWORDS):
                            send_new_post_message(feed_name, title, link, author)
                    else:
                        # 无关键词需求，直接发送
                        send_new_post_message(feed_name, title, link, author)

            # 更新 old_entries
            old_entries[feed_name] = new_links


def send_new_post_message(feed_name, title, link, author):
    """
    格式化并发送新增帖子的消息
    """
    msg = (
        "✨ <b>New Post Detected!</b> ✨\n"
        f"🌐 <b>Source:</b> {feed_name}\n"
        f"📜 <b>Title:</b> <a href='{link}'>{title}</a>\n"
        f"👤 <b>Author:</b> {author}"
    )
    print(f"[New Post] {feed_name} => {title}")
    send_message_to_telegram(msg)


def main_loop():
    """
    主循环:
      - 每次循环都立刻检查 Telegram 是否有新消息，如果有就立即处理命令
      - 每隔30秒才抓一次RSS并对比新帖子
      - sleep(1) 确保不会占用CPU太多
    """
    global old_entries

    # 先抓一次 RSS，初始化 old_entries
    initial_data = fetch_rss_feeds(monitored_feeds)
    old_entries = {
        fn: set(e[1] for e in edata) for fn, edata in initial_data.items()
    }

    print("Bot is running...")

    last_rss_check = 0
    rss_interval = 30  # 30秒一次抓取

    while True:
        # 1) 先处理命令
        updates = fetch_telegram_updates()
        if updates:
            process_telegram_updates(updates)

        # 2) 判断是否到达了抓取RSS的时间
        now = time.time()
        if now - last_rss_check >= rss_interval:
            new_data = fetch_rss_feeds(monitored_feeds)
            check_new_posts(new_data)
            last_rss_check = now

        # 3) 等1秒，再重复
        time.sleep(1)


if __name__ == "__main__":
    main_loop()
