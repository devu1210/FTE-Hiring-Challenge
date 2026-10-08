import asyncio
from playwright.async_api import async_playwright

URL = "https://www.ingredientsnetwork.com/aadi-giri-pvt-ltd-comp322378.html"


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=False)

        page = await browser.new_page(
            viewport={"width": 1400, "height": 900}
        )

        print("Opening company profile...")
        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        print("\n======================================")
        print("COMPANY PROFILE")
        print("======================================")

        print("URL:", page.url)
        print("TITLE:", await page.title())

        # --------------------------------------------------
        # BASIC COMPANY INFORMATION
        # --------------------------------------------------

        print("\n=== COMPANY NAME ===")

        h1 = page.locator("h1").first

        if await h1.count():
            print(await h1.inner_text())

        # --------------------------------------------------
        # ABOUT SECTION
        # --------------------------------------------------

        print("\n=== ABOUT SECTION ===")

        about = page.locator(
            "text=Company description"
        ).first

        if await about.count():
            parent = about.locator("xpath=..")

            try:
                print(
                    await parent.inner_text()
                )
            except:
                pass

        # --------------------------------------------------
        # QUICK FACTS
        # --------------------------------------------------

        print("\n=== QUICK FACTS ===")

        body = await page.locator("body").inner_text()

        for keyword in [
            "Sales markets",
            "Primary business activity",
            "Affiliated categories"
        ]:

            print("\n---", keyword, "---")

            pos = body.lower().find(
                keyword.lower()
            )

            if pos >= 0:
                print(
                    body[
                        max(0, pos - 300):
                        pos + 1500
                    ]
                )

        # --------------------------------------------------
        # CONTACT SECTION HTML
        # --------------------------------------------------

        print("\n=== CONTACT SECTION ===")

        contact = page.locator(
            "text=Contact information"
        ).first

        if await contact.count():

            # Walk upward to find a reasonable container
            parent = contact.locator(
                "xpath=.."
            )

            for level in range(4):

                try:
                    html = await parent.evaluate(
                        "(el) => el.outerHTML"
                    )

                    print(
                        f"\n--- PARENT LEVEL {level} ---"
                    )

                    print(html[:15000])

                    parent = parent.locator(
                        "xpath=.."
                    )

                except:
                    break

        # --------------------------------------------------
        # ALL LINKS
        # --------------------------------------------------

        print("\n=== LINKS ===")

        links = page.locator("a")

        for i in range(await links.count()):

            try:

                el = links.nth(i)

                text = (
                    await el.inner_text()
                ).strip()

                href = await el.get_attribute(
                    "href"
                )

                if href:

                    if any(
                        x in href.lower()
                        for x in [
                            "mailto:",
                            "tel:",
                            "http://",
                            "https://"
                        ]
                    ):

                        print(
                            i,
                            "TEXT=",
                            repr(text),
                            "HREF=",
                            href
                        )

            except:
                pass

        # --------------------------------------------------
        # IMAGES IN CONTACT SECTION
        # --------------------------------------------------

        print("\n=== CONTACT IMAGES ===")

        images = page.locator(
            "img"
        )

        for i in range(await images.count()):

            try:

                el = images.nth(i)

                src = await el.get_attribute(
                    "src"
                )

                alt = await el.get_attribute(
                    "alt"
                )

                title = await el.get_attribute(
                    "title"
                )

                if src:

                    print(
                        i,
                        "SRC=",
                        src,
                        "ALT=",
                        alt,
                        "TITLE=",
                        title
                    )

            except:
                pass

        # --------------------------------------------------
        # ELEMENTS CONTAINING CONTACT LABELS
        # --------------------------------------------------

        print("\n=== CONTACT LABEL ELEMENTS ===")

        for keyword in [
            "Address",
            "Email",
            "Telephone",
            "Website"
        ]:

            print(
                "\n###",
                keyword,
                "###"
            )

            loc = page.get_by_text(
                keyword,
                exact=True
            )

            print(
                "COUNT:",
                await loc.count()
            )

            for i in range(
                min(await loc.count(), 5)
            ):

                try:

                    el = loc.nth(i)

                    print(
                        await el.evaluate(
                            "(el) => el.outerHTML"
                        )
                    )

                except:
                    pass

        # --------------------------------------------------
        # FULL PAGE HTML
        # --------------------------------------------------

        html = await page.content()

        with open(
            "company_profile_debug.html",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(html)

        print(
            "\nSaved company_profile_debug.html"
        )

        print(
            "\nBrowser remains open."
        )

        await asyncio.to_thread(
            input,
            "Press ENTER to close..."
        )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())