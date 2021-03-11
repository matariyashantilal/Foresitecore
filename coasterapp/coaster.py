# Create your views here.
import datetime
import json
import logging
import os
import tempfile
from pathlib import Path
from time import sleep

from django.shortcuts import render

from coasterapp import shopify_helper_new

from . import coaster_api as coaster

from . import coasterscraper as thescraper

# Set up logging config
logging.basicConfig(filename='coaster.log', level=logging.WARNING)

# todo delete this variable
product_file = "supplier_coaster/products.txt"


thedir = os.environ.get("temp_directory_path")
thebasecoastertemppath = os.path.join(thedir, "foresitecore", "coaster")
Path(thebasecoastertemppath).mkdir(parents=True, exist_ok=True)

scrapeObj = thescraper.Scraper()


def scrapeAllProducts():
    return_me = ""
    # get the category json
    jObj = coaster.call("GetCategoryList", {})
    scrapeObj.resetcounts()
    for p in jObj:
        # get all the objects in a category
        #thefilter = saveFilter("getFilter?categoryCode="+p["CategoryCode"])
        # saveCoasterProduct(thefilter,"CompleteCategory-"+p["CategoryName"])
        args = {'CategoryCode': p["CategoryCode"]}
        data = coaster.call("GetFilter", args)
        filter = json.dumps(data).strip('"')
        # Call the coaster API to get all the info for the products into a dictionary of objects
        args = {'filterCode': filter}
        products = coaster.call("GetProductList", args)
        for product in products:
            try:
                pNum = product["ProductNumber"]
                scrapedata = scrapeObj.scrape(pNum)
                #return_me += "Scraped " + pNum + "<br>"
            except Exception as e:
                logging.error(
                    "ERROR: Could not read pNum from product " + product)
                return_me += "ERROR: Could not read pNum from product " + product + "<br>"
        return_me = "Scraped " + str(scrapeObj.count_scraped) + " Skipped " + str(scrapeObj.count_skipped) + \
            " Used cache:" + str(scrapeObj.count_used_cache) + \
            " Total processed:" + str(scrapeObj.count_total)
    return return_me

# Identify discontinued items


def processJSONByCategory():
    return_me = ""
    # get the category json
    jObj = coaster.call("GetCategoryList", {})
    for p in jObj:
        # get all the objects in a category
        #thefilter = saveFilter("getFilter?categoryCode="+p["CategoryCode"])
        # saveCoasterProduct(thefilter,"CompleteCategory-"+p["CategoryName"])
        args = {'CategoryCode': p["CategoryCode"]}
        data = coaster.call("GetFilter", args)
        filter = json.dumps(data).strip('"')
        # Call the coaster API to get all the info for the products into a dictionary of objects
        args = {'filterCode': filter}
        products = coaster.call("GetProductList", args)
        return_me += processProducts(products)
    return return_me


def add(sku):
    if sku[0] == "update-all":
        return processJSONByCategory()
    else:
        return addList(sku)

# Calls the Coaster api to get all the relevant data for the given SKU and adds it to Shopify.
# If successful, it gets added to the local products.txt list for price/inventory/meta updates and duplicate prevention


