import re
from urllib.parse import urlparse
import pandas as pd
from playwright.sync_api import sync_playwright

EMAIL_REGEX = r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"
PHONE_REGEX = r"(^\+[0-9]{2}|^\+[0-9]{2}\(0\)|^\(\+[0-9]{2}\)\(0\)|^00[0-9]{2}|^0)([0-9]{9}$|[0-9\-\s]{10}$)"


def check_break_condition(total_emails, total_phone, base_url):
    parsed_url = urlparse(base_url)
    domain = parsed_url.netloc

    # Filter by emails with domain name
    domain_emails = [email for email in total_emails if domain in email]

    return len(domain_emails) > 20 and len(total_phone) > 20


def get_site_contact_info(
    leads_df: pd.DataFrame, website_column: str, company_column: str
):
    email_log_file = open("data/email-log.csv", "a")
    phone_log_file = open("data/phone-log.csv", "a")

    email_result_list = []
    phone_result_list = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        def scrape_website(row):
            index = row.name
            start_url = row[website_column]
            company = row[company_column]

            # Remove https from URL
            start_url = start_url.replace("https://", "")
            start_url = start_url.replace("http://", "")

            depth = 0

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

                    print(
                        f"[{company}] Scraping {site} at depth {depth} ({index + 1} of {len(leads_df)})"
                    )
                    print(
                        f"[{company}] Found {len(total_emails)} emails and {len(total_phone)} phone numbers"
                    )

                    # If navigated to different website, skip
                    if not start_url in site:
                        continue

                    # Playwright needs URL with http or https
                    if not site.startswith("http"):
                        site = "https://" + site

                    try:
                        page.goto(site)
                        page.wait_for_load_state("networkidle")
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
                        total_emails.extend(
                            [
                                {"company": company, "site": site, "email": email}
                                for email in emails
                            ]
                        )

                        # Find all Dutch phone numbers
                        phone_numbers = re.findall(PHONE_REGEX, text)
                        total_phone.extend(
                            [
                                {"company": company, "site": site, "phone": phone}
                                for phone in phone_numbers
                            ]
                        )

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

            email_result_list.extend(total_emails)
            phone_result_list.extend(total_phone)

            # Write to log file
            for email in total_emails:
                email_log_file.write(
                    f"{email['company']},{email['site']},{email['email']}\n"
                )

            for phone in total_phone:
                phone_log_file.write(
                    f"{phone['company']},{phone['site']},{phone['phone']}\n"
                )

        leads_df.apply(scrape_website, axis=1)

    return email_result_list, phone_result_list


if __name__ == "__main__":
    website_df = pd.read_csv("data/lead-list.csv")
    website_df = website_df[:50]

    # Get contact info
    email_result_list, phone_result_list = get_site_contact_info(
        leads_df=website_df, website_column="Website", company_column="Company"
    )
    email_df = pd.DataFrame(email_result_list)
    phone_df = pd.DataFrame(phone_result_list)

    # Remove duplicates
    email_df = email_df.drop_duplicates(subset=["email"])
    phone_df = phone_df.drop_duplicates(subset=["phone"])

    # Save to CSV
    email_df.to_csv("data/emails.csv", index=False)
    phone_df.to_csv("data/phones.csv", index=False)

    print("Done!")
