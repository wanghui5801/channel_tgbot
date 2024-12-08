import time
import feedparser
import cloudscraper
import requests
import certifi

# Telegram bot info
TELEGRAM_BOT_TOKEN = ""
CHAT_ID = ""

# Keywords list
KEYWORDS = ["ovh", "ksa", "ks-a", "杜甫", "独服", "cc", "cloudcone", "rn", "racknerd", "99刀", "斯巴达","白丝云","cloudsilk","9929", "联通"]  

# RSS feeds with keyword matching
RSS_FEED_URLS_WITH_KEYWORDS = {
    "https://rss.nodeseek.com/": "nodeseek",
    "https://hostloc.com/forum.php?mod=rss": "hostloc"
}

# RSS feeds without keyword matching
RSS_FEED_URLS_NO_KEYWORDS = {
    "https://lowendtalk.com/categories/offers/feed.rss": "lowendtalk",
    "https://lowendspirit.com/categories/offers.rss": "lowendspirit"
}

ALL_FEEDS = {**RSS_FEED_URLS_WITH_KEYWORDS, **RSS_FEED_URLS_NO_KEYWORDS}


def send_message_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, data=data, verify=certifi.where())
        if resp.status_code != 200:
            print(f"Failed to send message to Telegram. Status code: {resp.status_code}, Response: {resp.text}")
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")


def fetch_rss_feeds(feed_dict):
    # Create a cloudscraper instance to bypass some restrictions
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False},
        delay=10
    )

    # Common headers
    common_headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/115.0.0.0 Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    # Special headers for lowendtalk
    lowendtalk_headers = dict(common_headers)
    lowendtalk_headers["Accept"] = ("text/html,application/xhtml+xml,application/xml;"
                                    "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
                                    "application/signed-exchange;v=b3;q=0.7")
    lowendtalk_headers["Referer"] = "https://www.google.com"

    result = {}
    for url, name in feed_dict.items():
        headers = common_headers
        if name == "lowendtalk":
            headers = lowendtalk_headers

        try:
            # 使用 verify 参数指定 certifi 的证书
            response = scraper.get(url, headers=headers, timeout=20, verify=certifi.where())
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if 'entries' in feed and len(feed.entries) > 0:
                    entries = []
                    for entry in feed.entries:
                        title = entry.get('title', 'No Title')
                        link = entry.get('link', 'No Link')
                        description = entry.get('summary', '')

                        # Try to get author or dc:creator
                        author = entry.get('author')
                        if not author:
                            author = entry.get('dc_creator', 'No Author')

                        entries.append((title, link, description, author))
                    result[name] = entries
                    print(f"Successfully fetched RSS feed for {name}: {url}")
                else:
                    print(f"Successfully fetched {name} but no RSS entries found: {url}")
                    result[name] = []
            else:
                print(f"Failed to fetch RSS feed for {name}: {url}, Status code: {response.status_code}")
                result[name] = []
        except Exception as e:
            print(f"Exception occurred while fetching {name} RSS feed: {url}, Error: {e}")
            result[name] = []
    return result


def main_loop():
    # Initial fetch
    old_data = fetch_rss_feeds(ALL_FEEDS)
    old_entries = {}
    for feed_name, entries in old_data.items():
        old_entries[feed_name] = set(link for _, link, _, _ in entries)

    print("Starting RSS monitoring...")
    # Check every 30 seconds
    while True:
        time.sleep(30)
        new_data = fetch_rss_feeds(ALL_FEEDS)

        for feed_name, entries in new_data.items():
            new_links = set(link for _, link, _, _ in entries)
            old_links = old_entries.get(feed_name, set())
            diff_links = new_links - old_links

            if diff_links:
                # New post(s) detected
                for title, link, description, author in entries:
                    if link in diff_links:
                        title_text = title.lower()

                        # Check if feed_name is one of the keyword-matching feeds
                        # feed_name should match values in RSS_FEED_URLS_WITH_KEYWORDS
                        if feed_name in RSS_FEED_URLS_WITH_KEYWORDS.values():
                            if any(keyword.lower() in title_text for keyword in KEYWORDS):
                                message = (
                                    "✨ <b>New Post Detected!</b> ✨\n"
                                    f"🌐 <b>Source:</b> {feed_name}\n"
                                    f"📜 <b>Title:</b> <a href='{link}'>{title}</a>\n"
                                    f"👤 <b>Author:</b> {author}"
                                )
                                print(f"New post (matches keyword in title) detected: {title} from {feed_name}")
                                send_message_to_telegram(message)
                        else:
                            # No keyword check needed
                            message = (
                                "✨ <b>New Post Detected!</b> ✨\n"
                                f"🌐 <b>Source:</b> {feed_name}\n"
                                f"📜 <b>Title:</b> <a href='{link}'>{title}</a>\n"
                                f"👤 <b>Author:</b> {author}"
                            )
                            print(f"New post detected: {title} from {feed_name}")
                            send_message_to_telegram(message)

                old_entries[feed_name] = new_links


if __name__ == '__main__':
    main_loop()
