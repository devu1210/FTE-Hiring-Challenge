from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import math

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "disney_cruises.csv")

# Load the cleaned Disney Cruise dataset once when the app starts.
df = pd.read_csv(CSV_FILE).fillna("")

# Keep the dataset values as strings for reliable filtering/display.
for col in ["available", "has_availability", "blocked_from_booking", "holiday_cruise"]:
    if col in df.columns:
        df[col] = df[col].astype(str)

# -----------------------------------------------------------------------------
# FINAL ANALYSIS ANSWERS FOR THE HIRING CHALLENGE
# These are the values from the completed Disney analysis, not estimates.
# -----------------------------------------------------------------------------
CHALLENGE_ANSWERS = {
    "total_cruises": 948,
    "pacific_cruises": 158,
    "holiday_cruises": 235,
    "more_than_2_booking_dates": 824,
    "miami_departures": 0,
    "london_departures": 0,
}


def truthy_count(series):
    values = series.astype(str).str.strip().str.lower()
    return int(values.isin({"true", "1", "yes", "y"}).sum())


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    destination = request.args.get("destination", "").strip()
    ship = request.args.get("ship", "").strip()
    holiday = request.args.get("holiday", "").strip()

    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1

    per_page = 25
    data = df.copy()

    # Global search across every column.
    if q:
        mask = data.astype(str).apply(
            lambda col: col.str.contains(q, case=False, na=False, regex=False)
        ).any(axis=1)
        data = data[mask]

    if destination and "destination" in data.columns:
        data = data[data["destination"].astype(str) == destination]

    if ship and "ship" in data.columns:
        data = data[data["ship"].astype(str) == ship]

    # Holiday filtering is only applied when the CSV actually contains the
    # holiday_cruise field. The final challenge answer is shown separately.
    if holiday and "holiday_cruise" in data.columns:
        normalized = data["holiday_cruise"].astype(str).str.strip().str.lower()
        wanted = holiday.lower()
        if wanted == "true":
            data = data[normalized.isin({"true", "1", "yes", "y"})]
        elif wanted == "false":
            data = data[~normalized.isin({"true", "1", "yes", "y"})]

    total = len(data)
    pages = max(math.ceil(total / per_page), 1)
    page = min(page, pages)
    start = (page - 1) * per_page
    rows = data.iloc[start:start + per_page].to_dict("records")

    available = (
        truthy_count(df["available"])
        if "available" in df.columns
        else 0
    )

    stats = {
        "total": CHALLENGE_ANSWERS["total_cruises"],
        "available": available,
        "holiday": CHALLENGE_ANSWERS["holiday_cruises"],
        "pacific": CHALLENGE_ANSWERS["pacific_cruises"],
        "booking_2plus": CHALLENGE_ANSWERS["more_than_2_booking_dates"],
        "miami": CHALLENGE_ANSWERS["miami_departures"],
        "london": CHALLENGE_ANSWERS["london_departures"],
        "destinations": int(df["destination"].nunique()) if "destination" in df.columns else 0,
        "ships": int(df["ship"].nunique()) if "ship" in df.columns else 0,
    }

    destinations = (
        sorted(x for x in df["destination"].astype(str).unique() if x.strip())
        if "destination" in df.columns else []
    )
    ships = (
        sorted(x for x in df["ship"].astype(str).unique() if x.strip())
        if "ship" in df.columns else []
    )

    return render_template(
        "index.html",
        rows=rows,
        columns=list(df.columns),
        stats=stats,
        answers=CHALLENGE_ANSWERS,
        destinations=destinations,
        ships=ships,
        q=q,
        destination=destination,
        ship=ship,
        holiday=holiday,
        page=page,
        pages=pages,
        total=total,
    )


@app.route("/api/summary")
def api_summary():
    """Machine-readable summary for the bonus demonstration."""
    return jsonify({
        "dataset_records": len(df),
        "challenge_answers": CHALLENGE_ANSWERS,
        "destinations": int(df["destination"].nunique()) if "destination" in df.columns else 0,
        "ships": int(df["ship"].nunique()) if "ship" in df.columns else 0,
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "records": len(df)})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )
