import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://disneycruise.disney.go.com/en-in/"

PRODUCT_NAME = "7-Night British Isles Cruise from Southampton"
SAILING_ID = "WW0594"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Opening Disney Cruise...")
        await page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(5000)

        view_dates = page.get_by_role("button", name="View Dates")

        if await view_dates.count() == 0:
            print("View Dates button not found.")
            await browser.close()
            return

        await view_dates.first.click()
        await page.wait_for_timeout(5000)

        print("Searching product:", PRODUCT_NAME)

        found = False

        for i in range(150):
            cards = page.locator("h2.product-card-content__name")

            count = await cards.count()

            for j in range(count):
                name = (await cards.nth(j).inner_text()).strip()

                if PRODUCT_NAME.lower() in name.lower():
                    print("FOUND PRODUCT:", name)

                    card = cards.nth(j).locator(
                        "xpath=ancestor::*[.//a[contains(., 'Show')]][1]"
                    )

                    show_dates = card.get_by_text(
                        "Show", exact=False
                    )

                    print("Show-date elements:", await show_dates.count())

                    async with page.expect_response(
                        lambda r: (
                            "available-sailings" in r.url
                            and r.request.method == "POST"
                        ),
                        timeout=30000
                    ) as response_info:

                        await show_dates.first.click()

                    response = await response_info.value

                    print("API URL:", response.url)
                    print("Status:", response.status)

                    request = response.request

                    print("\nREQUEST BODY:")
                    print(request.post_data)

                    data = await response.json()

                    with open(
                        "ww0594_response.json",
                        "w",
                        encoding="utf-8"
                    ) as f:
                        json.dump(data, f, indent=2)

                    print("\nResponse saved to ww0594_response.json")

                    sailings = data.get("sailings", [])

                    print("Sailings returned:", len(sailings))

                    for sailing in sailings:
                        if sailing.get("sailingId") == SAILING_ID:
                            print("\nFOUND TARGET SAILING:")
                            print(json.dumps(sailing, indent=2))

                    found = True
                    break

            if found:
                break

            await page.mouse.wheel(0, 1200)
            await page.wait_for_timeout(700)

        if not found:
            print("\nProduct was not found.")

        await page.wait_for_timeout(3000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())