import json
import logging
import os

import requests

# Access code for the coaster API
strkeycode = os.environ.get("COASTERKEYCODE")

# Defining a params dict for the parameters to be sent to the API
HEADERS = {'keycode': strkeycode}


def call(command, parameters):
    """Calls the specified function on the coaster API with the given (dictionary of) parameters, returning the API's reponse."""
    try:
        URL = "http://api.coasteramer.com/api/product/" + command + "?"
        for arg in parameters:
            URL += arg + "=" + parameters[arg] + "&"
        r = requests.get(url=URL, headers=HEADERS)
        data = r.json()
        return data
    except Exception as e:
        logging.error("Coaster API call failed")
        logging.error(e)
