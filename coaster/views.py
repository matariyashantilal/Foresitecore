import datetime
import json
import logging
import os
import tempfile
from pathlib import Path
from time import sleep

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from coaster import api
from coaster import scraper

# Set up logging config
logging.basicConfig(filename='coaster.log', level=logging.WARNING)

# scraper class object
scrapeObj = scraper.Scraper()


def scrape_all_product(request):
    """Scrape all the product.
    """
    return_me = ""
    # get the category json
    jObj = api.call("GetCategoryList", {})
    scrapeObj.resetcounts()
    for p in jObj:
        args = {'CategoryCode': p["CategoryCode"]}
        data = api.call("GetFilter", args)
        filter = json.dumps(data).strip('"')
        # Call the coaster API to get all the info for the products into a dictionary of objects
        args = {'filterCode': filter}
        products = api.call("GetProductList", args)
        for product in products:
            try:
                pNum = product["ProductNumber"]
                scrapedata = scrapeObj.scrape(pNum)
            except Exception as e:
                logging.error(
                    "ERROR: Could not read pNum from product " + product)
                return_me += "ERROR: Could not read pNum from product " + product + "<br>"
        return_me = "Scraped " + str(scrapeObj.count_scraped) + " Skipped " + str(scrapeObj.count_skipped) + \
            " Used cache:" + str(scrapeObj.count_used_cache) + \
            " Total processed:" + str(scrapeObj.count_total)
    return HttpResponse(return_me)


def scrape(request, productID):
    """Scrape product based on productID.
    """
    scrapedata = scrapeObj.scrape(productID)
    return HttpResponse("Scraped:"+productID)


def get_supplier_inventory_counts(request, refreshcache=False):
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
        print("Exception Inventory failed to save")
        print(e)
        return HttpResponse("Exception Inventory failed to save")
