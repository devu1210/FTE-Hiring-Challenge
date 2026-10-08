import asyncio
from playwright.async_api import async_playwright

URL = "https://www.ingredientsnetwork.com/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        print("Opening Ingredients Network...")
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        await page.wait_for_timeout(8000)

        print("\n=== PAGE ===")
        print("URL:", page.url)
        print("TITLE:", await page.title())

        print("\n=== ALL TEXT INPUTS ===")

        inputs = page.locator("input")
        input_count = await inputs.count()

        for i in range(input_count):
            try:
                el = inputs.nth(i)

                print(
                    i,
                    "type=", await el.get_attribute("type"),
                    "name=", await el.get_attribute("name"),
                    "placeholder=", await el.get_attribute("placeholder"),
                    "value=", await el.input_value()
                )
            except Exception:
                pass

        print("\n=== SEARCH INPUT DETECTION ===")

        search_input = None

        selectors = [
            'input[placeholder*="I’m looking for"]',
            'input[placeholder*="I\'m looking for"]',
            'input[type="text"]',
            'input[type="search"]'
        ]

        for selector in selectors:
            loc = page.locator(selector)

            try:
                count = await loc.count()
                print(selector, "=>", count)

                if count > 0:
                    for i in range(count):
                        try:
                            candidate = loc.nth(i)

                            if await candidate.is_visible():
                                search_input = candidate
                                print("Using:", selector, "index", i)
                                break
                        except:
                            pass

                if search_input:
                    break

            except:
                pass

        if not search_input:
            print("\nERROR: Could not find visible search input.")
            print("Saving screenshot...")
            await page.screenshot(path="ingredients_debug.png", full_page=True)

            print("Screenshot saved as ingredients_debug.png")

            await asyncio.to_thread(input("Press ENTER to close..."))
            await browser.close()
            return

        print("\nSearch input found.")

        print("Placeholder:",
              await search_input.get_attribute("placeholder"))

        print("Name:",
              await search_input.get_attribute("name"))

        print("Type:",
              await search_input.get_attribute("type"))

        print("\n=== SEARCH FORM ===")

        form = search_input.locator("xpath=ancestor::form[1]")

        if await form.count():
            print("FORM ACTION:",
                  await form.get_attribute("action"))

            print("FORM METHOD:",
                  await form.get_attribute("method"))

            try:
                html = await form.evaluate("(el) => el.outerHTML")
                print("\nFORM HTML:")
                print(html[:10000])
            except:
                pass
        else:
            print("No parent form found.")

        print("\n=== PERFORMING SEARCH ===")

        await search_input.fill("protein")

        print("Entered: protein")

        await page.wait_for_timeout(1000)

        print("\n=== SEARCH BUTTONS ===")

        buttons = page.locator("button, input[type='submit'], input[type='search']")

        button_count = await buttons.count()

        search_button = None

        for i in range(button_count):
            try:
                el = buttons.nth(i)

                if not await el.is_visible():
                    continue

                text = ""

                try:
                    text = (await el.inner_text()).strip()
                except:
                    pass

                value = await el.get_attribute("value")
                aria = await el.get_attribute("aria-label")

                print(
                    i,
                    "text=", repr(text),
                    "value=", value,
                    "aria=", aria
                )

                combined = f"{text} {value} {aria}".lower()

                if "search" in combined:
                    search_button = el
            except:
                pass

        if not search_button:
            print("\nERROR: Search button not found.")
            await page.screenshot(
                path="ingredients_before_search.png",
                full_page=True
            )

            await asyncio.to_thread(input("Press ENTER to close..."))
            await browser.close()
            return

        print("\nClicking Search...")

        old_url = page.url

        await search_button.click()

        try:
            await page.wait_for_load_state(
                "domcontentloaded",
                timeout=15000
            )
        except:
            pass

        await page.wait_for_timeout(5000)

        print("\n=== SEARCH COMPLETED ===")
        print("OLD URL:", old_url)
        print("NEW URL:", page.url)
        print("TITLE:", await page.title())

        print("\n=== ALL LINKS ===")

        links = page.locator("a")
        link_count = await links.count()

        for i in range(link_count):
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

        print("\n=== PAGE TEXT ===")

        body_text = await page.locator("body").inner_text()
        print(body_text[:15000])

        print("\n=== SAVING SEARCH RESULT HTML ===")

        html = await page.content()

        with open(
            "ingredients_search_result.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(html)

        await page.screenshot(
            path="ingredients_search_result.png",
            full_page=True
        )

        print("Saved:")
        print("  ingredients_search_result.html")
        print("  ingredients_search_result.png")

        print("\nBrowser will remain open.")
        await asyncio.to_thread(input("Press ENTER to close..."))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())