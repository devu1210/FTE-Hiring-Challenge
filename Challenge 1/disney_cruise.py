import asyncio
import json
import re
from collections import Counter

import pandas as pd
from playwright.async_api import async_playwright


URL = "https://disneycruise.disney.go.com/en-in/"

AVAILABLE_PRODUCTS_URL = (
    "https://disneycruise.disney.go.com/"
    "dcl-apps-productavail-vas/available-products/"
)

AVAILABLE_SAILINGS_URL = (
    "https://disneycruise.disney.go.com/"
    "dcl-apps-productavail-vas/available-sailings/"
)

TOTAL_EXPECTED_API_PAGES = 35


 # HELPERS
 
def clean_text(value):
    if value is None:
        return ""

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, (list, tuple)):
        values = []

        for item in value:
            cleaned = clean_text(item)

            if cleaned:
                values.append(cleaned)

        return ", ".join(values)

    if isinstance(value, dict):
        for key in [
            "name",
            "displayName",
            "portName",
            "city",
            "label",
            "value",
            "code"
        ]:
            if key in value and value[key]:
                return clean_text(value[key])

        return json.dumps(
            value,
            ensure_ascii=False
        )

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def extract_value(obj, possible_keys):
    """
    Recursively searches a JSON object for the first
    non-empty value matching one of the supplied keys.
    """

    if isinstance(obj, dict):

        for key in possible_keys:

            if key in obj:

                value = obj[key]

                if value not in (
                    None,
                    "",
                    [],
                    {}
                ):

                    cleaned = clean_text(value)

                    if cleaned:
                        return cleaned

        for value in obj.values():

            result = extract_value(
                value,
                possible_keys
            )

            if result:
                return result

    elif isinstance(obj, list):

        for item in obj:

            result = extract_value(
                item,
                possible_keys
            )

            if result:
                return result

    return ""


 # DATE EXTRACTION
 
def extract_sailing_dates(sailing):
    """
    Disney available-sailings API exposes the actual
    cruise dates as:

        sailDateFrom
        sailDateTo
    """

    start_date = clean_text(
        sailing.get("sailDateFrom")
    )

    end_date = clean_text(
        sailing.get("sailDateTo")
    )

    if not start_date:

        start_date = extract_value(
            sailing,
            [
                "sailingDate",
                "sailing_date",
                "departureDate",
                "departure_date",
                "startDate",
                "start_date",
                "sailDate",
                "sail_date",
                "date",
                "departureDateTime",
                "departure_date_time",
                "startDateTime",
                "start_date_time"
            ]
        )

    if not end_date:

        end_date = extract_value(
            sailing,
            [
                "sailDateTo",
                "sailingEndDate",
                "sailing_end_date",
                "arrivalDate",
                "arrival_date",
                "endDate",
                "end_date"
            ]
        )

    return start_date, end_date


 # PORT EXTRACTION FROM NESTED JSON
 
def find_port_by_type(obj, wanted_types):

    if isinstance(obj, dict):

        type_value = ""

        for key in [
            "portType",
            "port_type",
            "type",
            "locationType",
            "location_type"
        ]:

            if key in obj:

                type_value = clean_text(
                    obj[key]
                ).upper()

                break

        if type_value in wanted_types:

            for key in [
                "name",
                "portName",
                "port_name",
                "displayName",
                "city",
                "code"
            ]:

                if obj.get(key):

                    return clean_text(
                        obj[key]
                    )

        for value in obj.values():

            result = find_port_by_type(
                value,
                wanted_types
            )

            if result:
                return result

    elif isinstance(obj, list):

        for item in obj:

            result = find_port_by_type(
                item,
                wanted_types
            )

            if result:
                return result

    return ""


def extract_departure_port_from_sailing(sailing):

    value = extract_value(
        sailing,
        [
            "departurePort",
            "departure_port",
            "departureLocation",
            "departure_location",
            "originPort",
            "origin_port",
            "originLocation",
            "origin_location",
            "embarkationPort",
            "embarkation_port",
            "portOfDeparture",
            "port_of_departure"
        ]
    )

    if value:
        return value

    return find_port_by_type(
        sailing,
        [
            "DEPARTURE",
            "EMBARKATION",
            "ORIGIN"
        ]
    )


