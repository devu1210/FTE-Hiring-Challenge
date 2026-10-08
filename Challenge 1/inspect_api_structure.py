import json

with open("disney_api_pages.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("ROOT TYPE:", type(data).__name__)
print("ROOT KEYS:")
print(list(data.keys())[:30])

print("\n" + "=" * 70)

for key, value in list(data.items())[:5]:
    print("\nKEY:", key)
    print("VALUE TYPE:", type(value).__name__)

    if isinstance(value, dict):
        print("VALUE KEYS:")
        print(list(value.keys())[:30])

    elif isinstance(value, list):
        print("LIST LENGTH:", len(value))

        if value:
            print("FIRST ITEM TYPE:", type(value[0]).__name__)

            if isinstance(value[0], dict):
                print("FIRST ITEM KEYS:")
                print(list(value[0].keys())[:30])

    else:
        print("VALUE:", str(value)[:500])