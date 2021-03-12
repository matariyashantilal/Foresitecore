import json
import logging
import os

from coaster import api, inventory_count, scraper
from django.conf import settings
from django.http import HttpResponse

from shopify_module import views as shopify

scrapeObj = scraper.Scraper()


class products:

    def processProducts(self, products):
        return_text = ""
        stats_totalprods = len(products)
        stats_noupdates = 0
        stats_skips = 0
        stats_adds = 0
        inventoryCount = inventory_count.InventoryCount()

        # track how many updates, adds, noupdates, skips there are
        # try:
        #inventoryCount = coasterInventory.InventoryCount()
        # Call the coaster API to get price/MAP info for the products
        args = {'customerNumber': "105853"}
        prices = api.call("GetPriceList", args)
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
            product["RRFO_PRICE"] = str(self.getPrice(pNum))
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
                        scrapedata["Description"] + \
                        "</p><b>Features:</b><ul>"
                    for line in scrapedata["Features"]:
                        product["Description"] += "<li>" + line + "</li>"
                    product["Description"] += "</ul>"
                    product["Description"] += "<b>Dimensions:</b><ul>"
                    for line in scrapedata["Dimensions_Weight"]:
                        product["Description"] += "<li>" + line + "</li>"
                    product["Description"] += "</ul>"

                    product["Name"] = scrapedata["Title"]

                    # Add the product to Shopify

                    returnme = shopify.upsertShopifyProduct(product)

                # Add the Coaster SKU and Shopify product id to products.txt
                # with open(product_file, 'a') as file:
                #    file.write(str(pNum) + "\t" + str(shopify_id) + "\n")
                    return_text += "Processed Coaster product " + \
                        str(pNum) + " " + returnme + "<br>"
                else:
                    returnme = ""
                    return_text += "Skipped Coaster product. Found no scrape data " + \
                        str(pNum) + " " + returnme + "<br>"

        #stats_totalprods = products.len
        #stats_noupdates = 0
        #stats_skips = 0
        #stats_adds = 0
        return return_text
        # except Exception as e:
        #     return "Failed to add Coaster products: " + str(e)
    # Calls the Coaster api to get all the relevant data for the given SKU and adds it to Shopify.
    # If successful, it gets added to the local products.txt list for price/inventory/meta updates and duplicate prevention

    def addList(self, sku):
        return_text = ""
        # try:
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
        data = api.call("GetFilter", args)
        filter = json.dumps(data).strip('"')
        # Call the api API to get all the info for the products into a dictionary of objects
        args = {'filterCode': filter}
        products = api.call("GetProductList", args)
        return_text = self.processProducts(products)
        return return_text
        # except Exception as e:
        #     return "Failed to add api products: " + str(e)

    def getCoasterPriceList(self, refreshcache=False):
        if True:
            thefullpath = os.path.join(
                settings.COASTER_DIRECTORY_PATH, "theprices.json")
            if os.path.exists(thefullpath) and not refreshcache:
                with open(thefullpath) as outfile2:
                    priceData = json.load(outfile2)
                returnme = "Using Coaster prices cache"
            else:
                args = {'customerNumber': "105853"}
                priceData = api.call("GetPriceList", args)
                with open(thefullpath, 'w') as outfile:
                    json.dump(priceData, outfile)
            return priceData
        else:
            return priceData

    def getPrice(self, productnumber):
        data = self.getCoasterPriceList()
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
