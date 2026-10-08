import asyncio
import re
import pandas as pd
from pathlib import Path
from playwright.async_api import async_playwright

INPUT_CSV = "ingredients_network.csv"
OUTPUT_CSV = "ingredients_network.csv"
BACKUP_CSV = "ingredients_network_before_quickfacts_patch.csv"

CONCURRENCY = 10
SAVE_EVERY = 50


def clean(value):
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value).strip()
    return value


def extract_labeled_value(text, label, next_labels):
    """
    Extract:
        Sales markets
        VALUE

    or:
        Sales markets: VALUE
    """

    escaped = re.escape(label)

    # Label followed by value on same line
    pattern = rf"{escaped}\s*[:\-]?\s*([^\n\r]+)"
    m = re.search(pattern, text, re.I)

    if m:
        value = clean(m.group(1))

        # Don't accidentally capture another section heading
        for next_label in next_labels:
            if value.lower().startswith(next_label.lower()):
                value = ""
                break

        if value:
            return value

    # Label followed by value on next line(s)
    pattern = rf"{escaped}\s*(?:\n|\r\n)+\s*([^\n\r]+)"
    m = re.search(pattern, text, re.I)

    if m:
        value = clean(m.group(1))

        for next_label in next_labels:
            if value.lower().startswith(next_label.lower()):
                value = ""
                break

        if value:
            return value

    return ""


async def extract_quickfacts(page):
    body_text = await page.locator("body").inner_text(timeout=10000)
    body_text = body_text.replace("\xa0", " ")

    sales = extract_labeled_value(
        body_text,
        "Sales markets",
        [
            "Primary business activity",
            "Affiliated categories",
            "Categories",
            "Company description",
        ],
    )

    primary = extract_labeled_value(
        body_text,
        "Primary business activity",
        [
            "Affiliated categories",
            "Sales markets",
            "Categories",
            "Company description",
        ],
    )

    # Try DOM-based extraction if body-text extraction failed.
    if not sales or not primary:
        labels = await page.locator("text=/Sales markets|Primary business activity/i").all()

        for label_locator in labels:
            try:
                label_text = clean(await label_locator.inner_text())

                parent_text = clean(
                    await label_locator.locator("xpath=..").inner_text()
                )

                if "sales markets" in label_text.lower() and not sales:
                    candidate = re.sub(
                        r"(?i)^sales markets\s*:?\s*",
                        "",
                        parent_text,
                    )
                    if candidate.lower() != "sales markets":
                        sales = clean(candidate)

                if (
                    "primary business activity" in label_text.lower()
                    and not primary
                ):
                    candidate = re.sub(
                        r"(?i)^primary business activity\s*:?\s*",
                        "",
                        parent_text,
                    )
                    if candidate.lower() != "primary business activity":
                        primary = clean(candidate)

            except Exception:
                pass

    return sales, primary, body_text


async def process_row(browser, index, row, semaphore):
    async with semaphore:
        url = str(row["Profile URL"]).strip()

        page = await browser.new_page()

        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            await page.wait_for_timeout(1000)

            sales, primary, body_text = await extract_quickfacts(page)

            return index, sales, primary

        except Exception as e:
            print(f"[ERROR] {row['Company Name']} -> {e}")
            return index, "", ""

        finally:
            await page.close()


async def main():
    csv_path = Path(INPUT_CSV)

    if not csv_path.exists():
        print(f"ERROR: {INPUT_CSV} not found.")
        return

    df = pd.read_csv(INPUT_CSV).fillna("")

    # Backup before modification
    df.to_csv(BACKUP_CSV, index=False)

    # Normalize blanks
    for col in ["Sales Markets", "Primary Business Activity"]:
        df[col] = df[col].astype(str).replace(
            ["nan", "None", "NULL"],
            "",
        ).str.strip()

    mask = (
        df["Sales Markets"].eq("")
        | df["Primary Business Activity"].eq("")
    )

    targets = df[mask].copy()

    print("=" * 70)
    print("INGREDIENTS NETWORK - QUICK FACTS PATCH")
    print("=" * 70)
    print(f"Total rows              : {len(df)}")
    print(f"Rows needing repair     : {len(targets)}")
    print(
        f"Sales Markets missing   : {df['Sales Markets'].eq('').sum()}"
    )
    print(
        f"Primary Activity missing: "
        f"{df['Primary Business Activity'].eq('').sum()}"
    )
    print("=" * 70)

    if targets.empty:
        print("Nothing to repair.")
        return

    semaphore = asyncio.Semaphore(CONCURRENCY)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )

        tasks = [
            process_row(
                browser,
                index,
                row,
                semaphore,
            )
            for index, row in targets.iterrows()
        ]

        completed = 0
        repaired_sales = 0
        repaired_primary = 0

        for future in asyncio.as_completed(tasks):
            index, sales, primary = await future

            company = df.at[index, "Company Name"]

            if (
                not df.at[index, "Sales Markets"].strip()
                and sales
            ):
                df.at[index, "Sales Markets"] = sales
                repaired_sales += 1

            if (
                not df.at[index, "Primary Business Activity"].strip()
                and primary
            ):
                df.at[index, "Primary Business Activity"] = primary
                repaired_primary += 1

            completed += 1

            if completed % SAVE_EVERY == 0:
                df.to_csv(OUTPUT_CSV, index=False)
                print(
                    f"[{completed}/{len(targets)}] "
                    f"Checkpoint saved | "
                    f"Sales={repaired_sales} | "
                    f"Primary={repaired_primary}"
                )

        await browser.close()

    # Final save
    df.to_csv(OUTPUT_CSV, index=False)

    print("\n" + "=" * 70)
    print("PATCH COMPLETE")
    print("=" * 70)

    print(f"Rows processed           : {len(targets)}")
    print(f"Sales Markets repaired   : {repaired_sales}")
    print(f"Primary Activity repaired: {repaired_primary}")

    print("\nFINAL QUALITY")
    print("-" * 70)

    for col in [
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
    ]:
        missing = df[col].astype(str).str.strip().eq("").sum()
        filled = len(df) - missing
        print(
            f"{col:<28} "
            f"filled={filled:<5} "
            f"missing={missing}"
        )

    print("\nBackup:")
    print(BACKUP_CSV)

    print("\nOutput:")
    print(OUTPUT_CSV)


if __name__ == "__main__":
    asyncio.run(main())