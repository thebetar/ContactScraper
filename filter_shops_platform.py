import datetime
import csv
import requests
import pandas as pd

# List of technologies to search for
TECHNOLOGIES = [
    "Shopify",
    "WooCommerce",
    "Magento",
    "Lightspeed",
    "WordPress",
]


def filter_shops_platform():
    date_str = datetime.datetime.today().strftime("%Y-%m-%d")
    data_file_str = f"data/shops_{date_str}.csv"

    with open(data_file_str, "w") as f:
        f.write("product,company,website,technology\n")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }

    def check_shops(websites):
        result = []

        for website in websites:
            try:
                product = website["product"]
                company = website["company"]
                website_url = website["website"]

                # Get HTML from website
                response = requests.get(website_url, headers=headers, timeout=5)

                # Check if website is online
                if response.status_code != 200:
                    continue

                # Check if website is of one of the technologies
                for technology in TECHNOLOGIES:
                    if not technology.lower() in response.text.lower():
                        continue

                    result.append(
                        {
                            "product": product,
                            "company": company,
                            "website": website_url,
                            "technology": technology,
                        }
                    )

                    with open(data_file_str, "a") as f:
                        f.write(f"{product},{company},{website_url},{technology}\n")

                    print(f"Found {technology} on {website_url} ({len(result)})")
                    break
            except Exception as e:
                print(f"Error: {e}")
                continue

        return result

    # Load shops from daily leads list
    leads_file_str = f"data/leads_{date_str}.csv"
    leads = csv.DictReader(open(leads_file_str))

    print(f"Filtering initial leads by platform...")

    # Filter shops
    check_shops(leads)


if __name__ == "__main__":
    filter_shops_platform()
