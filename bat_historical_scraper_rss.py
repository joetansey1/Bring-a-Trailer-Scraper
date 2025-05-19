import cloudscraper
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from influx_writer import write_to_influx

scraper = cloudscraper.create_scraper()
RSS_FEED_URL = "https://bringatrailer.com/search/?s=gt350&feed=rss2"

KNOWN_COLORS = [
    "white", "black", "red", "blue", "gray", "grey", "green",
    "silver", "orange", "magnetic", "yellow", "oxford"
]

def guess_color(text):
    text = text.lower()
    for color in KNOWN_COLORS:
        if color in text:
            return color
    return "unknown"

def get_listing_details(url):
    print(f"→ Visiting {url}")
    res = scraper.get(url)
    if res.status_code != 200:
        print(f"❌ Failed to fetch {url}")
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    # ✅ Updated price selector
    price_tag = soup.select_one("div.auction-result .price")
    if not price_tag:
        return None

    price_text = price_tag.text.strip().replace("$", "").replace(",", "")
    price = int(price_text) if price_text.isdigit() else None

    # ✅ Updated title selector
    title_tag = soup.select_one("h1.hero-title")
    title = title_tag.text.strip() if title_tag else "Unknown"

    # ✅ Updated close date selector
    date_tag = soup.select_one("div.auction-meta time")
    close_date = datetime.fromisoformat(date_tag["datetime"]) if date_tag else datetime.utcnow()

    # ✅ Mileage via fuzzy regex
    mileage = None
    match = re.search(r"([\d,]+)\s+miles", soup.text)
    if match:
        mileage = int(match.group(1).replace(",", ""))

    # ✅ Year detection
    year = None
    match = re.search(r"\b(201[5-9]|2020)\b", title)
    if match:
        year = match.group(0)

    if not year or int(year) < 2015 or int(year) > 2020:
        return None

    color = guess_color(title)

    return {
        "price": price,
        "year": year,
        "mileage": mileage,
        "color": color,
        "date": close_date,
        "title": title
    }

def scrape_rss_feed():
    print("📡 Fetching BaT RSS feed for GT350s...")
    res = scraper.get(RSS_FEED_URL)
    if res.status_code != 200:
        print(f"❌ Failed to fetch RSS feed — HTTP {res.status_code}")
        return

    root = ET.fromstring(res.text)

    count = 0
    for item in root.findall("./channel/item"):
        link = item.find("link").text
        listing = get_listing_details(link)
        if not listing:
            continue

        write_to_influx(
            source="bringatrailer",
            year=listing["year"],
            price=listing["price"],
            mileage=listing["mileage"],
            color=listing["color"],
            link=link,
            time=listing["date"],
            status="completed"
        )

        print(f"✓ {listing['title']} — {listing['mileage'] or 'N/A'} mi — {listing['color']} — ${listing['price']} — {listing['date'].date()}")
        count += 1

    print(f"✅ Done. Inserted {count} completed GT350 listings.")

if __name__ == "__main__":
    scrape_rss_feed()
