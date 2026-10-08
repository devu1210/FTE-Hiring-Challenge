import json

with open("disney_api_pages.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

pages = raw["pages"]

print("TOTAL PAGES:", len(pages))

seen = set()

for page_item in pages:

    data = page_item.get("data", {})

    if not isinstance(data, dict):
        continue

    products = data.get("products", [])

    for product in products:

        product_id = product.get("productId")

        if product_id in seen:
            continue

        seen.add(product_id)

        print("\n" + "=" * 80)
        print("PRODUCT:", product_id)
        print("NAME:", product.get("productName"))

        itineraries = product.get("itineraries", [])

        print("ITINERARIES:", len(itineraries))

        for itinerary in itineraries:

            print("\nITINERARY KEYS:")
            print(list(itinerary.keys()))

            print("\nPORT / LOCATION FIELDS:")

            found = False

            for key, value in itinerary.items():

                key_lower = str(key).lower()

                if any(word in key_lower for word in [
                    "port",
                    "departure",
                    "arrival",
                    "location",
                    "origin",
                    "destination",
                    "route"
                ]):
                    print(f"{key} = {value}")
                    found = True

            if not found:
                print("No obvious port/location field found.")

        print("=" * 80)

print("\nUNIQUE PRODUCTS:", len(seen))