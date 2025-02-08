import sys
import re
import pandas as pd
from playwright.sync_api import sync_playwright

EMAIL_REGEX = r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"
PHONE_REGEX = r"(^\+[0-9]{2}|^\+[0-9]{2}\(0\)|^\(\+[0-9]{2}\)\(0\)|^00[0-9]{2}|^0)([0-9]{9}$|[0-9\-\s]{10}$)"
WHITE_SPACE_FILL = "                                       "


def get_site_contact_info(
    leads_df: pd.DataFrame, website_column: str, company_column: str
):
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

            while depth < 3:
                # Find all the links on the page
                new_sites = []

                # For all pages at depth
                for site in sites_to_scrape:
                    # If navigated to path instead of website add base url
                    if site.startswith("/"):
                        site = start_url + site

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
                            if href and href.startswith("http"):
                                new_sites.append(href)

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
                    except Exception as e:
                        continue

                sites_to_scrape = new_sites

                depth += 1

            email_result_list.extend(total_emails)
            phone_result_list.extend(total_phone)

        leads_df.apply(scrape_website, axis=1)

    return email_result_list, phone_result_list


if __name__ == "__main__":
    website_df = pd.read_csv("data/lead-list.csv")

    email_result_list, phone_result_list = get_site_contact_info(
        leads_df=website_df, website_column="Website", company_column="Company"
    )
    email_df = pd.DataFrame(email_result_list)
    phone_df = pd.DataFrame(phone_result_list)

    email_df.to_csv("data/emails.csv", index=False)
    phone_df.to_csv("data/phones.csv", index=False)

    print("Done!")
