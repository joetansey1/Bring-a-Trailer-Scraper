import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from influxdb_client import InfluxDBClient, Point, WriteOptions

# ✅ CONFIG
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "UR TOKEN HERE"
INFLUX_ORG = "localorg"
INFLUX_BUCKET = "GT350"
BASE_URL = "https://bringatrailer.com/search/?s=mustang+shelby+gt350&page={}"

print("✅ SCRIPT LOADED")

# ✅ Setup Influx client
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=WriteOptions(batch_size=1))

def start_browser():
    print("🌐 Starting headless browser")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

def scrape_gt350_links(driver):
    print("🔄 Scrolling through 'More' pages to load all GT350 listings")
    all_links = set()
    driver.get("https://bringatrailer.com/search/?s=mustang+shelby+gt350")

    for i in range(50):  # Hard limit to avoid infinite loop
        time.sleep(2)  # Let results load
        elems = driver.find_elements(By.TAG_NAME, "a")
        page_links = [e.get_attribute("href") for e in elems if e.get_attribute("href") and "/listing/" in e.get_attribute("href")]
        before = len(all_links)
        all_links.update(page_links)
        print(f"🔎 Click {i+1}: {len(page_links)} links found, total unique so far: {len(all_links)}")

        try:
            more_button = driver.find_element(By.CSS_SELECTOR, "a.load-more")
            driver.execute_script("arguments[0].scrollIntoView();", more_button)
            more_button.click()
        except Exception as e:
            print("✅ No more pages to load.")
            break

    return list(all_links)

def extract_listing_details(driver, url):
    driver.get(url)
    time.sleep(1)
    try:
        title = driver.find_element(By.TAG_NAME, "h1").text
    except:
        title = "unknown"

    try:
        page_source = driver.page_source
        price_match = re.search(r"\$([\d,]+)</strong>", page_source)
        price = int(price_match.group(1).replace(",", "")) if price_match else None
    except:
        price = None

    year_match = re.search(r"(20\d{2}|19\d{2})", title)
    year = int(year_match.group(1)) if year_match else None
    mileage_match = re.search(r"([\d,]+)-[Mm]ile", title)
    mileage = mileage_match.group(1).replace(",", "") if mileage_match else "N/A"

    return {
        "title": title,
        "year": year,
        "price": price,
        "mileage": mileage,
        "link": url,
        "sold_date": datetime.now().strftime("%Y-%m-%d"),
        "color": "unknown",
        "status": "completed",
        "source": "bringatrailer"
    }

def write_to_influx(**kwargs):
    if kwargs.get("price") is None:
        print(f"⚠️ Skipping Influx write for {kwargs['link']} — no price")
        return
    point = Point("gt350_listing")
    for key, value in kwargs.items():
        if isinstance(value, (int, float)):
            point.field(key, value)
        else:
            point.tag(key, str(value))
    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
    except Exception as e:
        print(f"❌ Influx write failed for {kwargs['link']}: {e}")

def scrape_all_gt350s():
    driver = start_browser()
    all_links = set()
    max_pages = 60  # Adjust if more than ~1440 results
    for page in range(1, max_pages + 1):
        if page == 1:
            url = "https://bringatrailer.com/search/?s=Mustang+GT350"
        elif page == 2:
            url = f"https://bringatrailer.com/search/page/{page}/?s=Mustang+GT350"
        else:
            url = f"https://bringatrailer.com/search/page/{page}/?s=Mustang+GT350&pagination_query=query_previous_auctions"

        print(f"📄 Loading page {page}: {url}")
        driver.get(url)
        time.sleep(2)  # Let listings load

        page_source = driver.page_source
        new_links = set(re.findall(r'href="(https://bringatrailer\.com/listing/[^"]+)"', page_source))
        added = len(new_links - all_links)
        print(f"✅ Page {page}: {len(new_links)} total found, {added} new")

        if added == 0:
            print("🛑 No new listings found — stopping pagination.")
            break

        all_links.update(new_links)

    print(f"📦 Total unique listings found: {len(all_links)}")

    count = 0
    for link in all_links:
        print(f"🔗 Visiting {link}")
        try:
            data = extract_listing_details(driver, link)
            if not (2015 <= data["year"] <= 2020):
                print(f"⏭️ Skipping {data['title']} — year {data['year']} out of range")
                continue
            print(f"✅ {data['title']} — ${data['price']} — {data['mileage']} mi")
            write_to_influx(**data)
            count += 1
        except Exception as e:
            print(f"❌ Error scraping {link}: {e}")

    print(f"✅ Inserted {count} completed GT350 listings.")
    driver.quit()

def main():
    print("🚀 Inside main()")
    scrape_all_gt350s()

if __name__ == "__main__":
    main()
