import json

with open("disney_api_pages.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

products = {}

for page in raw["pages"]:
    for product in page.get("data", {}).get("products", []):
        pid = product.get("productId")

        if pid:
            products[pid] = product

print("=" * 80)
print("CHECKING DEPARTURE-RELATED DATA")
print("=" * 80)

for pid, product in products.items():

    name = (
        product.get("productDisplayName")
        or product.get("productName")
        or ""
    )

    if "miami" in name.lower() or "southampton" in name.lower() or "london" in name.lower():

        print("\nPRODUCT ID:", pid)
        print("PRODUCT NAME:", name)

        for itinerary in product.get("itineraries", []):

            print("\nITINERARY ID:", itinerary.get("itineraryId"))
            print("ONE WAY:", itinerary.get("oneWayItinerary"))
            print("TWO STOPS:", itinerary.get("twoStopsItinerary"))
            print("PORTS OF CALL:", itinerary.get("portsOfCall"))

            sailings = itinerary.get("sailings", [])

            if sailings:
                s = sailings[0]

                print("SAILING ID:", s.get("sailingId"))
                print("DESTINATION:", s.get("destination"))
                print("GEO AREA:", s.get("geoArea"))
                print("PACKAGE CODE:", s.get("packageCode"))
                print("SAILING KEYS:", list(s.keys()))

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)