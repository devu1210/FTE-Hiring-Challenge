import asyncio
import json
import re
from playwright.async_api import async_playwright


URL = "https://disneycruise.disney.go.com/en-in/"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=200
        )

        page = await browser.new_page(
            viewport={"width": 1440, "height": 900}
        )

        responses = []

        async def capture_response(response):
            url = response.url

            if (
                "available-products" in url
                or "quick-quote" in url
                or "productavail" in url
            ):
                try:
                    request = response.request

                    record = {
                        "url": url,
                        "method": request.method,
                        "status": response.status,
                        "post_data": request.post_data,
                    }

                    print("\n========== API RESPONSE ==========")
                    print("METHOD:", request.method)
                    print("STATUS:", response.status)
                    print("URL:", url)

                    if request.post_data:
                        print("POST DATA:")
                        print(request.post_data[:2000])

                    try:
                        data = await response.json()

                        record["json"] = data

                        if isinstance(data, dict):
                            print("JSON KEYS:", list(data.keys()))

                            if "products" in data:
                                print(
                                    "PRODUCTS:",
                                    len(data.get("products", []))
                                )

                            if "totalAvailableCruises" in data:
                                print(
                                    "TOTAL CRUISES:",
                                    data.get("totalAvailableCruises")
                                )

                            if "totalPages" in data:
                                print(
                                    "TOTAL PAGES:",
                                    data.get("totalPages")
                                )

                    except Exception as e:
                        print("Could not parse JSON:", e)

                    responses.append(record)

                except Exception as e:
                    print("Response capture error:", e)

        page.on("response", capture_response)

        print("\n========================================")
        print("OPENING DISNEY CRUISE")
        print("========================================")

        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        await page.wait_for_timeout(5000)

        # ---------------------------------------------------------
        # STEP 1: Click "View Dates"
        # ---------------------------------------------------------

        print("\n========================================")
        print("STEP 1: VIEW DATES")
        print("========================================")

        view_dates = page.get_by_role(
            "button",
            name=re.compile(r"View Dates", re.IGNORECASE)
        )

        view_dates_count = await view_dates.count()

        print(
            f"View Dates buttons found: {view_dates_count}"
        )

        if view_dates_count == 0:
            print("ERROR: View Dates button not found.")
            await browser.close()
            return

        await view_dates.first.scroll_into_view_if_needed()

        await page.wait_for_timeout(1000)

        await view_dates.first.click()

        print("View Dates clicked successfully.")

        # Give Disney time to load the cruise list.
        await page.wait_for_timeout(10000)

        print(
            "\nCurrent URL:",
            page.url
        )

        # ---------------------------------------------------------
        # STEP 2: Locate "Show N Dates" links
        # IMPORTANT:
        # These are <a href="#"> elements, not buttons.
        # ---------------------------------------------------------

        print("\n========================================")
        print("STEP 2: FIND SHOW DATES LINKS")
        print("========================================")

        show_dates = page.locator(
            'a[href="#"]'
        ).filter(
            has_text=re.compile(
                r"Show\s+\d+\s+Dates?",
                re.IGNORECASE
            )
        )

        count = await show_dates.count()

        print(
            f"Show Dates links found: {count}"
        )

        # ---------------------------------------------------------
        # STEP 3: Print first few matching links
        # ---------------------------------------------------------

        if count > 0:

            print("\nFirst Show Dates links:")

            for i in range(min(count, 10)):
                try:
                    text = await show_dates.nth(i).inner_text()
                    href = await show_dates.nth(i).get_attribute("href")

                    print(
                        f"{i + 1}. text='{text.strip()}' | href='{href}'"
                    )

                except Exception as e:
                    print(
                        f"Could not inspect link {i}: {e}"
                    )

        else:
            print(
                "\nNo Show Dates links found using the primary locator."
            )

            # -----------------------------------------------------
            # FALLBACK: search all links containing "Show"
            # -----------------------------------------------------

            print(
                "\nTrying fallback link search..."
            )

            all_links = page.locator("a")

            all_link_count = await all_links.count()

            print(
                f"Total <a> elements: {all_link_count}"
            )

            matches = []

            for i in range(all_link_count):
                try:
                    text = (
                        await all_links.nth(i).inner_text()
                    ).strip()

                    if re.search(
                        r"Show\s+\d+\s+Dates?",
                        text,
                        re.IGNORECASE
                    ):
                        matches.append(
                            {
                                "index": i,
                                "text": text,
                                "href": await all_links.nth(i).get_attribute(
                                    "href"
                                )
                            }
                        )

                except Exception:
                    pass

            print(
                f"Fallback matches: {len(matches)}"
            )

            for item in matches[:10]:
                print(
                    f"{item['index']}: "
                    f"text='{item['text']}' | "
                    f"href='{item['href']}'"
                )

        # ---------------------------------------------------------
        # STEP 4: Click first Show Dates link
        # ---------------------------------------------------------

        if count > 0:

            first_show_dates = show_dates.first

            print("\n========================================")
            print("STEP 3: CLICK FIRST SHOW DATES")
            print("========================================")

            text_before = await first_show_dates.inner_text()

            print(
                "Clicking:",
                text_before.strip()
            )

            try:
                await first_show_dates.scroll_into_view_if_needed()

                await page.wait_for_timeout(1000)

                # Use force because Disney's card/list UI can have
                # overlapping elements while rendering.
                await first_show_dates.click(
                    force=True
                )

                print(
                    "Show Dates clicked successfully."
                )

            except Exception as e:

                print(
                    "Normal click failed:",
                    e
                )

                print(
                    "Trying JavaScript click..."
                )

                await first_show_dates.evaluate(
                    "(element) => element.click()"
                )

                print(
                    "JavaScript click executed."
                )

            # -----------------------------------------------------
            # STEP 5: Wait for any API triggered by the click
            # -----------------------------------------------------

            print(
                "\nWaiting for network/API activity..."
            )

            await page.wait_for_timeout(8000)

            # -----------------------------------------------------
            # STEP 6: Inspect page text after click
            # -----------------------------------------------------

            print("\n========================================")
            print("PAGE STATE AFTER SHOW DATES CLICK")
            print("========================================")

            print(
                "Current URL:",
                page.url
            )

            body_text = await page.locator(
                "body"
            ).inner_text()

            print("\n---------- BODY TEXT ----------")

            print(
                body_text[:15000]
            )

            # -----------------------------------------------------
            # STEP 7: Inspect visible date-related elements
            # -----------------------------------------------------

            print("\n========================================")
            print("DATE-RELATED ELEMENTS")
            print("========================================")

            date_patterns = [
                r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
                r"\b\d{1,2}-\d{1,2}-\d{2,4}\b",
                r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}",
                r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
            ]

            for pattern in date_patterns:

                matches = re.findall(
                    pattern,
                    body_text,
                    re.IGNORECASE
                )

                if matches:
                    print(
                        f"\nPattern: {pattern}"
                    )

                    print(
                        "Matches:",
                        matches[:50]
                    )

        # ---------------------------------------------------------
        # STEP 8: Save captured network data
        # ---------------------------------------------------------

        print("\n========================================")
        print("SAVING CAPTURED NETWORK DATA")
        print("========================================")

        with open(
            "show_dates_capture.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                responses,
                f,
                indent=2,
                ensure_ascii=False,
                default=str
            )

        print(
            f"Saved {len(responses)} captured responses."
        )

        print(
            "\nFile: show_dates_capture.json"
        )

        # ---------------------------------------------------------
        # STEP 9: Keep browser open briefly
        # ---------------------------------------------------------

        print(
            "\nBrowser will remain open for 10 seconds..."
        )

        await page.wait_for_timeout(10000)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())