def processProducts(products):
    return_text = ""
    stats_totalprods = len(products)
    stats_noupdates = 0
    stats_skips = 0
    stats_adds = 0
    inventoryCount = InventoryCount()

    # track how many updates, adds, noupdates, skips there are
    try:
        #inventoryCount = coasterInventory.InventoryCount()
        # Call the coaster API to get price/MAP info for the products
        args = {'customerNumber': "105853"}
        prices = coaster.call("GetPriceList", args)
        # Convert the price dictionary into one where the key is the ProductNumber/SKU
        price_data = {}
        for entry in prices[0]["PriceList"]:
            price_data[entry["ProductNumber"]] = {
                "MAP": entry["MAP"], "Price": entry["Price"]}

        # 5. Add new unique SKUs to Shopify and products.txt
        # Go through the products and update the Shopify store front with any new items, removing discontinued items along the way
        discontinuedcount = 0
        for product in products:
            # if product["IsDiscontinued"]:
            #    logging.warning(product["ProductNumber"] + " has been discontinued.")
            # Handle discontinued + 0 quantity items here (remove from Shopify, maybe remove from products.txt)
            # else:
            pNum = product["ProductNumber"]
            logging.info(
                "supplier_coaster->main.py->processProducts() Acting on product: "+pNum)
            # this check is useful for debugging and setting a breakpoint when pNum equals a certain value
            if pNum == "900803":
                logging.info(
                    "supplier_coaster->main.py->processProducts() Acting on product: "+pNum)

            inventorycount = inventoryCount.getInventoryCount(pNum)
            product["RRFO_Supplier_Inventory_Count"] = inventorycount
            product["Vendor"] = "Coaster"
            product["MAP"] = str(price_data[pNum]["MAP"])
            product["RRFO_PRICE"] = str(getPrice(pNum))
            product["Images"] = []
            #inventorycount = inventoryCount.getInventoryCount(product["ProductNumber"])
            if inventorycount == 0 and product["IsDiscontinued"]:
                # discontinued.updateDiscontinuedMap(product["ProductNumber"])
                #logging.info("productNumber is discontinued: "+product["ProductNumber"])
                discontinuedcount = discontinuedcount + 1
                logging.info(
                    "It's discontinued and inventory is zero. Don't add to shopify." + pNum)
                return_text += "Skiped discontinued and zero inventory Coaster product " + \
                    str(pNum) + "  <br>"
            elif pNum.endswith('B1') or pNum.endswith('B2') or pNum.endswith('B3'):
                logging.info("It's a box. Don't add to shopify." + pNum)
                return_text += "Skiped box Coaster product " + \
                    str(pNum) + "  <br>"
            else:
                # Dimensions - This should be switched to use the public dimension data instead of the API info
                #product["Description"] += "<br><br>Dimensions (Length x Width x Height):"
                # for option in product["MeasurementList"]:
                #    product["Description"] += "<br>" + option["PieceName"] + ": " + str(option["Length"]) + "\" x " + str(option["Width"]) + "\" x " + str(option["Height"]) + "\""
                #product["Tags"] = "2000"

                scrapedata = scrapeObj.scrape(product['ProductNumber'])
                if len(scrapedata) != 0:

                    # If there are public images available for the product, grab their URLs
                    product["Images"] = scrapedata["Images"]
                    product["Tags"] = ','.join(scrapedata["Breadcrumb"])
                    product["product_type"] = scrapedata["Breadcrumb"][-1]

                    # If there weren't any public images, grab the nextgen image URLs
                    if not product["Images"]:
                        logging.warn(
                            "Product " + product["ProductNumber"] + " has no images, so it won't be added to Shopify")
                        # TODO figure out the nextGen images
                        #images = data[0]["ListNextGenImages"]
                        #product["Images"] = images.nextGen(product)
                    # And if there still aren't any images, log an error and go to the next product
                    if not product["Images"]:
                        logging.warn(
                            "Product " + product["ProductNumber"] + " has no images, so it won't be added to Shopify")
                        continue

                    product["Description"] = "<p>" + \
                        scrapedata["Description"] + "</p><b>Features:</b><ul>"
                    for line in scrapedata["Features"]:
                        product["Description"] += "<li>" + line + "</li>"
                    product["Description"] += "</ul>"
                    product["Description"] += "<b>Dimensions:</b><ul>"
                    for line in scrapedata["Dimensions_Weight"]:
                        product["Description"] += "<li>" + line + "</li>"
                    product["Description"] += "</ul>"

                    product["Name"] = scrapedata["Title"]

                    # Add the product to Shopify
                    returnme = shopify_helper_new.upsertShopifyProduct(product)

                # Add the Coaster SKU and Shopify product id to products.txt
                # with open(product_file, 'a') as file:
                #    file.write(str(pNum) + "\t" + str(shopify_id) + "\n")
                    return_text += "Processed Coaster product " + \
                        str(pNum) + " " + returnme + "<br>"
                else:
                    return_text += "Skipped Coaster product. Found no scrape data " + \
                        str(pNum) + " " + returnme + "<br>"

        #stats_totalprods = products.len
        #stats_noupdates = 0
        #stats_skips = 0
        #stats_adds = 0
        return return_text
    except Exception as e:
        return "Failed to add Coaster products: " + str(e)
