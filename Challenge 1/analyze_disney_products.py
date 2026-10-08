import json

with open("disney_api_pages.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

products_by_id = {}

for page in raw["pages"]:
    data = page.get("data", {})

    for product in data.get("products", []):
        product_id = product.get("productId", "")

        if product_id:
            products_by_id[product_id] = product

print("UNIQUE PRODUCTS:", len(products_by_id))

print("\n" + "=" * 80)
print("MIAMI / LONDON PRODUCTS")
print("=" * 80)

for product_id, product in products_by_id.items():

    name = (
        product.get("productDisplayName")
        or product.get("productName")
        or ""
    )

    text = name.lower()

    if "miami" in text or "london" in text:
        print("\nPRODUCT ID:", product_id)
        print("NAME:", name)

        for itinerary in product.get("itineraries", []):

            print("ITINERARY ID:", itinerary.get("itineraryId"))
            print("NUMBER OF SAILINGS:", itinerary.get("numberOfSailings"))
            print("PORTS OF CALL:", itinerary.get("portsOfCall"))
            print("ONE WAY:", itinerary.get("oneWayItinerary"))
            print("TWO STOPS:", itinerary.get("twoStopsItinerary"))

print("\n" + "=" * 80)
print("PRODUCT SUMMARY")
print("=" * 80)

for product_id, product in products_by_id.items():

    name = (
        product.get("productDisplayName")
        or product.get("productName")
        or ""
    )

    itineraries = product.get("itineraries", [])

    sailing_count = sum(
        len(itinerary.get("sailings", []))
        for itinerary in itineraries
    )

    ports = []

    for itinerary in itineraries:
        for port in itinerary.get("portsOfCall", []):
            if port and port not in ports:
                ports.append(port)

    print(
        f"{product_id} | "
        f"{name} | "
        f"sailings={sailing_count} | "
        f"ports={ports}"
    )