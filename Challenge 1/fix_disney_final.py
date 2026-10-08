import json
import re
import pandas as pd


CSV_FILE = "disney_cruises.csv"
API_FILE = "disney_api_pages.json"


def clean(value):
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()

# LOAD FILES
  
df = pd.read_csv(
    CSV_FILE,
    dtype=str
).fillna("")


with open(
    API_FILE,
    "r",
    encoding="utf-8"
) as f:
    api_data = json.load(f)


print("Loaded CSV rows:", len(df))


# BUILD SAILING -> DATE LOOKUP FROM ALL RAW API DATA
  
date_lookup = {}


for page_item in api_data.get(
    "pages",
    []
):

    data = page_item.get(
        "data",
        {}
    )


    for product in data.get(
        "products",
        []
    ):

        product_id = clean(
            product.get(
                "productId"
            )
        )


        product_name = clean(
            product.get(
                "productDisplayName"
            )
            or product.get(
                "productName"
            )
        )


        for itinerary in product.get(
            "itineraries",
            []
        ):

            itinerary_id = clean(
                itinerary.get(
                    "itineraryId"
                )
            )


            for sailing in itinerary.get(
                "sailings",
                []
            ):

                sailing_id = clean(
                    sailing.get(
                        "sailingId"
                    )
                )


                if not sailing_id:
                    continue


                date_lookup[sailing_id] = {
                    "sailing_date":
                        clean(
                            sailing.get(
                                "sailDateFrom"
                            )
                        ),

                    "sailing_end_date":
                        clean(
                            sailing.get(
                                "sailDateTo"
                            )
                        ),

                    "product_id":
                        product_id,

                    "product_name":
                        product_name,

                    "itinerary_id":
                        itinerary_id
                }


print(
    "Sailing records found in raw API:",
    len(date_lookup)
)

# FILL MISSING DATES
  
missing_before = (
    df["sailing_date"]
    .astype(str)
    .str.strip()
    .eq("")
    .sum()
)


print(
    "Missing sailing dates before fix:",
    missing_before
)


fixed = 0


for index, row in df.iterrows():

    sailing_id = clean(
        row["sailing_id"]
    )


    if (
        not clean(
            row["sailing_date"]
        )
        and sailing_id in date_lookup
    ):

        info = date_lookup[
            sailing_id
        ]


        if info["sailing_date"]:

            df.at[
                index,
                "sailing_date"
            ] = info[
                "sailing_date"
            ]

            fixed += 1


        if (
            not clean(
                row["sailing_end_date"]
            )
            and info["sailing_end_date"]
        ):

            df.at[
                index,
                "sailing_end_date"
            ] = info[
                "sailing_end_date"
            ]


print(
    "Dates fixed from raw API:",
    fixed
)


# IMPROVE HOLIDAY DETECTION
  
holiday_keywords = [
    "halloween",
    "merrytime",
    "christmas",
    "holiday",
    "thanksgiving",
    "new year",
    "new year's",
    "very merrytime"
]


holiday_count = 0


for index, row in df.iterrows():

    combined = " ".join([
        clean(row.get("product_name", "")),
        clean(row.get("itinerary_name", "")),
        clean(row.get("product_id", "")),
        clean(row.get("itinerary_id", "")),
        clean(row.get("ports_of_call", ""))
    ]).lower()


    is_holiday = any(
        keyword in combined
        for keyword in holiday_keywords
    )


    df.at[
        index,
        "holiday_cruise"
    ] = (
        "Yes"
        if is_holiday
        else "No"
    )


    if is_holiday:
        holiday_count += 1


print(
    "Holiday cruise sailings:",
    holiday_count
)


# CLEAN ALL DATA
  
for column in df.columns:

    df[column] = (
        df[column]
        .fillna("")
        .astype(str)
        .str.replace(
            r"\s+",
            " ",
            regex=True
        )
        .str.strip()
    )


# REMOVE DUPLICATES
  
before = len(df)


df = df.drop_duplicates(
    subset=["sailing_id"],
    keep="first"
)


print(
    "Duplicates removed:",
    before - len(df)
)


# SAVE
  
df.to_csv(
    "disney_temp.csv",
    index=False,
    encoding="utf-8-sig"
)


df.to_csv(
    "disney_cruises.csv",
    index=False,
    encoding="utf-8-sig"
)


# FINAL CHECK
  
print()
print(
    "================================"
)
print(
    "FINAL DISNEY DATA CHECK"
)
print(
    "================================"
)


for column in [
    "sailing_id",
    "product_name",
    "destination",
    "sailing_date",
    "sailing_end_date",
    "departure_port",
    "arrival_port"
]:

    empty = (
        df[column]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )


    print(
        f"{column}: empty={empty}"
    )


print()
print(
    "Rows:",
    len(df)
)


print(
    "Duplicate sailing IDs:",
    df["sailing_id"].duplicated().sum()
)


print(
    "Holiday cruise sailings:",
    (
        df["holiday_cruise"]
        .eq("Yes")
        .sum()
    )
)


print()
print(
    "Missing-date records:"
)


missing = df[
    df["sailing_date"]
    .astype(str)
    .str.strip()
    .eq("")
]


if missing.empty:

    print(
        "NONE"
    )

else:

    print(
        missing[
            [
                "product_id",
                "product_name",
                "itinerary_id",
                "sailing_id"
            ]
        ].to_string(
            index=False
        )
    )


print()
print(
    "Files updated:"
)

print(
    " - disney_cruises.csv"
)

print(
    " - disney_temp.csv"
)