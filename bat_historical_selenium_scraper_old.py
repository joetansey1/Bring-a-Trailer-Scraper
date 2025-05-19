import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from influxdb_client import InfluxDBClient, Point, WritePrecision

BASE_URL = "https://bringatrailer.com/search/?s=mustang+shelby+gt350&page={}"
ORG = "localorg"
BUCKET = "GT350"
TOKEN = "erfvQYLBhrERH9bu8ORZzBRbfQ4GuEM8_f4MYCvVeMJhe38F-K2hZf0C0aNj4MPhk-GyRxufLNRzNrAs0h8gjg=="
INFLUX_URL = "http://localhost:8086"

# Setup InfluxDB client
client = InfluxDBClient(url=INFLUX_URL, token=TOKEN, org=ORG)
from influxdb_client.client.write_api import SYNCHRONOUS
write_api = client.write_api(write_options=SYNCHRONOUS)

def start_browser():
    options = Options()
    options.binary_location = "/usr/bin/chromium"  # or "/usr/bin/chromium-browser"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver_path = "/usr/bin/chromedriver"  # your chromedriver path
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service, options=options)
    return driver
def scrape_gt350_links(driver, page):
    listings = []
    try:
        # Wait for listing containers to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.listing"))
        )
    except:
        print("Timeout waiting for listings to load.")
        return []

    listing_elements = driver.find_elements(By.CSS_SELECTOR, "div.listing")
    for element in listing_elements:
        try:
            # Find the link inside the listing
            link_elem = element.find_element(By.CSS_SELECTOR, "a.current-auction-link")
            url = link_elem.get_attribute("href")
            # Get the title
            title_elem = element.find_element(By.CSS_SELECTOR, "h1.post-title.listing-post-title")
            title = title_elem.text.strip()

            # Extract bid amount text
            bid_elem = element.find_element(By.CSS_SELECTOR, "span.info-value.noborder-tiny")
            bid_text = bid_elem.text.strip()

            # Extract numerical bid using regex
            import re
            match = re.search(r'\$([\d,]+)', bid_text)
            if match:
                price_str = match.group(1).replace(',', '')
                price = int(price_str)
            else:
                price = None  # Or 0 if preferred

            # Append dict
            listings.append({
                'title': title,
                'url': url,
                'price': price
            })

        except Exception as e:
            print(f"Error extracting one listing: {e}")
    return listings

def write_to_influx(data):
    point = Point("gt350_listing")
    for k, v in data.items():
        if isinstance(v, (int, float)):
            point.field(k, float(v))
        else:
            point.tag(k, str(v))
    point.time(datetime.utcnow(), WritePrecision.NS)
    write_api.write(bucket=BUCKET, org=ORG, record=point)

def scrape_all_gt350s():
    driver = start_browser()
    print("Starting Selenium-based GT350 scraper...")
    all_links = set()
    page = 1

    while True:
        links = scrape_gt350_links(driver, page)
        if not links:
            print("No listings found on page {} — stopping.".format(page))
            break
        new_links = set(links) - all_links
        if not new_links:
            print("DEBUG: All {} unique links collected so far (added 0)".format(len(all_links)))
            break
        print("DEBUG: All {} unique links collected so far (added {})".format(len(all_links) + len(new_links), len(new_links)))
        all_links.update(new_links)
        page += 1

    print("Total unique listings found:", len(all_links))
    inserted = 0
    for link in all_links:
        try:
            driver.get(link)
            time.sleep(1.5)
            title_elem = driver.find_element(By.TAG_NAME, "h1")
            title = title_elem.text.strip()
            sold_elem = driver.find_element(By.CSS_SELECTOR, "strong:contains('USD')")
            price = int(sold_elem.text.replace("USD $", "").replace(",", ""))
            data = {
                "title": title,
                "price": price,
                "link": link,
                "source": "bringatrailer",
                "status": "completed"
            }
            write_to_influx(data)
            inserted += 1
        except Exception as e:
            print(f"Failed to process {link}: {e}")

    print(f"Inserted {inserted} completed GT350 listings.")
    driver.quit()

if __name__ == "__main__":
    print("SCRIPT LOADED")
    scrape_all_gt350s()