def extract_arrival_port_from_sailing(sailing):

    value = extract_value(
        sailing,
        [
            "arrivalPort",
            "arrival_port",
            "arrivalLocation",
            "arrival_location",
            "destinationPort",
            "destination_port",
            "destinationLocation",
            "destination_location",
            "disembarkationPort",
            "disembarkation_port",
            "portOfArrival",
            "port_of_arrival"
        ]
    )

    if value:
        return value

    return find_port_by_type(
        sailing,
        [
            "ARRIVAL",
            "DISEMBARKATION",
            "DESTINATION"
        ]
    )


 # PRODUCT NAME -> DEPARTURE / ARRIVAL
 
def normalize_port_name(value):

    value = clean_text(value)

    if not value:
        return ""

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    return value


def parse_ports_from_product_name(product_name):

    product_name = clean_text(
        product_name
    )

    if not product_name:
        return "", ""



    # Pattern:
    # "Cruise from Barcelona ending in Southampton"
    
    match = re.search(
        r"\bfrom\s+(.+?)\s+ending\s+in\s+(.+?)\s*$",
        product_name,
        flags=re.IGNORECASE
    )

    if match:

        departure = normalize_port_name(
            match.group(1)
        )

        arrival = normalize_port_name(
            match.group(2)
        )

        return departure, arrival


    # Pattern:
    # "Cruise from Miami to London"
    
    match = re.search(
        r"\bfrom\s+(.+?)\s+to\s+(.+?)\s*$",
        product_name,
        flags=re.IGNORECASE
    )

    if match:

        departure = normalize_port_name(
            match.group(1)
        )

        arrival = normalize_port_name(
            match.group(2)
        )

        return departure, arrival


        # Pattern:
    # "Cruise from Singapore"
    #
    # Normal round-trip cruise.
    # Arrival will initially be same as departure.
    
    match = re.search(
        r"\bfrom\s+(.+?)\s*$",
        product_name,
        flags=re.IGNORECASE
    )

    if match:

        departure = normalize_port_name(
            match.group(1)
        )

        return departure, departure


    return "", ""


 # ITINERARY PORT FALLBACK
 
def derive_ports(
    product_name,
    itinerary,
    sailing
):

    # First try actual sailing-level data.

    departure = extract_departure_port_from_sailing(
        sailing
    )

    arrival = extract_arrival_port_from_sailing(
        sailing
    )

    if departure and arrival:
        return departure, arrival


    # Then parse the product name.

    name_departure, name_arrival = (
        parse_ports_from_product_name(
            product_name
        )
    )

    if not departure:
        departure = name_departure

    if not arrival:
        arrival = name_arrival


        # Itinerary one-way information
    
    one_way = itinerary.get(
        "oneWayItinerary"
    )

    if isinstance(one_way, str):

        one_way = (
            one_way.lower()
            == "true"
        )


        # If it is a normal round trip, arrival is normally
    # the same port as departure.
    
    if (
        not arrival
        and departure
        and one_way is not True
    ):

        arrival = departure


        # Use portsOfCall as an additional fallback for
    # one-way itineraries.
    #
    # Important:
    # We do NOT replace an explicitly known arrival.
    
    ports_of_call = itinerary.get(
        "portsOfCall",
        []
    )

    if isinstance(
        ports_of_call,
        list
    ):

        cleaned_ports = [
            clean_text(x)
            for x in ports_of_call
            if clean_text(x)
        ]

        if (
            one_way is True
            and not arrival
            and cleaned_ports
        ):

            arrival = cleaned_ports[-1]


    return (
        clean_text(departure),
        clean_text(arrival)
    )


 # SHIP
 
def get_ship_name(sailing):

    ship = sailing.get(
        "ship",
        {}
    )

    if isinstance(ship, dict):

        return clean_text(
            ship.get("name")
            or ship.get("displayName")
            or ship.get("shipName")
        )

    return clean_text(ship)


 # HOLIDAY DETECTION
 
def detect_holiday_cruise(
    product_name,
    itinerary_name
):

    text = (
        clean_text(product_name)
        + " "
        + clean_text(itinerary_name)
    ).lower()

    holiday_terms = [
        "halloween",
        "merrytime",
        "christmas",
        "holiday",
        "thanksgiving",
        "new year's",
        "new year",
        "very merrytime"
    ]

    for term in holiday_terms:

        if term in text:
            return "Yes"

    return "No"


 # API REQUEST
 