# Calls the Coaster api to get all the relevant data for the given SKU and adds it to Shopify.
# If successful, it gets added to the local products.txt list for price/inventory/meta updates and duplicate prevention


def addList(sku):
    return_text = ""
    try:
        # if no sku is specified, then load in all products
        # "GetCategoryList"

        # 1. Eliminate duplicates from the SKU list submitted

        new_sku = set(sku)

        # 2. Read products.txt into a set (SKU's only)
        #existing_sku = set(line.split()[0] for line in open(product_file))

        # 3. Remove SKUs already present in products.txt
        # 3.1 wee need the ability to perform updates and adds
        #new_sku -= existing_sku

        # 3.5: If new_sku is empty, the coaster API is going to give back its entire catalog (10k+ products)
        #      So just throw an error and exit early
        #if len(new_sku) == 0: raise Exception("No products given")

        # 4. Use the coaster API to get info for all remaining SKUs
        # - Convert new_sku set into a comma-delimited string
        sku_list = ','.join(str(sku) for sku in new_sku)
        # Call coaster API to get a filter for these products
        args = {'ProductNumber': sku_list}
        data = coaster.call("GetFilter", args)
        filter = json.dumps(data).strip('"')
        # Call the coaster API to get all the info for the products into a dictionary of objects
        args = {'filterCode': filter}
        products = coaster.call("GetProductList", args)
        return_text = processProducts(products)
        return return_text
    except Exception as e:
        return "Failed to add Coaster products: " + str(e)

# Remove any number of SKUs from products.txt, then use the corresponding Shopify product id to remove it from Shopify


def remove(sku_list):
    return_text = ""
    for sku in sku_list:
        try:
            success = False
            with open(product_file, "r") as file:
                lines = file.readlines()
            with open(product_file, "w") as file:
                for line in lines:
                    if line[0:len(sku)+1] != sku + "\t":
                        file.write(line)
                    else:
                        # If this is the correct line, grab the product id and use it to remove the product from Shopify
                        shopify_id = line.strip("\n").split("\t")
                        shopify_id = shopify_id[1]
                        success = True
            if not success:
                raise Exception("SKU not found in products.txt")

            # Delete the product from Shopify
            shopify_helper_new.deleteProduct(shopify_id)
            return_text += "Removed Coaster product " + sku + "<br>"
        except Exception as e:
            return_text += "Failed to remove Coaster product " + \
                sku + ": " + str(e) + "<br>"
    return return_text


############################################################
##
# Prices
##
############################################################
# zzz

def updatePrices():
    try:
        sps = shopify_helper_new.ShopifyProducts()
        for p in sps.dProducts.values():
            if p.attributes["vendor"] == "Coaster":
                # get the suppliers inventory count for this product
                pNum = p.attributes["variants"][0].sku
                price = getPrice(pNum)
                shopify_id = p.attributes["id"]
                shopify_helper_new.updatePrice(shopify_id, price)

        # TODO return reporting metrics. how many were updated. how many were skipped, etc
        return "Updated RRFO prices for Coaster on the Shopify site"

    except Exception as e:
        logging.info("Cannot update price for "+sSupplierSKU +
                     ". Problem with product id find. Did the id change, or was the product on the website removed?")
        logging.info(e)
        return


priceData = "empty"
#
# TODO This should go in a class init


def getCoasterPriceList(refreshcache=False):
    # if priceData == "empty":
    if True:
        thefullpath = os.path.join(thebasecoastertemppath, "theprices.json")
        if os.path.exists(thefullpath) and not refreshcache:
            with open(thefullpath) as outfile2:
                priceData = json.load(outfile2)
            returnme = "Using Coaster prices cache"
        else:
            args = {'customerNumber': "105853"}
            priceData = coaster.call("GetPriceList", args)
            with open(thefullpath, 'w') as outfile:
                json.dump(priceData, outfile)
        return priceData
    else:
        return priceData


