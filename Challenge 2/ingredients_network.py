import asyncio
import re
import os
from urllib.parse import urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


BASE_URL = "https://www.ingredientsnetwork.com"

OUTPUT_CSV = "ingredients_network.csv"
TEMP_CSV = "ingredients_temp.csv"
URLS_FILE = "company_urls.txt"

CONCURRENCY = 10
SAVE_EVERY = 25
PAGE_TIMEOUT = 60000

REQUIRED_COLUMNS = [
    "Company Name",
    "Company Description",
    "Sales Markets",
    "Primary Business Activity",
    "Categories",
    "Events",
    "Address",
    "Email",
    "Telephone",
    "Website",
    "Profile URL",
]


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    if isinstance(value, (list, tuple)):
        value = " ".join(str(x) for x in value)

    value = re.sub(r"\s+", " ", str(value))
    return value.strip(" |:-\t\r\n")


def unique_join(values, separator=" | "):
    result = []

    for value in values:
        value = clean_text(value)

        if value and value not in result:
            result.append(value)

    return separator.join(result)


def normalize_url(url):
    if not url:
        return ""

    url = str(url).strip()

    if url.startswith("//"):
        url = "https:" + url

    if url.startswith("/"):
        url = urljoin(BASE_URL, url)

    return url.split("#")[0]


def is_external_url(url):
    if not url:
        return False

    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False

    if not host:
        return False

    blocked = [
        "ingredientsnetwork.com",
        "facebook.com",
        "linkedin.com",
        "youtube.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "google.com",
        "pinterest.com",
    ]

    return not any(domain in host for domain in blocked)


def is_empty(value):
    return not clean_text(value)


# ============================================================
# EXISTING DATA
# ============================================================

def load_existing_urls():
    if not os.path.exists(URLS_FILE):
        return []

    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls = [
            normalize_url(line)
            for line in f
            if line.strip()
        ]

    urls = sorted(set(x for x in urls if x))

    print(f"Existing company URLs loaded: {len(urls)}")

    return urls


def load_existing_data():
    """
    Load previous CSV so reruns do not destroy good values.
    """

    if not os.path.exists(OUTPUT_CSV):
        return {}

    try:
        df = pd.read_csv(
            OUTPUT_CSV,
            dtype=str,
            keep_default_na=False
        )

        if "Profile URL" not in df.columns:
            return {}

        existing = {}

        for _, row in df.iterrows():
            url = normalize_url(row.get("Profile URL", ""))

            if not url:
                continue

            record = {}

            for column in REQUIRED_COLUMNS:
                record[column] = clean_text(
                    row.get(column, "")
                )

            existing[url] = record

        print(f"Existing CSV records loaded: {len(existing)}")

        return existing

    except Exception as e:
        print(f"Could not load existing CSV: {e}")
        return {}


# ============================================================
# TEXT EXTRACTION
# ============================================================

def body_lines(soup):
    text = soup.get_text("\n", strip=True)

    lines = []

    for line in text.splitlines():
        line = clean_text(line)

        if line:
            lines.append(line)

    return lines


def find_heading(soup, keywords):
    keywords = [
        clean_text(x).lower()
        for x in keywords
    ]

    for tag in soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    ):
        text = clean_text(
            tag.get_text(" ", strip=True)
        ).lower()

        if any(keyword in text for keyword in keywords):
            return tag

    return None


def extract_section_text(
    soup,
    start_keywords,
    stop_keywords=None
):
    stop_keywords = stop_keywords or []

    lines = body_lines(soup)

    start_index = None

    for i, line in enumerate(lines):
        lower = line.lower()

        if any(
            keyword.lower() in lower
            for keyword in start_keywords
        ):
            start_index = i
            break

    if start_index is None:
        return ""

    collected = []

    for line in lines[start_index + 1:]:
        lower = line.lower()

        if any(
            keyword.lower() in lower
            for keyword in stop_keywords
        ):
            break

        collected.append(line)

        if len(collected) >= 30:
            break

    return unique_join(
        collected,
        separator=" | "
    )


# ============================================================
# COMPANY NAME
# ============================================================

