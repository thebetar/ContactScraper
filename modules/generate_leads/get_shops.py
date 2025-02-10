from urllib.parse import urlparse
import random
import time
import datetime
import os
from playwright.sync_api import sync_playwright

# Google search URL
GOOGLE_SEARCH_URL = "https://www.bing.com/search"

FORBIDDEN_SHOPS = [
    "bol.com",
    "amazon.nl",
    "coolblue.nl",
    "mediamarkt.nl",
    "marktplaats.nl",
    "store.steampowered.com",
    "beslist.nl",
    "google.com",
    "ebay.nl",
]


def get_product_list():
    products = []

    # Get kind of products
    with open("modules/generate_leads/products.txt", "r") as file:
        for line in file:
            products.append(line.strip())

    # Remove duplicates
    products = list(set(products))

    if os.path.exists("data/history/queried_products.txt"):
        # Get already queried products
        with open("data/history/queried_products.txt", "r") as f:
            queried_products = [line.strip() for line in f]

        # Remove queried products
        products = [product for product in products if product not in queried_products]

    return products


def get_shops():
    date_str = datetime.datetime.today().strftime("%Y-%m-%d")
    data_file_str = f"data/shops_{date_str}.csv"

    # If file does not exist, create it
    if not os.path.exists(data_file_str):
        with open(data_file_str, "w") as data_file:
            data_file.write("product,company,website\n")

    # History to prevent double entries
    website_url_history = []

    # Function to perform Google search
    def google_search(page, product):
        product = product.replace(" ", "+").lower()

        search_url = f"{GOOGLE_SEARCH_URL}?q={product}+kopen"

        page_count = 0

        result = []

        # Search first 6 pages
        while page_count < 6:
            try:
                page_search_url = f"{search_url}&first={page_count * 10}"

                page.goto(page_search_url)
                page.wait_for_load_state("networkidle")

                # Get all search results
                websites = page.query_selector_all("a.tilk > div.tptxt")

                for website in websites:
                    website_url = website.query_selector(
                        "div.tpmeta > div.b_attribution"
                    )
                    website_name = website.query_selector("div.tptt")

                    website_url_text = website_url.inner_text()
                    website_name_text = website_name.inner_text()

                    # Get all test before first white space
                    website_url_text = website_url_text.split(" ")[0]

                    # Parse URL to find origin
                    parsed_url = urlparse(website_url_text)

                    # Check if URL is forbidden
                    if parsed_url.netloc.replace("www.", "") in FORBIDDEN_SHOPS:
                        continue

                    # Check if URL is not .nl or .com
                    if not parsed_url.netloc.endswith(
                        ".nl"
                    ) and not parsed_url.netloc.endswith(".com"):
                        continue

                    # Check if URL was found already to prevent doubles
                    if website_url_text in website_url_history:
                        continue

                    # Store website as result to prevent double entries
                    website_url_history.append(website_url_text)

                    # Append to result
                    result.append(
                        {
                            "product": product,
                            "company": website_name_text,
                            "website": website_url_text,
                        }
                    )

                    # Write row for intermediary results
                    with open(data_file_str, "a") as data_file:
                        data_file.write(
                            f"{product},{website_name_text},{website_url_text}\n"
                        )

                # Increase page count (step in bing search)
                page_count += 1
            except Exception as e:
                print(f"Error: {e}")
                continue

        # Write all found shops to history to prevent double searching
        with open("data/history/queried_products.txt", "a") as f:
            f.write(f"{product}\n")

        return result

    # Get all products
    products = get_product_list()

    # Start Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            locale="nl-NL",
        )
        page = context.new_page()

        # Iterate over all products
        for index, product in enumerate(products):
            # Print current product
            print(f"Searching for {product}... ({index + 1} of {len(products)})")

            # Perform Google search
            google_search(page, product)

            # Random sleep to avoid being blocked
            time.sleep(random.uniform(2, 5))

        browser.close()


if __name__ == "__main__":
    get_shops()