def getPrice(productnumber):
    data = getCoasterPriceList()
    # open the price file
    newprice = 100000
    for i in data[0]["PriceList"]:
        if i['ProductNumber'] == productnumber:
            theprice = i['Price']
            shipping = theprice * .17
            markupspread = theprice * .90
            newprice = theprice + shipping + markupspread
            break

    # Use floor int division to return an integer
    return int(newprice)


def updateAllPrices():
    # default location id:36481335376
    #API_VERSION = "2020-04"
    #shop_url = "https://%s:%s@red-rock-luxury-furniture-2.myshopify.com/admin/api/%s" % (config.data["API_KEY"], config.data["PASSWORD"], API_VERSION)
    # shopify.ShopifyResource.set_site(shop_url)
    #shop = shopify.Shop.current()

    # open each json file in the directory
    os.chdir("C:/Projects/CoasterAPI/coasterapi/cached_json")
    logging.info("Updating prices")
    for file in glob.glob("*.json"):
        # logging.info(file)
        with open('C:/Projects/CoasterAPI/coasterapi/cached_json/'+file) as json_file:
            coasterobj = json.load(json_file)
            updatePrice(coasterobj)
        #images = data[0]["ListNextGenImages"]


def updatePrice(coasterJSONObj):
    if(type(coasterJSONObj) != list):
        logging.info("This is an invalid produt JSON object")
        return
    # Get a specific product
    shopifyproductid = ""
    sSupplierSKU = coasterJSONObj[0]["ProductNumber"]
    if sSupplierSKU in cm.dTheMap:
        shopifyproductid = cm.dTheMap[sSupplierSKU]
        try:
            price = getPrice(sSupplierSKU)
            oProduct = shopify.Product.find(shopifyproductid)
            logging.info("12sleep")
            time.sleep(1)

            if oProduct.variants[0].price != price:
                logging.info("Updated price for:"+sSupplierSKU)
                oProduct.variants[0].price = price
                oProduct.variants[0].save()
                logging.info("13sleep")
                time.sleep(1)
        except Exception as e:
            logging.info("Cannot update price for "+sSupplierSKU +
                         ". Problem with product id find. Did the id change, or was the product on the website removed?")
            logging.info(e)
            return
    else:
        logging.info("Cannot update price for "+sSupplierSKU +
                     ". Problem with product id find. Did the id change, or was the product on the website removed?")
        return


# Updates the price for everything in products.txt
# delete this method
def updatePricesold():
    try:
        sku_list = ""
        shopify_ids = []
        # 1. Go through products.txt and put together a Python list of everything that needs a price update (SKU and shopify_id)
        with open(product_file, "r") as file:
            for line in file:
                pair = line.strip("\n").split("\t")
                sku_list += pair[0] + ","
                shopify_ids.append(pair[1])
        # Remove trailing comma
        sku_list = sku_list.rstrip(',')

        # 2. Call the Coaster API to get prices for those products
        # Call coaster API to get a filter for the products
        args = {'ProductNumber': sku_list}
        data = coaster.call("GetFilter", args)
        args['filterCode'] = json.dumps(data).strip('"')
        args['customerNumber'] = "105853"
        # Call the coaster API to get price/MAP info for the products
        prices = coaster.call("GetPriceList", args)
        # Convert the price dictionary into one where the key is the ProductNumber/SKU
        #price_data = { }
        # for entry in prices[0]["PriceList"]:
        #    price_data[entry["ProductNumber"]] = { "MAP": entry["MAP"], "Price": entry["Price"]}
        # ^ I think this is unnecessary for price updates, since they should be in the same order as the shopify_ids? TBD

        # 3. Update prices for those products on Shopify
        for index, shopify_id in enumerate(shopify_ids):
            shopify_helper_new.updatePrice(
                shopify_id, prices[0]["PriceList"][index]["Price"])
        return "Updated Coaster prices (" + str(len(shopify_ids)) + " products)"
    except Exception as e:
        return "Failed to update Coaster prices: " + str(e)

