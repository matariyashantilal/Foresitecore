import json
import logging
import os

from coaster.views import api, scraper
from django.http import HttpResponse

# Set up logging config
logging.basicConfig(filename='coaster.log', level=logging.WARNING)

# scraper class object
scrapeObj = scraper.Scraper()


def scrape_all_product(request):
    """Scrape all the product on coaster.
    """
    return_me = ""
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
