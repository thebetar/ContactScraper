import re
import os
import csv
import datetime
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

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

if not os.path.exists(email_file_str):
    with open(email_file_str, "w") as data_file:
        data_file.write("company,site,page,email\n")

if not os.path.exists(phone_file_str):
    with open(phone_file_str, "w") as data_file:
        data_file.write("company,site,page,phone\n")


def log_status(company, message, pages_scanned, depth=0):
    print(f"[{company}] {message} ({pages_scanned} pages scanned at depth {depth})")


def get_companies():
    files = os.listdir("data")

    companies = []

    for file in files:
        if not file.startswith("leads_"):
            continue

        with open(f"data/{file}", "r") as f:
            reader = csv.DictReader(f)

            for row in reader:
                companies.append(row)

    if os.path.exists("data/history/enriched_leads.txt"):
        with open("data/history/enriched_leads.txt", "r") as f:
            enriched_leads = [line.strip() for line in f]

        companies = [
            company for company in companies if company["company"] not in enriched_leads
        ]

    return companies


def check_break_condition(total_emails, total_phone, base_url):
    parsed_url = urlparse(base_url)
    domain = parsed_url.netloc

    # Filter by emails with domain name
    domain_emails = [email for email in total_emails if domain in email]

    return len(domain_emails) > 12 and len(total_phone) > 6


def scrape_website(website_url, company_name):
    parsed_website_url = urlparse(website_url)
    start_url = parsed_website_url.netloc

    company = company_name
    depth = 0
    pages_scanned = 0

    sites_to_scrape = ["https://" + start_url]

    total_emails = []
    total_phone = []
    scrape_history = []

    while depth < 3:
        new_sites = []

        for site in sites_to_scrape:
            scrape_history.append(site)

            if start_url not in urlparse(site).netloc:
                log_status(
                    company=company,
                    message=f"Skipping external link {site}",
                    pages_scanned=pages_scanned,
                    depth=depth,
                )
                continue

            try:
                resp = requests.get(site, timeout=10)

                if resp.status_code != 200:
                    log_status(
                        company=company,
                        message=f"Skipping status code {resp.status_code} {site}",
                        pages_scanned=pages_scanned,
                        depth=depth,
                    )
                    continue

                pages_scanned += 1

                if (pages_scanned > 20 and depth > 1) or pages_scanned > 60:
                    # Check URL more strictly to be contact page
                    parsed_url = urlparse(site)
                    path = parsed_url.path

                    # If URL does not contain any contact substrings, skip
                    if (
                        not any([substr in path for substr in CONTACT_SUBSTRINGS])
                        or "stopcontact" in path.lower()
                    ):
                        log_status(
                            company=company,
                            message=f"Skipping non-contact page {site}",
                            pages_scanned=pages_scanned,
                            depth=depth,
                        )
                        continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # Get new pages to scrape
                for link in soup.find_all("a"):
                    href = link.get("href")

                    if (
                        not href
                        or href in ["#", "/", "javascript:void(0)"]
                        or "mailto:" in href
                    ):
                        continue

                    if href.startswith("http"):
                        new_site = href
                    else:
                        new_site = urljoin(start_url, href)

                    new_site = new_site.split("#")[0]

                    if new_site in scrape_history:
                        continue

                    new_sites.append(new_site)

                # Get all text from the page
                text = soup.get_text()

                emails = list(set(re.findall(EMAIL_REGEX, text)))

                for email in emails:
                    if email in total_emails:
                        continue

                    total_emails.append(email)

                    with open(email_file_str, "a") as data_file:
                        data_file.write(f"{company},{start_url},{site},{email}\n")

                phone_numbers = list(set(re.findall(PHONE_REGEX, text)))

                for phone in phone_numbers:
                    if phone in total_phone:
                        continue

                    total_phone.append(phone)

                    with open(phone_file_str, "a") as data_file:
                        data_file.write(f"{company},{start_url},{site},{phone}\n")

                log_status(
                    company=company,
                    message=f"Finished {site} | {len(total_emails)} email | {len(total_phone)} phone",
                    pages_scanned=pages_scanned,
                    depth=depth,
                )

                if check_break_condition(total_emails, total_phone, start_url):
                    return
            except Exception as e:
                continue

        if check_break_condition(total_emails, total_phone, start_url):
            break

        sites_to_scrape = list(set(new_sites))
        depth += 1

    with open("data/history/enriched_leads.txt", "a") as f:
        f.write(f"{company}\n")


def enrich_leads():
    # Create log file if it does not exist
    if not os.path.exists("data/history/enriched_leads.txt"):
        with open("data/history/enriched_leads.txt", "w") as f:
            f.write("")

    companies = get_companies()

    for index, company in enumerate(companies):
        company_name = company["company"]
        website_url = company["website"]

        scrape_website(website_url, company_name)

        print(f"[{company_name}] Done! ({index + 1})")

    print("Done!")


if __name__ == "__main__":
    enrich_leads()
