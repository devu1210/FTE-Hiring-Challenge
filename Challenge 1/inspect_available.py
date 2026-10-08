import json

with open(
    "disney_available_sailings.json",
    "r",
    encoding="utf-8"
) as f:
    data = json.load(f)

print("Responses:", len(data))

for item in data:

    sailings = item.get(
        "data",
        {}
    ).get(
        "sailings",
        []
    )

    if sailings:

        print()
        print("======================================")
        print("PRODUCT:", item.get("product_id"))
        print("ITINERARY:", item.get("itinerary_id"))
        print("SAILING COUNT:", len(sailings))
        print("======================================")

        print(
            json.dumps(
                sailings[0],
                indent=2,
                ensure_ascii=False
            )
        )

        break