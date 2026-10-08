import json
import re


INPUT_FILE = "disney_api_pages.json"


def find_values(obj, path="root"):
    if isinstance(obj, dict):

        for key, value in obj.items():

            key_lower = str(key).lower()

            # Show keys that might contain date/port information
            if any(word in key_lower for word in [
                "date",
                "departure",
                "arrival",
                "port",
                "origin",
                "start",
                "end",
                "sail"
            ]):
                print(
                    f"\nKEY FOUND: {path}.{key}"
                )

                if isinstance(value, (dict, list)):
                    print(
                        "TYPE:",
                        type(value).__name__,
                        "ITEMS:",
                        len(value)
                    )

                    print(
                        json.dumps(
                            value,
                            indent=2,
                            ensure_ascii=False
                        )[:5000]
                    )

                else:
                    print(
                        "VALUE:",
                        repr(value)
                    )

            find_values(
                value,
                f"{path}.{key}"
            )

    elif isinstance(obj, list):

        for index, item in enumerate(obj[:20]):

            find_values(
                item,
                f"{path}[{index}]"
            )


def main():

    print(
        "Loading disney_api_pages.json..."
    )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    print(
        "Loaded successfully."
    )

    print()
    print(
        "Searching API response for "
        "date / departure / arrival / port fields..."
    )

    find_values(data)

    print()
    print(
        "DONE"
    )


if __name__ == "__main__":
    main()