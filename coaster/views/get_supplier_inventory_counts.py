import json
import os

from coaster.views import api, inventory_count, scraper
from django.conf import settings
from django.http import HttpResponse
from shopify_wrapper import views as shopify
from shopify_wrapper.views import productObj

# scraper class object
scrapeObj = scraper.Scraper()


def get_supplier_inventory_counts(request, refreshcache=False):
    """Coaster inventory counts for warehouse
    """
    returnme = ""
    try:
        thefilename = "inventory_coaster.json"
        thefullpath = os.path.join(
            settings.COASTER_DIRECTORY_PATH, thefilename)
        returnme = ""
        args = {'warehouse': "LD"}
        data = api.call("GetInventoryList", args)
        with open(os.path.join(settings.COASTER_DIRECTORY_PATH, thefilename), 'w') as outfile:
            json.dump(data, outfile)
        for warehouse in data:
            returnme += "Saved Coaster inventory counts for warehouse:" + \
                warehouse["WarehouseCode"] + "<p>"
        return HttpResponse(returnme)
    except Exception as e:
        return HttpResponse("Exception Inventory failed to save")
