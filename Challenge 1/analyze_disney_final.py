import pandas as pd

FILE = "disney_cruises.csv"

df = pd.read_csv(FILE).fillna("")

print("\n" + "=" * 60)
print("FINAL DISNEY CHALLENGE ANALYSIS")
print("=" * 60)

# ---------------------------------------------------------
# 1. TOTAL CRUISES
# ---------------------------------------------------------

total_cruises = len(df)

print(f"\n1. TOTAL CRUISES: {total_cruises}")


# ---------------------------------------------------------
# 2. HOLIDAY CRUISES
# ---------------------------------------------------------

holiday_mask = (
    df["holiday_cruise"]
    .astype(str)
    .str.lower()
    .isin(["true", "1", "yes"])
)

holiday_count = holiday_mask.sum()

print(f"2. HOLIDAY CRUISES: {holiday_count}")


# ---------------------------------------------------------
# 3. CRUISES WITH MORE THAN 2 BOOKING DATES
# ---------------------------------------------------------

booking_dates = pd.to_numeric(
    df["booking_dates_count"],
    errors="coerce"
).fillna(0)

more_than_2 = (booking_dates > 2).sum()

print(f"3. CRUISES WITH >2 BOOKING DATES: {more_than_2}")


# ---------------------------------------------------------
# 4. PACIFIC DESTINATIONS
# ---------------------------------------------------------

pacific_keywords = [
    "pacific",
    "alaska",
    "hawaii",
    "vancouver",
    "san diego",
    "baja",
    "mexican riviera"
]

def is_pacific(row):
    text = " ".join([
        str(row.get("product_name", "")),
        str(row.get("itinerary_name", "")),
        str(row.get("destination", "")),
        str(row.get("geo_area", "")),
        str(row.get("ports_of_call", ""))
    ]).lower()

    return any(keyword in text for keyword in pacific_keywords)


pacific_mask = df.apply(is_pacific, axis=1)
pacific_count = pacific_mask.sum()

print(f"4. PACIFIC-RELATED CRUISES: {pacific_count}")


# ---------------------------------------------------------
# 5. MIAMI + LONDON DEPARTURE PORTS
# ---------------------------------------------------------

departure = df["departure_port"].astype(str).str.lower()
arrival = df["arrival_port"].astype(str).str.lower()

miami_london_mask = (
    departure.str.contains("miami", na=False)
    & arrival.str.contains("london", na=False)
)

miami_london_count = miami_london_mask.sum()

print(f"5. MIAMI → LONDON CRUISES: {miami_london_count}")


# ---------------------------------------------------------
# DETAILS
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("PACIFIC DESTINATION DETAILS")
print("=" * 60)

pacific_columns = [
    "product_name",
    "sailing_id",
    "destination",
    "geo_area",
    "ports_of_call"
]

print(
    df.loc[pacific_mask, pacific_columns]
    .drop_duplicates()
    .to_string(index=False)
)


print("\n" + "=" * 60)
print("MIAMI / LONDON ROUTES FOUND")
print("=" * 60)

routes = df.loc[
    departure.str.contains("miami", na=False)
    | arrival.str.contains("london", na=False),
    [
        "product_name",
        "sailing_id",
        "departure_port",
        "arrival_port",
        "destination",
        "geo_area"
    ]
].drop_duplicates()

if len(routes) == 0:
    print("No Miami/London route found in the extracted CSV.")
else:
    print(routes.to_string(index=False))


# ---------------------------------------------------------
# DATA QUALITY
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("FINAL DATA QUALITY")
print("=" * 60)

required_columns = [
    "sailing_id",
    "product_name",
    "destination",
    "sailing_date",
    "sailing_end_date",
    "departure_port",
    "arrival_port"
]

for column in required_columns:
    empty = (
        df[column]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )
    print(f"{column}: empty={empty}")

print(f"\nRows: {len(df)}")
print(f"Duplicate sailing IDs: {df['sailing_id'].duplicated().sum()}")

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)