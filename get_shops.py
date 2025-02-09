from urllib.parse import urlparse
import random
import time
import datetime
import csv
from playwright.sync_api import sync_playwright

# Google search URL
GOOGLE_SEARCH_URL = "https://www.bing.com/search"

# List of technologies to search for
TECHNOLOGIES = [
    "Shopify",
    "WordPress",
    "WooCommerce",
    "Magento",
    "Lightspeed",
]

date_str = datetime.datetime.today().strftime("%Y-%m-%d")
data_file_str = f"data/leads_{date_str}.csv"

with open(data_file_str, "w") as data_file:
    data_file.write("product,website\n")


# Function to perform Google search
def google_search(page, product):
    product = product.replace(" ", "+").lower()

    search_url = f"{GOOGLE_SEARCH_URL}?q={product}+kopen"

    page_count = 0

    result = []

    # Search first 5 pages
    while page_count < 5:
        try:
            page_search_url = f"{search_url}&first={page_count * 10}"

            page.goto(page_search_url)
            page.wait_for_load_state("networkidle")

            # Get all search results
            websites = page.query_selector_all("div.tpmeta > div.b_attribution")

            for website in websites:
                website_text = website.inner_text()

                # Get all test before first white space
                website_text = website_text.split(" ")[0]

                # Parse URL to find origin
                parsed_url = urlparse(website_text)

                if not parsed_url.netloc.endswith(
                    ".nl"
                ) and not parsed_url.netloc.endswith(".com"):
                    continue

                if website_text in result:
                    continue

                result.append(website_text)

                with open(data_file_str, "a") as data_file:
                    data_file.write(f"{product},{website_text}\n")

            page_count += 1
        except Exception as e:
            print(f"Error: {e}")
            continue

    return list(set(result))


products = []

# Get kind of products
with open("producten.txt", "r") as file:
    for line in file:
        products.append(line.strip())

# Remove duplicates
products = list(set(products))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        locale="nl-NL",
    )
    page = context.new_page()

    for index, product in enumerate(products):
        print(f"Searching for {product}... ({index + 1} of {len(products)})")

        # Perform Google search
        links = google_search(page, product)

        # Random sleep to avoid being blocked
        time.sleep(random.uniform(2, 5))

    browser.close()