async def fetch_available_sailings(
    page,
    product_id,
    itinerary_id,
    max_retries=3
):

    body = {
        "currency": "INR",

        "filters": [],

        "partyMix": [
            {
                "accessible": False,
                "adultCount": 2,
                "childCount": 0,
                "nonAdultAges": [],
                "partyMixId": "0"
            }
        ],

        "region": "INTL",

        "storeId": "DCL",

        "affiliations": [],

        "itineraryId": itinerary_id,

        "productId": product_id,

        "includeAdvancedBookingPrices": True
    }


    for attempt in range(
        1,
        max_retries + 1
    ):

        try:

            result = await page.evaluate(
                """
                async ({url, body}) => {

                    const response =
                        await fetch(
                            url,
                            {
                                method: "POST",
                                headers: {
                                    "Content-Type":
                                        "application/json"
                                },
                                body:
                                    JSON.stringify(body)
                            }
                        );

                    let data = {};

                    try {

                        data =
                            await response.json();

                    } catch (e) {

                        data = {};

                    }

                    return {
                        status:
                            response.status,

                        data:
                            data
                    };
                }
                """,
                {
                    "url":
                        AVAILABLE_SAILINGS_URL,

                    "body":
                        body
                }
            )


            status = result.get(
                "status"
            )

            data = result.get(
                "data",
                {}
            )


            if status == 200:

                return {
                    "success": True,
                    "status": status,
                    "data": data
                }


            print(
                f"Retry {attempt}/"
                f"{max_retries} | "
                f"{product_id} | "
                f"status={status}"
            )


        except Exception as e:

            print(
                f"Retry {attempt}/"
                f"{max_retries} | "
                f"{product_id} | "
                f"ERROR={e}"
            )


        await page.wait_for_timeout(
            1000 * attempt
        )


    return {
        "success": False,
        "status": None,
        "data": {}
    }


 # MAIN
 
