from coaster import inventory_count
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

from coaster import api, inventory_count, scraper
from shopify_module.views import productObj
from shopify_module import views as shopify

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


def get_product_inventory_count(request, pNum):
    inventoryCount = inventory_count.InventoryCount()
    inventorycount = inventoryCount.getInventoryCount(pNum)

    return HttpResponse(inventorycount)


def update_inventory(request):
    """Updates inventory for everything in the vendor's product list.
    """
    inventoryCount = inventory_count.InventoryCount()
    sps = shopify.ShopifyProducts()
    for p in sps.dProducts.values():
        if p.attributes["vendor"] == "Coaster":
            # get the suppliers inventory count for this product
            sSupplierSKU = p.attributes["variants"][0].sku
            inventorycount = inventoryCount.getInventoryCount(sSupplierSKU)
            inventory_item_id = p.attributes["variants"][0].attributes["inventory_item_id"]
            shopify_id = p.attributes["id"]
            shopify.updateInventoryNew(
                shopify_id, inventory_item_id, inventorycount)

    # TODO return reporting metrics. how many were updated. how many were skipped, etc
    return HttpResponse("Updated Coaster inventory counts on the Shopify site")

    # elif (vendor == "uttermost"):
    #     email_subject = os.environ.get("emailsubject_inventorycountsuttermost")
    #     EmailClass = gmail_lib.Gmail()
    #     thedownloadedfilename = EmailClass.DownloadAttachement(email_subject)
    #     if thedownloadedfilename:
    #         SupplierClass = manage_uttermost_products.ManageUttermostProducts()
    #         SupplierClass.updateInventoryCounts(thedownloadedfilename)
    #         return HttpResponse("Updated inventory for Uttermost")
    #     else:
    #         return HttpResponse("Inventory counts for Uttermost is up to date.")
    # elif (vendor == "foa"):
    #     return HttpResponse(FOA.updateInventory())

# TODO - add a flag to read from disk or refresh the cache, and use the flag
# TODO check the timestamp on the file. if it is older than x then refresh the file.





def update_prices(request):
    """Updates all the prices for a vendor.
    """
    try:
        sps = shopify.ShopifyProducts()
        for p in sps.dProducts.values():
            if p.attributes["vendor"] == "Coaster":
                # get the suppliers inventory count for this product
                pNum = p.attributes["variants"][0].sku
                price = productObj.getPrice(pNum)
                shopify_id = p.attributes["id"]
                shopify.updatePrice(shopify_id, price)

        # TODO return reporting metrics. how many were updated. how many were skipped, etc
        return HttpResponse("Updated RRFO prices for Coaster on the Shopify site")

    except Exception as e:
        logging.info("Cannot update price for "+sSupplierSKU +
                     ". Problem with product id find. Did the id change, or was the product on the website removed?")
        logging.info(e)
        return

    # elif (vendor == "uttermost"):
    #     return HttpResponse("[TODO: Update prices (Uttermost)]")
    # elif (vendor == "foa"):
    #     return HttpResponse("[TODO: Update prices (FOA)]")
    # else:
    #     return HttpResponse(vendor + " not recognized.")


priceData = "empty"
#
# TODO This should go in a class init