def extract_company_name(soup):
    for selector in [
        "h1",
        ".company-name",
        ".companyName",
        ".profile-name",
        ".supplier-name",
        "[class*='company-name']",
        "[class*='companyName']",
        "[class*='supplier-name']",
        "[class*='supplierName']",
    ]:
        tag = soup.select_one(selector)

        if tag:
            value = clean_text(
                tag.get_text(" ", strip=True)
            )

            if value:
                return value

    title = clean_text(
        soup.title.get_text()
        if soup.title
        else ""
    )

    title = re.sub(
        r"\s*\|\s*Ingredients Network.*$",
        "",
        title,
        flags=re.I
    )

    title = re.sub(
        r"\s*-\s*Ingredients Network.*$",
        "",
        title,
        flags=re.I
    )

    return clean_text(title)


# ============================================================
# DESCRIPTION
# ============================================================

def extract_description(soup):
    selectors = [
        ".company-description",
        ".companyDescription",
        ".profile-description",
        ".supplier-description",
        "[class*='company-description']",
        "[class*='companyDescription']",
        "[class*='profile-description']",
        "[class*='supplier-description']",
    ]

    candidates = []

    for selector in selectors:
        for tag in soup.select(selector):
            value = clean_text(
                tag.get_text(" ", strip=True)
            )

            if len(value) >= 30:
                candidates.append(value)

    if candidates:
        return max(candidates, key=len)

    # Look around "Company description"
    lines = body_lines(soup)

    for i, line in enumerate(lines):
        if "company description" in line.lower():
            values = []

            for next_line in lines[i + 1:i + 8]:
                lower = next_line.lower()

                if any(
                    stop in lower
                    for stop in [
                        "quick facts",
                        "sales markets",
                        "primary business activity",
                        "affiliated categories",
                        "upcoming events",
                        "contact information",
                    ]
                ):
                    break

                values.append(next_line)

            value = unique_join(values, " ")

            if len(value) >= 20:
                return value

    # Meta fallback
    for selector in [
        'meta[name="description"]',
        'meta[property="og:description"]',
    ]:
        tag = soup.select_one(selector)

        if tag:
            value = clean_text(
                tag.get("content", "")
            )

            if value:
                return value

    return ""


# ============================================================
# QUICK FACTS
# ============================================================

def extract_fact_from_lines(lines, label):
    label_lower = label.lower()

    for i, line in enumerate(lines):
        lower = line.lower()

        # Same line:
        # Sales markets | Asia, Europe
        match = re.search(
            rf"{re.escape(label_lower)}\s*\|\s*(.+)",
            lower,
            flags=re.I
        )

        if match:
            original = line

            value = re.sub(
                rf"^{re.escape(label)}\s*\|\s*",
                "",
                original,
                flags=re.I
            )

            value = clean_text(value)

            if value:
                return value

        # Label on one line, value next line
        if lower.strip() == label_lower:
            for next_line in lines[i + 1:i + 4]:
                value = clean_text(next_line)

                if not value:
                    continue

                if value.lower() == label_lower:
                    continue

                return value

    return ""


def extract_quick_facts(soup):
    lines = body_lines(soup)

    sales_markets = ""

    for label in [
        "Sales markets",
        "Sales Markets",
        "Sales market",
    ]:
        sales_markets = extract_fact_from_lines(
            lines,
            label
        )

        if sales_markets:
            break

    primary_activity = ""

    for label in [
        "Primary business activity",
        "Primary Business Activity",
        "Primary business activities",
        "Primary Activity",
    ]:
        primary_activity = extract_fact_from_lines(
            lines,
            label
        )

        if primary_activity:
            break

    return (
        clean_text(sales_markets),
        clean_text(primary_activity)
    )


# ============================================================
# CATEGORIES
# ============================================================