async def main():

    responses = []

    captured_pages = set()


    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100
        )


        page = await browser.new_page(
            viewport={
                "width": 1440,
                "height": 900
            }
        )


          # CAPTURE AVAILABLE-PRODUCTS API
  
        async def capture_products(response):

            if (
                "available-products"
                not in response.url
            ):
                return


            if response.request.method != "POST":
                return


            try:

                post_data = (
                    response.request.post_data
                )

                payload = {}


                if post_data:

                    try:

                        payload = json.loads(
                            post_data
                        )

                    except Exception:
                        pass


                page_number = payload.get(
                    "page"
                )


                data = await response.json()


                if not data.get(
                    "products"
                ):
                    return


                if page_number in captured_pages:
                    return


                captured_pages.add(
                    page_number
                )


                responses.append({
                    "page":
                        page_number,

                    "data":
                        data
                })


                print(
                    f"Captured API page "
                    f"{page_number} | "
                    f"products="
                    f"{len(data.get('products', []))} | "
                    f"total cruises="
                    f"{data.get('totalAvailableCruises')} | "
                    f"total pages="
                    f"{data.get('totalPages')}"
                )


            except Exception as e:

                print(
                    "API capture error:",
                    e
                )


        page.on(
            "response",
            capture_products
        )


          # OPEN DISNEY
  
        print()
        print(
            "================================"
        )
        print(
            "OPENING DISNEY CRUISE"
        )
        print(
            "================================"
        )


        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=120000
        )


        await page.wait_for_timeout(
            5000
        )


          # CLICK VIEW DATES
  
        print()
        print(
            "Clicking View Dates..."
        )


        button = page.get_by_role(
            "button",
            name=re.compile(
                r"View Dates",
                re.IGNORECASE
            )
        )


        button_count = await button.count()


        print(
            "View Dates buttons found:",
            button_count
        )


        if button_count == 0:

            print(
                "ERROR: View Dates button "
                "not found."
            )

            await browser.close()

            return


        await button.first.scroll_into_view_if_needed()

        await page.wait_for_timeout(
            1000
        )


        await button.first.click()


        print(
            "View Dates clicked successfully."
        )


        await page.wait_for_timeout(
            10000
        )


          # LOAD ALL API PAGES
  
        print()
        print(
            "================================"
        )
        print(
            "LOADING CRUISE DATA"
        )
        print(
            "================================"
        )


        previous_api_count = 0
        stable_rounds = 0


        for i in range(120):

            await page.mouse.wheel(
                0,
                3000
            )


            await page.wait_for_timeout(
                1200
            )


            current_api_count = len(
                responses
            )


            print(
                f"Scroll {i + 1}/120 | "
                f"Unique API pages: "
                f"{current_api_count}/"
                f"{TOTAL_EXPECTED_API_PAGES}"
            )


            if current_api_count == previous_api_count:

                stable_rounds += 1

            else:

                stable_rounds = 0


            previous_api_count = (
                current_api_count
            )


            if (
                current_api_count
                >= TOTAL_EXPECTED_API_PAGES
            ):

                print()
                print(
                    "All 35 API pages "
                    "captured."
                )

                break


            if stable_rounds >= 10:

                print(
                    "No new API pages "
                    "detected."
                )

                break


        await page.wait_for_timeout(
            3000
        )


        responses.sort(
            key=lambda x:
                x["page"]
                if x["page"] is not None
                else 9999
        )


          # SAVE RAW PRODUCT DATA
  
        raw_capture = {
            "total_captured_pages":
                len(responses),

            "pages":
                responses
        }


        with open(
            "disney_api_pages.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                raw_capture,
                f,
                indent=2,
                ensure_ascii=False
            )


        print()
        print(
            "Saved raw API data:",
            len(responses),
            "pages"
        )


          # BUILD PRODUCT / ITINERARY LIST
  
        print()
        print(
            "================================"
        )
        print(
            "BUILDING PRODUCT LIST"
        )
        print(
            "================================"
        )


        product_pairs = {}

        base_rows = []


        for captured in responses:

            api_page = captured.get(
                "page",
                ""
            )

            response = captured.get(
                "data",
                {}
            )


            for product in response.get(
                "products",
                []
            ):

                product_id = clean_text(
                    product.get(
                        "productId"
                    )
                )


                product_name = clean_text(
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

                    itinerary_id = clean_text(
                        itinerary.get(
                            "itineraryId"
                        )
                    )


                    itinerary_name = clean_text(
                        itinerary.get(
                            "name"
                        )
                    )


                    ports_of_call = (
                        itinerary.get(
                            "portsOfCall",
                            []
                        )
                    )


                    ports_of_call_text = (
                        clean_text(
                            ports_of_call
                        )
                    )


                    number_of_sailings = (
                        itinerary.get(
                            "numberOfSailings",
                            0
                        )
                    )


                    one_way = itinerary.get(
                        "oneWayItinerary"
                    )


                    pair_key = (
                        product_id,
                        itinerary_id
                    )


                    product_pairs[
                        pair_key
                    ] = {

                        "product_id":
                            product_id,

                        "product_name":
                            product_name,

                        "itinerary_id":
                            itinerary_id,

                        "itinerary_name":
                            itinerary_name,

                        "ports_of_call":
                            ports_of_call_text,

                        "number_of_sailings":
                            number_of_sailings,

                        "one_way":
                            one_way,

                        "holiday_cruise":
                            detect_holiday_cruise(
                                product_name,
                                itinerary_name
                            )
                    }


                    for sailing in itinerary.get(
                        "sailings",
                        []
                    ):

                        sailing_id = clean_text(
                            sailing.get(
                                "sailingId"
                            )
                        )


                        base_rows.append({

                            "api_page":
                                api_page,

                            "product_id":
                                product_id,

                            "product_name":
                                product_name,

                            "itinerary_id":
                                itinerary_id,

                            "itinerary_name":
                                itinerary_name,

                            "ports_of_call":
                                ports_of_call_text,

                            "booking_dates_count":
                                clean_text(
                                    number_of_sailings
                                ),

                            "holiday_cruise":
                                detect_holiday_cruise(
                                    product_name,
                                    itinerary_name
                                ),

                            "sailing_id":
                                sailing_id,

                            "package_id":
                                clean_text(
                                    sailing.get(
                                        "packageId"
                                    )
                                ),

                            "package_code":
                                clean_text(
                                    sailing.get(
                                        "packageCode"
                                    )
                                ),

                            "ship":
                                get_ship_name(
                                    sailing
                                ),

                            "destination":
                                clean_text(
                                    sailing.get(
                                        "destination"
                                    )
                                ),

                            "geo_area":
                                clean_text(
                                    sailing.get(
                                        "geoArea"
                                    )
                                ),

                            "number_of_nights":
                                clean_text(
                                    sailing.get(
                                        "numberOfNights"
                                    )
                                ),

                            "available":
                                clean_text(
                                    sailing.get(
                                        "available"
                                    )
                                ),

                            "has_availability":
                                clean_text(
                                    sailing.get(
                                        "hasAvailability"
                                    )
                                ),

                            "blocked_from_booking":
                                clean_text(
                                    sailing.get(
                                        "blockedFromBooking"
                                    )
                                ),

                            "sailing_date":
                                "",

                            "sailing_end_date":
                                "",

                            "departure_port":
                                "",

                            "arrival_port":
                                ""
                        })


        print(
            "Unique product/itinerary pairs:",
            len(product_pairs)
        )


        print(
            "Raw sailing records:",
            len(base_rows)
        )


          # FETCH ACTUAL SAILING DATA
  
        print()
        print(
            "================================"
        )
        print(
            "FETCHING ACTUAL SAILING DATA"
        )
        print(
            "================================"
        )


        available_sailings_data = []

        pair_list = list(
            product_pairs.keys()
        )


        for index, pair in enumerate(
            pair_list,
            start=1
        ):

            product_id, itinerary_id = pair


            result = await fetch_available_sailings(
                page,
                product_id,
                itinerary_id,
                max_retries=3
            )


            if result.get(
                "success"
            ):

                data = result.get(
                    "data",
                    {}
                )

                sailings = data.get(
                    "sailings",
                    []
                )


                available_sailings_data.append({

                    "product_id":
                        product_id,

                    "itinerary_id":
                        itinerary_id,

                    "data":
                        data

                })


                print(
                    f"[{index}/"
                    f"{len(pair_list)}] "
                    f"{product_id} | "
                    f"sailings="
                    f"{len(sailings)}"
                )


            else:

                print(
                    f"[{index}/"
                    f"{len(pair_list)}] "
                    f"FAILED | "
                    f"{product_id}"
                )


            await page.wait_for_timeout(
                100
            )


          # SAVE AVAILABLE SAILINGS
  
        with open(
            "disney_available_sailings.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                available_sailings_data,
                f,
                indent=2,
                ensure_ascii=False
            )


        print()
        print(
            "Saved available-sailings responses:",
            len(
                available_sailings_data
            )
        )


          # BUILD SAILING LOOKUP
  
        sailing_lookup = {}

        total_available_sailings = 0


        print()
        print(
            "Processing available sailing records..."
        )


        for response_item in (
            available_sailings_data
        ):

            product_id = response_item.get(
                "product_id",
                ""
            )


            itinerary_id = response_item.get(
                "itinerary_id",
                ""
            )


            data = response_item.get(
                "data",
                {}
            )


            sailings = data.get(
                "sailings",
                []
            )


            total_available_sailings += len(
                sailings
            )


            itinerary = product_pairs.get(
                (
                    product_id,
                    itinerary_id
                ),
                {}
            )


            product_name = itinerary.get(
                "product_name",
                ""
            )


            for sailing in sailings:

                if not isinstance(
                    sailing,
                    dict
                ):
                    continue


                sailing_id = clean_text(
                    sailing.get(
                        "sailingId"
                    )
                )


                if not sailing_id:

                    sailing_id = clean_text(
                        sailing.get(
                            "sailingID"
                        )
                    )


                if not sailing_id:

                    sailing_id = clean_text(
                        sailing.get(
                            "id"
                        )
                    )


                if not sailing_id:
                    continue


                   # Actual Disney dates
   
                sailing_date, sailing_end_date = (
                    extract_sailing_dates(
                        sailing
                    )
                )


                # Actual sailing-level ports if available,
                # otherwise product-name / itinerary fallback.
   
                departure_port, arrival_port = (
                    derive_ports(
                        product_name,
                        itinerary,
                        sailing
                    )
                )


                sailing_lookup[
                    sailing_id
                ] = {

                    "sailing_date":
                        sailing_date,

                    "sailing_end_date":
                        sailing_end_date,

                    "departure_port":
                        departure_port,

                    "arrival_port":
                        arrival_port,

                    "raw":
                        sailing,

                    "product_id":
                        product_id,

                    "itinerary_id":
                        itinerary_id
                }


        print(
            "Available sailing records:",
            total_available_sailings
        )


        print(
            "Unique sailing lookup records:",
            len(sailing_lookup)
        )


          # MERGE DATA
  
        print()
        print(
            "================================"
        )
        print(
            "MERGING DATA"
        )
        print(
            "================================"
        )


        for row in base_rows:

            sailing_id = row.get(
                "sailing_id",
                ""
            )


            details = sailing_lookup.get(
                sailing_id
            )


            if details:

                row[
                    "sailing_date"
                ] = details.get(
                    "sailing_date",
                    ""
                )


                row[
                    "sailing_end_date"
                ] = details.get(
                    "sailing_end_date",
                    ""
                )


                row[
                    "departure_port"
                ] = details.get(
                    "departure_port",
                    ""
                )


                row[
                    "arrival_port"
                ] = details.get(
                    "arrival_port",
                    ""
                )


          # DATAFRAME
  
        df = pd.DataFrame(
            base_rows
        )


        if df.empty:

            print(
                "ERROR: No data extracted."
            )

            await browser.close()

            return


          # REMOVE DUPLICATES
  
        before = len(df)


        df = df.drop_duplicates(
            subset=[
                "sailing_id"
            ],
            keep="first"
        )


        after = len(df)


        print(
            "Duplicates removed:",
            before - after
        )


          # CLEAN ALL COLUMNS
  
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


          # FINAL FALLBACK FOR PORTS
  
        for index, row in df.iterrows():

            departure = clean_text(
                row.get(
                    "departure_port",
                    ""
                )
            )

            arrival = clean_text(
                row.get(
                    "arrival_port",
                    ""
                )

            )

            product_name = clean_text(
                row.get(
                    "product_name",
                    ""
                )
            )


            if not departure or not arrival:

                name_departure, name_arrival = (
                    parse_ports_from_product_name(
                        product_name
                    )
                )


                if not departure:
                    departure = name_departure


                if not arrival:
                    arrival = name_arrival


            # Normal round-trip fallback.

            if (
                departure
                and not arrival
            ):

                arrival = departure


            df.at[
                index,
                "departure_port"
            ] = departure


            df.at[
                index,
                "arrival_port"
            ] = arrival


          # TEMP CSV
  
        df.to_csv(
            "disney_temp.csv",
            index=False,
            encoding="utf-8-sig"
        )


          # FINAL CSV
  
        df.to_csv(
            "disney_cruises.csv",
            index=False,
            encoding="utf-8-sig"
        )


        await browser.close()


# FINAL SUMMARY
     
    print()
    print(
        "================================"
    )
    print(
        "DISNEY SCRAPER COMPLETE"
    )
    print(
        "================================"
    )


    print(
        "API pages captured:",
        len(responses)
    )


    print(
        "Expected API pages:",
        TOTAL_EXPECTED_API_PAGES
    )


    print(
        "Raw sailing records:",
        len(base_rows)
    )


    print(
        "Available sailing records:",
        total_available_sailings
    )


    print(
        "Unique sailings:",
        len(df)
    )


    print()
    print(
        "Columns:"
    )


    for column in df.columns:

        print(
            " -",
            column
        )


    print()
    print(
        "Files created:"
    )


    print(
        " - disney_api_pages.json"
    )

    print(
        " - disney_available_sailings.json"
    )

    print(
        " - disney_temp.csv"
    )

    print(
        " - disney_cruises.csv"
    )


         # DATA QUALITY CHECK
     
    print()
    print(
        "================================"
    )
    print(
        "DATA QUALITY CHECK"
    )
    print(
        "================================"
    )


    required_columns = [
        "sailing_id",
        "product_name",
        "destination",
        "sailing_date",
        "sailing_end_date",
        "departure_port",
        "arrival_port"
    ]


    print()
    print(
        "Required column checks:"
    )


    for column in required_columns:

        if column not in df.columns:

            print(
                f" - {column}: MISSING"
            )

        else:

            empty_count = (
                df[column]
                .astype(str)
                .str.strip()
                .eq("")
                .sum()
            )

            print(
                f" - {column}: "
                f"empty={empty_count}"
            )


         # DUPLICATE CHECK
     
    duplicate_count = (
        df["sailing_id"]
        .duplicated()
        .sum()
    )


    print()
    print(
        "Duplicate sailing IDs:",
        duplicate_count
    )


         # DATE CHECK
     
    valid_date_count = (
        pd.to_datetime(
            df["sailing_date"],
            errors="coerce"
        )
        .notna()
        .sum()
    )


    print(
        "Valid sailing dates:",
        valid_date_count,
        "/",
        len(df)
    )


         # PORT CHECK
     
    empty_departure = (
        df["departure_port"]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )


    empty_arrival = (
        df["arrival_port"]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )


    print(
        "Empty departure ports:",
        empty_departure
    )


    print(
        "Empty arrival ports:",
        empty_arrival
    )


         # IMPORTANT ROUTE CHECKS
     
    print()
    print(
        "================================"
    )
    print(
        "ROUTE CHECKS"
    )
    print(
        "================================"
    )


    route_df = df[
        [
            "product_name",
            "departure_port",
            "arrival_port"
        ]
    ].drop_duplicates()


    print()
    print(
        "Miami-related routes:"
    )


    miami_rows = route_df[
        route_df[
            "departure_port"
        ].str.contains(
            "Miami",
            case=False,
            na=False
        )
        |
        route_df[
            "arrival_port"
        ].str.contains(
            "Miami",
            case=False,
            na=False
        )
    ]


    if miami_rows.empty:

        print(
            " - No Miami route found "
            "in extracted data."
        )

    else:

        for _, row in miami_rows.iterrows():

            print(
                " -",
                row["departure_port"],
                "->",
                row["arrival_port"],
                "|",
                row["product_name"]
            )


    print()
    print(
        "London-related routes:"
    )


    london_rows = route_df[
        route_df[
            "departure_port"
        ].str.contains(
            "London",
            case=False,
            na=False
        )
        |
        route_df[
            "arrival_port"
        ].str.contains(
            "London",
            case=False,
            na=False
        )
    ]


    if london_rows.empty:

        print(
            " - No London route found "
            "in extracted data."
        )

    else:

        for _, row in london_rows.iterrows():

            print(
                " -",
                row["departure_port"],
                "->",
                row["arrival_port"],
                "|",
                row["product_name"]
            )


         # HOLIDAY COUNT
     
    holiday_count = (
        df[
            "holiday_cruise"
        ]
        .eq("Yes")
        .sum()
    )


    print()
    print(
        "Holiday cruise sailings:",
        holiday_count
    )


         # BOOKING DATE COUNT
     
    booking_counts = pd.to_numeric(
        df[
            "booking_dates_count"
        ],
        errors="coerce"
    )


    greater_than_two = (
        booking_counts > 2
    ).sum()


    print(
        "Cruises with >2 booking dates:",
        greater_than_two
    )


         # PACIFIC DESTINATION CHECK
     
    pacific_keywords = [
        "pacific",
        "alaska",
        "hawaii",
        "mexican riviera",
        "baja",
        "san diego",
        "vancouver"
    ]


    destination_text = (
        df[
            "destination"
        ]
        .fillna("")
        .astype(str)
        .str.lower()
    )


    pacific_mask = False


    for keyword in pacific_keywords:

        current_mask = (
            destination_text
            .str.contains(
                keyword,
                case=False,
                na=False
            )
        )

        pacific_mask = (
            pacific_mask
            | current_mask
        )


    print(
        "Pacific-related sailing records:",
        int(pacific_mask.sum())
    )


         # SAMPLE
     
    print()
    print(
        "================================"
    )
    print(
        "SAMPLE RECORDS"
    )
    print(
        "================================"
    )


    sample_columns = [
        "product_name",
        "sailing_id",
        "sailing_date",
        "sailing_end_date",
        "departure_port",
        "arrival_port",
        "ship",
        "destination",
        "number_of_nights"
    ]


    print(
        df[
            sample_columns
        ].head(10).to_string(
            index=False
        )
    )


    print()
    print(
        "================================"
    )
    print(
        "DONE"
    )
    print(
        "================================"
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )