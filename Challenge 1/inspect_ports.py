import json

with open("disney_available_sailings.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    sailings = item.get("data", {}).get("sailings", [])

    if not sailings:
        continue

    s = sailings[0]

    print("\n==============================")
    print("PRODUCT:", item.get("productId"))
    print("ITINERARY:", item.get("itineraryId"))
    print("SAILING:", s.get("sailingId"))

    print("\nTOP LEVEL KEYS:")
    print(list(s.keys()))

    print("\nDATE:")
    print(s.get("sailDateFrom"), "->", s.get("sailDateTo"))

    print("\nPOSSIBLE PORT/LOCATION FIELDS:")
    for key, value in s.items():
        key_lower = key.lower()
        if any(x in key_lower for x in [
            "port", "location", "departure", "arrival",
            "origin", "destination", "itinerary", "route"
        ]):
            print(key, "=", value)

    print("==============================")

    break