# Create a function to get the inventory count for a specific SKU
# create a function to update all inventory counts for this supplier in shopify

# TODO fix to accept a list of part numbers


def scrape(pNum):
    if pNum == "update-all":
        return scrapeAllProducts()
    else:
        scrapedata = scrapeObj.scrape(pNum)
    return "Scraped:"+pNum


def getProductInventoryCount(pNum):
    inventoryCount = InventoryCount()
    inventorycount = inventoryCount.getInventoryCount(pNum)

    return inventorycount


class InventoryCount:
    dInventoryCount = {}
    dTheMap = {}
    # thedir = tempfile.gettempdir()
    thefilename = "inventory_coaster.json"

    def getInventoryCount(self, productnumber):
        try:
            # TODO loop through each warehouse and add the counts together
            return self.dTheMap[productnumber]
        except:
            return 0

    def __init__(self):
        inventory_coaster_json_path = os.path.join(thedir, self.thefilename)
        print(inventory_coaster_json_path)
        if not os.path.exists(inventory_coaster_json_path):
            os.mknod(inventory_coaster_json_path)
        with open(inventory_coaster_json_path) as file_handle:
            jInventory = json.load(file_handle)

        # TODO create the map for each warehouse location
        # TODO read the inventory count from shopify for the Hurricane warehouse
        # The current code combines the inventory count from both warehouses
        for i in jInventory[0]["InventoryList"]:
            self.dTheMap[i['ProductNumber']] = int(i['QtyAvail'])
        # TODO fix this to handle a dynamic number of locations
        for i in jInventory[1]["InventoryList"]:
            self.dTheMap[i['ProductNumber']] += int(i['QtyAvail'])

# iterate through every item in the live shopify products list
# grab the coaster sku
# get the supplier's inventory count
# update the shopify inventory count


def updateInventory():
    inventoryCount = InventoryCount()
    sps = shopify_helper_new.ShopifyProducts()
    for p in sps.dProducts.values():
        if p.attributes["vendor"] == "Coaster":
            # get the suppliers inventory count for this product
            sSupplierSKU = p.attributes["variants"][0].sku
            inventorycount = inventoryCount.getInventoryCount(sSupplierSKU)
            inventory_item_id = p.attributes["variants"][0].attributes["inventory_item_id"]
            shopify_id = p.attributes["id"]
            shopify_helper_new.updateInventoryNew(
                shopify_id, inventory_item_id, inventorycount)

    # TODO return reporting metrics. how many were updated. how many were skipped, etc
    return "Updated Coaster inventory counts on the Shopify site"

# TODO - add a flag to read from disk or refresh the cache, and use the flag
# TODO check the timestamp on the file. if it is older than x then refresh the file.


def getSupplierInventoryCounts(refreshcache=False):

    # const url1 = "http://api.coasteramer.com/api/product/GetInventoryList?warehouseCode=SF";
    # const url2 = "http://api.coasteramer.com/api/product/GetInventoryList?warehouseCode=LD";

    returnme = ""
    try:
        # thedir = tempfile.gettempdir()
        thefilename = "inventory_coaster.json"
        thefullpath = os.path.join(thebasecoastertemppath, thefilename)
        returnme = ""
        # if os.path.exists(thefullpath) and not refreshcache:
        #     returnme = "Using Coaster inventory count cache"
        # else:
        args = {'warehouse': "LD"}
        data = coaster.call("GetInventoryList", args)
        with open(os.path.join(thedir, thefilename), 'w') as outfile:
            json.dump(data, outfile)
        for warehouse in data:
            #    thefilename = "inventory_coaster_"+warehouse["WarehouseCode"]+".json"
            returnme += "Saved Coaster inventory counts for warehouse:" + \
                warehouse["WarehouseCode"] + "<p>"
        #    #productnum = data[0]["InventoryList"][0]["ProductNumber"]
        #    with open(os.path.join(thedir, thefilename), 'w') as outfile:
        #        json.dump(data, outfile)
        return returnme
    except Exception as e:
        print("Exception Inventory failed to save")
        print(e)
        return "Exception Inventory failed to save"
