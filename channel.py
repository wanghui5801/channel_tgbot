import time
import feedparser
import cloudscraper
import requests

# Telegram bot info
TELEGRAM_BOT_TOKEN = ""
CHAT_ID = ""

# Only match the keywords "sell" and "buy" for Hostloc title detection
HOSTLOC_KEYWORDS = ["出", "收"]

RSS_FEEDS = {
    "https://rss.nodeseek.com/": "nodeseek",
    "https://hostloc.com/forum.php?mod=rss": "hostloc"
}


def send_message_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, data=data)
        if resp.status_code != 200:
            print(f"Failed to send message to Telegram. Status code: {resp.status_code}, Response: {resp.text}")
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")


def fetch_rss_feeds(feed_dict):
    # Create a cloudscraper instance
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False},
        delay=10
    )

    common_headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/115.0.0.0 Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    result = {}
    for url, name in feed_dict.items():
        headers = common_headers
        try:
            response = scraper.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if 'entries' in feed and len(feed.entries) > 0:
                    entries = []
                    for entry in feed.entries:
                        title = entry.get('title', 'No Title')
                        link = entry.get('link', 'No Link')
                        description = entry.get('summary', '')
                        author = entry.get('author')
                        if not author:
                            author = entry.get('dc_creator', 'No Author')

                        # Get category information
                        category = entry.get('category', '').strip().lower()

                        entries.append((title, link, description, author, category))
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
    # Initial RSS fetch
    old_data = fetch_rss_feeds(RSS_FEEDS)
    old_entries = {}
    for feed_name, entries in old_data.items():
        old_entries[feed_name] = set(link for _, link, _, _, _ in entries)

    print("Starting RSS monitoring...")
    # Check for updates every 30 seconds
    while True:
        time.sleep(30)
        new_data = fetch_rss_feeds(RSS_FEEDS)

        for feed_name, entries in new_data.items():
            new_links = set(link for _, link, _, _, _ in entries)
            old_links = old_entries.get(feed_name, set())
            diff_links = new_links - old_links

            if diff_links:
                # New posts detected
                for title, link, description, author, category in entries:
                    if link in diff_links:
                        if feed_name == "nodeseek":
                            # Only posts in the "trade" category
                            if category == "trade":
                                message = (
                                    "🚀 <b>NodeSeek New Trade Post!</b>\n"
                                    f"🎉 <b>Title:</b> <a href='{link}'>{title}</a>\n"
                                    f"👤 <b>Author:</b> {author}"
                                )
                                print(f"New trade category post detected on nodeseek: {title}")
                                send_message_to_telegram(message)

                        elif feed_name == "hostloc":
                            # Titles containing "sell" or "buy"
                            title_text = title.lower()
                            if any(kw in title_text for kw in HOSTLOC_KEYWORDS):
                                message = (
                                    "📢 <b>Hostloc Matched Post!</b>\n"
                                    f"🔎 <b>Title:</b> <a href='{link}'>{title}</a>\n"
                                    f"👤 <b>Author:</b> {author}"
                                )
                                print(f"New matched keyword post detected on hostloc: {title}")
                                send_message_to_telegram(message)

                old_entries[feed_name] = new_links


if __name__ == '__main__':
    main_loop()
