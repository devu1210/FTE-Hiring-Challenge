import asyncio
from playwright.async_api import async_playwright

URL = "https://www.ingredientsnetwork.com/company/a.html"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        page = await browser.new_page(
            viewport={"width": 1400, "height": 900}
        )

        print("Opening Suppliers directory...")
        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        print("\n================================")
        print("SUPPLIERS DIRECTORY")
        print("================================")

        print("URL:", page.url)
        print("TITLE:", await page.title())

        print("\n=== PAGE TEXT ===")

        text = await page.locator("body").inner_text()

        print(text[:20000])

        print("\n=== ALL LINKS ===")

        links = page.locator("a")
        count = await links.count()

        print("TOTAL LINKS:", count)

        for i in range(count):
            try:
                el = links.nth(i)

                text = (await el.inner_text()).strip()
                href = await el.get_attribute("href")

                if text or href:
                    print(
                        f"{i}: TEXT={repr(text[:200])} | HREF={href}"
                    )

            except:
                pass

        print("\n=== PAGINATION / SHOW MORE ===")

        for selector in [
            "a",
            "button",
            "input"
        ]:
            elements = page.locator(selector)

            for i in range(await elements.count()):
                try:
                    el = elements.nth(i)

                    txt = ""

                    try:
                        txt = (await el.inner_text()).strip()
                    except:
                        pass

                    href = await el.get_attribute("href")
                    value = await el.get_attribute("value")

                    combined = (
                        f"{txt} {href} {value}"
                    ).lower()

                    if any(x in combined for x in [
                        "next",
                        "more",
                        "page",
                        "load"
                    ]):
                        print(
                            selector,
                            i,
                            "TEXT=", repr(txt),
                            "HREF=", href,
                            "VALUE=", value
                        )

                except:
                    pass

        print("\n=== COMPANY LINKS ===")

        company_links = []

        for i in range(count):
            try:
                el = links.nth(i)

                href = await el.get_attribute("href")
                text = (await el.inner_text()).strip()

                if href and (
                    "-comp" in href
                    or "/company/" in href
                ):
                    company_links.append(
                        (text, href)
                    )

            except:
                pass

        print(
            "COMPANY LINKS FOUND:",
            len(company_links)
        )

        for text, href in company_links[:100]:
            print(
                repr(text[:150]),
                "=>",
                href
            )

        print("\n=== SAVING HTML ===")

        html = await page.content()

        with open(
            "suppliers_directory.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(html)

        await page.screenshot(
            path="suppliers_directory.png",
            full_page=True
        )

        print("Saved suppliers_directory.html")
        print("Saved suppliers_directory.png")

        print("\nBrowser remains open.")
        await asyncio.to_thread(
            input,
            "Press ENTER to close..."
        )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())