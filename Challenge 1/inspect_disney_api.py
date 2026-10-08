from playwright.sync_api import sync_playwright
import json

URL = "https://disneycruise.disney.go.com/en-in/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    def capture_response(response):
        if "available-products" in response.url:
            print("\n========================================")
            print("AVAILABLE PRODUCTS RESPONSE")
            print("========================================")
            print("STATUS:", response.status)
            print("URL:", response.url)

            try:
                data = response.json()

                with open("disney_full_response.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print("Saved: disney_full_response.json")
                print("Top-level keys:", list(data.keys()))

                if "products" in data:
                    print("Products:", len(data["products"]))

                    for i, product in enumerate(data["products"][:3]):
                        print("\nPRODUCT", i)
                        print("Name:", product.get("productName"))
                        print("Keys:", list(product.keys()))

                        itineraries = product.get("itineraries", [])

                        for j, itinerary in enumerate(itineraries[:2]):
                            print("\n  ITINERARY", j)
                            print("  Keys:", list(itinerary.keys()))
                            print("  Sailings:", len(itinerary.get("sailings", [])))

                            print(
                                "  Number of sailings:",
                                itinerary.get("numberOfSailings")
                            )

                            print(
                                "  Ports of call:",
                                itinerary.get("portsOfCall")
                            )

                            if itinerary.get("sailings"):
                                sailing = itinerary["sailings"][0]

                                print("\n  FIRST SAILING KEYS:")
                                print(list(sailing.keys()))

                                print("\n  FIRST SAILING:")
                                print(json.dumps(
                                    sailing,
                                    indent=2,
                                    ensure_ascii=False
                                )[:5000])

            except Exception as e:
                print("ERROR:", e)

    page.on("response", capture_response)

    print("Opening Disney...")
    page.goto(
        URL,
        wait_until="domcontentloaded",
        timeout=120000
    )

    page.wait_for_timeout(5000)

    print("Clicking View Dates...")

    try:
        page.get_by_role(
            "button",
            name="View Dates"
        ).first.click()
    except Exception as e:
        print("View Dates error:", e)

    page.wait_for_timeout(15000)

    input("\nPress ENTER to close...")

    browser.close()