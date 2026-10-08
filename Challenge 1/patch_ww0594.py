import pandas as pd

csv_file = "disney_cruises.csv"

df = pd.read_csv(csv_file)

mask = df["sailing_id"].astype(str).str.strip() == "WW0594"

if mask.sum() != 1:
    raise ValueError(f"Expected exactly 1 WW0594 record, found {mask.sum()}")

df.loc[mask, "sailing_date"] = "2027-09-03"
df.loc[mask, "sailing_end_date"] = "2027-09-10"

df.to_csv(csv_file, index=False)
df.to_csv("disney_temp.csv", index=False)

print("WW0594 patched successfully.")
print(
    df.loc[
        mask,
        [
            "sailing_id",
            "product_name",
            "sailing_date",
            "sailing_end_date",
            "departure_port",
            "arrival_port",
        ],
    ].to_string(index=False)
)

print("\nMissing sailing dates:", df["sailing_date"].isna().sum())
print("Missing ending dates:", df["sailing_end_date"].isna().sum())
print("Duplicate sailing IDs:", df["sailing_id"].duplicated().sum())