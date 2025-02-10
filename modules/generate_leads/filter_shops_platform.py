import datetime
import csv
import requests
import os

# List of technologies to search for
TECHNOLOGIES = [
    "Shopify",
    "WooCommerce",
    "Magento",
    "Lightspeed",
    # "WordPress",
]


def get_leads():
    leads = []
    filtered_leads = []

    # Get all leads
    files = os.listdir("data")

    # Get all leads
    for file in files:
        if file.startswith("leads_"):
            file_leads = csv.DictReader(open(f"data/{file}"))

            for row in file_leads:
                leads.append(row)

    if os.path.exists("data/history/filtered_shops.txt"):
        # Get all filtered shops
        with open("data/history/filtered_shops.txt", "r") as f:
            for line in f:
                filtered_leads.append(line.strip())

    # Remove filtered shops from leads
    leads = [lead for lead in leads if not lead["website"] in filtered_leads]

    return leads


def filter_shops_platform():
    # Create log file if it does not exist
    if not os.path.exists("data/history/filtered_shops.txt"):
        with open("data/history/filtered_shops.txt", "w") as f:
            f.write("")

    # Create data file if it does not exist
    date_str = datetime.datetime.today().strftime("%Y-%m-%d")
    data_file_str = f"data/leads_{date_str}.csv"

    # If file exists no need to write header
    if not os.path.exists(data_file_str):
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

                # Record that this website has been checked
                with open("data/history/filtered_shops.txt", "a") as f:
                    f.write(f"{website_url}\n")
            except Exception as e:
                print(f"Error: {e}")
                continue

        return result

    # Load shops from daily leads list
    leads = get_leads()

    print(f"Filtering initial leads by platform...")

    # Filter shops
    check_shops(leads)


if __name__ == "__main__":
    filter_shops_platform()
