import datetime
import re
import csv
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

EMAIL_REGEX = r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"
PHONE_REGEX = r"^((\+|00(\s|\s?\-\s?)?)31(\s|\s?\-\s?)?(\(0\)[\-\s]?)?|0)[1-9]((\s|\s?\-\s?)?[0-9])((\s|\s?-\s?)?[0-9])((\s|\s?-\s?)?[0-9])\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]$"

CONTACT_SUBSTRINGS = [
    "contact",
    "about",
    "team",
    "support",
    "faq",
    "help",
    "getintouch",
    "get-in-touch",
    "klantenservice",
    "press",
    "terms",
]


date_str = datetime.datetime.today().strftime("%Y-%m-%d")
email_file_str = f"data/email_{date_str}.csv"
phone_file_str = f"data/phone_{date_str}.csv"


with open(email_file_str, "w") as data_file:
    data_file.write("company,site,page,email\n")

with open(phone_file_str, "w") as data_file:
    data_file.write("company,site,page,phone\n")


def check_break_condition(total_emails, total_phone, base_url):
    parsed_url = urlparse(base_url)
    domain = parsed_url.netloc

    # Filter by emails with domain name
    domain_emails = [email for email in total_emails if domain in email]

    return len(domain_emails) > 12 and len(total_phone) > 6


def scrape_website(page, website_url, company_name):
    start_url = website_url
    company = company_name

    # Remove https from URL
    start_url = start_url.replace("https://", "")
    start_url = start_url.replace("http://", "")

    depth = 0
    pages_scanned = 0

    sites_to_scrape = [start_url]
    total_emails = []
    total_phone = []

    scrape_history = []

    while depth < 3:
        # Find all the links on the page
        new_sites = []

        # For all pages at depth
        for site in sites_to_scrape:
            scrape_history.append(site)

            # If navigated to different website, skip
            if not start_url in site:
                continue

            # Playwright needs URL with http or https
            if not site.startswith("http"):
                site = "https://" + site

            # After 20 pages scanned check more strictly
            if pages_scanned > 20:
                # Check URL more strictly to be contact page
                parsed_url = urlparse(site)
                path = parsed_url.path

                # If URL does not contain any contact substrings, skip
                if (
                    not any([substr in path for substr in CONTACT_SUBSTRINGS])
                    or "stopcontact" in path.lower()
                ):
                    continue

            print(f"[{company}] Scraping {site} at depth {depth}")
            print(
                f"[{company}] Found {len(total_emails)} emails and {len(total_phone)} phone numbers"
            )

            try:
                page.goto(site)
                page.wait_for_load_state("networkidle")

                pages_scanned += 1

                links = page.query_selector_all("a")

                # For all links on the page
                for link in links:
                    href = link.get_attribute("href")

                    if (
                        not href
                        or href == "#"
                        or href == "/"
                        or href == "javascript:void(0)"
                        or "mailto:" in href
                    ):
                        continue

                    # If absolute path
                    if href.startswith("http"):
                        if href in scrape_history:
                            continue

                        new_sites.append(href)
                    # If relative path
                    else:
                        new_site = start_url + href

                        # Remove double slashes
                        new_site = new_site.replace("//", "/").replace(
                            "https:/", "https://"
                        )

                        if new_site in scrape_history:
                            continue

                        new_sites.append(new_site)

                # Find all emails
                text = page.inner_text("body")

                emails = re.findall(EMAIL_REGEX, text)

                # Filter out duplicates
                emails = list(set(emails))

                for email in emails:
                    if email in total_emails:
                        continue

                    total_emails.append(email)

                    with open(email_file_str, "a") as data_file:
                        data_file.write(f"{company},{start_url},{site},{email}\n")

                # Find all Dutch phone numbers
                phone_numbers = re.findall(PHONE_REGEX, text)

                # Filter out duplicates
                phone_numbers = list(set(phone_numbers))

                for phone in phone_numbers:
                    if phone in total_phone:
                        continue

                    total_phone.append(phone)

                    with open(phone_file_str, "a") as data_file:
                        data_file.write(f"{company},{start_url},{site},{phone}\n")

                # If total emails and phone numbers are more than 100, stop scraping
                if check_break_condition(total_emails, total_phone, start_url):
                    break
            except Exception as e:
                continue

        sites_to_scrape = list(set(new_sites))

        # If total emails and phone numbers are more than 100, stop scraping
        if check_break_condition(total_emails, total_phone, start_url):
            break

        depth += 1


if __name__ == "__main__":
    companies = csv.DictReader(open("data/lead-list.csv"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            locale="nl-NL",
        )
        page = browser.new_page()

        for index, company in enumerate(companies):
            company_name = company["Company"]
            website_url = company["Website"]

            scrape_website(page, website_url, company_name)

            print(f"[{company_name}] Done! ({index + 1})")

    print("Done!")
