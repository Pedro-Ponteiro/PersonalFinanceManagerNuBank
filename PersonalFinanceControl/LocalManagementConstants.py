import os

script_location = os.path.dirname(os.path.abspath(__file__))

CACHE_FOLDER = os.path.join(script_location, "cache")
CACHE_BILL_FILEPATH = os.path.join(CACHE_FOLDER, "open_bill_details.pickle")
SECRETS_LOCATION = os.path.join(script_location, "secrets.prod.json")