def extract_categories(soup):
    categories = []

    # Find the actual category section
    heading = find_heading(
        soup,
        [
            "Categories affiliated with",
            "Categories",
            "Affiliated categories",
        ]
    )

    if heading:
        # First try links near heading
        parent = heading.parent

        if parent:
            for a in parent.find_all(
                "a",
                href=True
            ):
                text = clean_text(
                    a.get_text(" ", strip=True)
                )

                href = a.get("href", "")

                if not text:
                    continue

                if text.lower() in {
                    "more",
                    "less",
                    "view all",
                    "read more",
                }:
                    continue

                if (
                    "/category" in href.lower()
                    or "/ingredient" in href.lower()
                    or "/food" in href.lower()
                    or text
                ):
                    if len(text) <= 150:
                        categories.append(text)

        # Then inspect following elements
        current = heading

        for _ in range(20):
            current = current.find_next()

            if not current:
                break

            if current.name in [
                "h2",
                "h3",
                "h4",
                "h5",
            ]:
                text = clean_text(
                    current.get_text(" ", strip=True)
                )

                if (
                    text
                    and text != clean_text(
                        heading.get_text(
                            " ",
                            strip=True
                        )
                    )
                ):
                    if any(
                        stop in text.lower()
                        for stop in [
                            "contact information",
                            "upcoming events",
                            "request information",
                            "meet us at",
                        ]
                    ):
                        break

                    if len(text) <= 150:
                        categories.append(text)

            elif current.name == "a":
                text = clean_text(
                    current.get_text(
                        " ",
                        strip=True
                    )
                )

                href = current.get(
                    "href",
                    ""
                ).lower()

                if (
                    text
                    and len(text) <= 150
                    and (
                        "/category" in href
                        or "/categories" in href
                        or "/ingredient" in href
                    )
                ):
                    categories.append(text)

    # Generic category links
    if not categories:
        for a in soup.find_all(
            "a",
            href=True
        ):
            text = clean_text(
                a.get_text(" ", strip=True)
            )

            href = a.get(
                "href",
                ""
            ).lower()

            if (
                text
                and len(text) <= 150
                and (
                    "/category/" in href
                    or "/categories/" in href
                    or "/ingredients/" in href
                )
            ):
                categories.append(text)

    # Remove obvious navigation
    blocked = {
        "categories",
        "view all",
        "more",
        "less",
        "read more",
        "learn more",
    }

    categories = [
        x for x in categories
        if x.lower() not in blocked
    ]

    return unique_join(categories)


# ============================================================
# EVENTS
# ============================================================

def extract_events(soup):
    events = []

    heading = find_heading(
        soup,
        [
            "Upcoming events",
            "Upcoming Event",
            "Recently at",
        ]
    )

    if not heading:
        return ""

    # Inspect parent containers
    containers = []

    if heading.parent:
        containers.append(heading.parent)

    if heading.parent and heading.parent.parent:
        containers.append(
            heading.parent.parent
        )

    for container in containers:
        for element in container.find_all(
            ["article", "li", "div", "a"]
        ):
            text = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if not text:
                continue

            if len(text) < 10 or len(text) > 500:
                continue

            lower = text.lower()

            if any(
                keyword in lower
                for keyword in [
                    "ingredients network",
                    "contact information",
                    "request information",
                    "view all",
                    "read more",
                ]
            ):
                continue

            # Event-like text usually has a date,
            # venue, exhibition, show, etc.
            if (
                re.search(
                    r"\b\d{1,2}\s*[-–]?\s*"
                    r"\d{0,2}\s*"
                    r"(jan|feb|mar|apr|may|jun|jul|aug|"
                    r"sep|sept|oct|nov|dec)",
                    lower
                )
                or any(
                    word in lower
                    for word in [
                        "expo",
                        "exhibition",
                        "trade show",
                        "fi europe",
                        "vitafoods",
                        "gulfood",
                        "food ingredients",
                    ]
                )
            ):
                events.append(text)

    # Deduplicate
    cleaned = []

    for event in events:
        event = clean_text(event)

        if (
            event
            and event not in cleaned
        ):
            cleaned.append(event)

    return unique_join(
        cleaned,
        separator=" || "
    )


# ============================================================
# CONTACT
# ============================================================

def extract_contact_details(soup):
    email = ""
    telephone = ""
    website = ""

    # Email
    for a in soup.find_all(
        "a",
        href=True
    ):
        href = a.get(
            "href",
            ""
        ).strip()

        if href.lower().startswith(
            "mailto:"
        ):
            email = clean_text(
                href[7:].split("?")[0]
            )

            if email:
                break

    # Visible email
    if not email:
        text = soup.get_text(
            " ",
            strip=True
        )

        match = re.search(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            text,
            flags=re.I
        )

        if match:
            email = clean_text(
                match.group(0)
            )

    # Telephone
    for a in soup.find_all(
        "a",
        href=True
    ):
        href = a.get(
            "href",
            ""
        ).strip()

        if href.lower().startswith(
            "tel:"
        ):
            telephone = clean_text(
                href[4:]
            )

            if telephone:
                break

    # Telephone visible fallback
    if not telephone:
        for selector in [
            "[class*='phone']",
            "[class*='telephone']",
            "[class*='tel']",
        ]:
            for tag in soup.select(selector):
                value = clean_text(
                    tag.get_text(
                        " ",
                        strip=True
                    )
                )

                if value:
                    telephone = value
                    break

            if telephone:
                break

    # Website
    candidates = []

    for a in soup.find_all(
        "a",
        href=True
    ):
        href = normalize_url(
            a.get("href", "")
        )

        if not href.startswith(
            ("http://", "https://")
        ):
            continue

        if is_external_url(href):
            candidates.append(href)

    for candidate in candidates:
        lower = candidate.lower()

        if not any(
            x in lower
            for x in [
                "privacy",
                "terms",
                "cookie",
            ]
        ):
            website = candidate
            break

    return (
        clean_text(email),
        clean_text(telephone),
        clean_text(website),
    )


# ============================================================
# ADDRESS
# ============================================================

def extract_address(soup):
    addresses = []

    for tag in soup.find_all("address"):
        value = clean_text(
            tag.get_text(
                " ",
                strip=True
            )
        )

        if value:
            addresses.append(value)

    if addresses:
        return unique_join(
            addresses,
            separator=" | "
        )

    for selector in [
        "[class*='address']",
        "[class*='Address']",
        "[class*='location']",
        "[class*='Location']",
    ]:
        for tag in soup.select(selector):
            value = clean_text(
                tag.get_text(
                    " ",
                    strip=True
                )
            )

            if (
                value
                and len(value) >= 8
                and len(value) <= 500
            ):
                return value

    lines = body_lines(soup)

    for i, line in enumerate(lines):
        if line.lower() in {
            "address",
            "company address",
            "office address",
        }:
            values = []

            for next_line in lines[i + 1:i + 6]:
                if next_line.lower() in {
                    "email",
                    "telephone",
                    "phone",
                    "website",
                }:
                    break

                values.append(next_line)

            value = unique_join(
                values,
                separator=", "
            )

            if value:
                return value

    return ""


# ============================================================
# PROFILE
# ============================================================

def extract_profile(html, url):
    soup = BeautifulSoup(
        html,
        "lxml"
    )

    company_name = extract_company_name(
        soup
    )

    description = extract_description(
        soup
    )

    sales_markets, primary_activity = (
        extract_quick_facts(soup)
    )

    categories = extract_categories(
        soup
    )

    events = extract_events(
        soup
    )

    address = extract_address(
        soup
    )

    email, telephone, website = (
        extract_contact_details(soup)
    )

    return {
        "Company Name": company_name,
        "Company Description": description,
        "Sales Markets": sales_markets,
        "Primary Business Activity": primary_activity,
        "Categories": categories,
        "Events": events,
        "Address": address,
        "Email": email,
        "Telephone": telephone,
        "Website": website,
        "Profile URL": url,
    }


# ============================================================
# BROWSER SCRAPING
# ============================================================

async def scrape_page(page, url):
    for attempt in range(3):
        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=PAGE_TIMEOUT
            )

            # Give dynamic content time to render
            await page.wait_for_timeout(1200)

            try:
                await page.wait_for_load_state(
                    "networkidle",
                    timeout=8000
                )
            except Exception:
                pass

            # Scroll to trigger lazy-loaded sections
            await page.evaluate(
                """
                async () => {
                    window.scrollTo(
                        0,
                        document.body.scrollHeight
                    );
                    await new Promise(
                        r => setTimeout(r, 700)
                    );
                    window.scrollTo(0, 0);
                }
                """
            )

            await page.wait_for_timeout(500)

            html = await page.content()

            if html and len(html) > 1000:
                return html

        except Exception as e:
            print(
                f"[RETRY {attempt + 1}/3] "
                f"{url} -> {str(e)[:150]}"
            )

            await asyncio.sleep(
                1 + attempt
            )

    return None


# ============================================================
# MERGE
# ============================================================

def merge_records(old, new):
    """
    Keep existing good values.
    Replace only when the new browser extraction
    actually found something.
    """

    merged = {}

    for column in REQUIRED_COLUMNS:
        old_value = clean_text(
            old.get(column, "")
        )

        new_value = clean_text(
            new.get(column, "")
        )

        merged[column] = (
            new_value
            if new_value
            else old_value
        )

    return merged


# ============================================================
# WORKER
# ============================================================

async def worker(
    worker_id,
    browser,
    urls,
    existing,
    results,
    counter,
    lock,
):
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/154.0.0.0 Safari/537.36"
        ),
        locale="en-US",
    )

    page = await context.new_page()

    for url in urls:
        old_record = existing.get(
            url,
            {}
        )

        html = await scrape_page(
            page,
            url
        )

        if html:
            try:
                new_record = extract_profile(
                    html,
                    url
                )

                record = merge_records(
                    old_record,
                    new_record
                )

            except Exception as e:
                print(
                    f"[PARSE ERROR] "
                    f"{url} -> {e}"
                )

                record = old_record.copy()

                if not record:
                    record = {
                        column: ""
                        for column in REQUIRED_COLUMNS
                    }

                record["Profile URL"] = url

        else:
            record = old_record.copy()

            if not record:
                record = {
                    column: ""
                    for column in REQUIRED_COLUMNS
                }

            record["Profile URL"] = url

        async with lock:
            results[url] = record
            counter[0] += 1

            current = counter[0]
            total = counter[1]

            print(
                f"[{current}/{total}] "
                f"{record.get('Company Name', '')[:60]}"
            )

            if current % SAVE_EVERY == 0:
                save_checkpoint(
                    results
                )

    await context.close()


# ============================================================
# CHECKPOINT
# ============================================================

def save_checkpoint(results):
    rows = list(results.values())

    if not rows:
        return

    df = pd.DataFrame(rows)

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[
        REQUIRED_COLUMNS
    ]

    for column in REQUIRED_COLUMNS:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .map(clean_text)
        )

    df = df.drop_duplicates(
        subset=["Profile URL"]
    )

    df.to_csv(
        TEMP_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"\nCHECKPOINT SAVED: "
        f"{len(df)} records\n"
    )


# ============================================================
# FINAL VALIDATION
# ============================================================

def validate_dataframe(df):
    print("\n================================")
    print("DATA QUALITY")
    print("================================")

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            print(
                f"{column}: COLUMN MISSING"
            )
            continue

        empty = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
            .sum()
        )

        print(
            f"{column}: empty = {empty}"
        )

    print(
        f"Rows: {len(df)}"
    )

    print(
        "Duplicate company names:",
        df["Company Name"].duplicated().sum()
    )

    print(
        "Duplicate profile URLs:",
        df["Profile URL"].duplicated().sum()
    )


# ============================================================
# MAIN
# ============================================================

async def main():
    print("================================")
    print("INGREDIENTS NETWORK SCRAPER")
    print("BROWSER RENDERED VERSION")
    print("================================")

    company_urls = load_existing_urls()

    if not company_urls:
        raise RuntimeError(
            "company_urls.txt not found. "
            "Your 1592 URLs are required."
        )

    existing = load_existing_data()

    print(
        f"\nProfiles to process: "
        f"{len(company_urls)}"
    )

    print(
        f"Existing records to preserve: "
        f"{len(existing)}"
    )

    results = {}

    # Start with previous records
    for url in company_urls:
        if url in existing:
            results[url] = existing[url]

    counter = [
        0,
        len(company_urls)
    ]

    lock = asyncio.Lock()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )

        # Split URLs among workers
        chunks = [
            company_urls[i::CONCURRENCY]
            for i in range(CONCURRENCY)
        ]

        tasks = []

        for worker_id, chunk in enumerate(chunks):
            if not chunk:
                continue

            tasks.append(
                asyncio.create_task(
                    worker(
                        worker_id,
                        browser,
                        chunk,
                        existing,
                        results,
                        counter,
                        lock,
                    )
                )
            )

        await asyncio.gather(
            *tasks
        )

        await browser.close()

    # Final save
    save_checkpoint(
        results
    )

    rows = list(results.values())

    df = pd.DataFrame(rows)

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[
        REQUIRED_COLUMNS
    ]

    for column in REQUIRED_COLUMNS:
        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
            .map(clean_text)
        )

    # Profile URL is the true identity
    df = (
        df
        .drop_duplicates(
            subset=["Profile URL"]
        )
        .reset_index(drop=True)
    )

    # Keep same general ordering
    df = df.sort_values(
        by=[
            "Company Name",
            "Profile URL"
        ],
        kind="stable"
    ).reset_index(
        drop=True
    )

    df.to_csv(
        TEMP_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n================================")
    print("INGREDIENTS NETWORK COMPLETE")
    print("================================")

    print(
        f"Company profiles processed: "
        f"{len(df)}"
    )

    print(
        f"Output: {OUTPUT_CSV}"
    )

    print(
        f"Temp: {TEMP_CSV}"
    )

    print(
        f"URLs: {URLS_FILE}"
    )

    validate_dataframe(
        df
    )


if __name__ == "__main__":
    asyncio.run(main())