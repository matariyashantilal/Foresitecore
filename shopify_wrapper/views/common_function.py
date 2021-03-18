import glob
import json
import logging
import os
import shutil
import time
from pathlib import Path

import jsonpickle
import requests
import shopify
from coaster.views import api
from django.http import HttpResponse

from . import product, shopify_products

productObj = product.products()
locationid = os.environ.get("SHOPIFY_LOCATION")
thebaseshopifylogpath = os.environ.get("SHOPIFY_DIRECTORY_PATH")
thejsonfilename = "allshopifyproducts." + \
    str(os.environ.get("SHOPIFY_SHOP")) + ".json"
Path(str(thebaseshopifylogpath)).mkdir(parents=True, exist_ok=True)
currentDir = os.getcwd()
shopify.ShopifyResource.set_site(os.environ.get("SHOPIFY_SECUREURL"))

# flag to toggle Shopify persist to live system
bPersistToShopify = True


# get all inventory counts for the location
# https://shopify.dev/docs/admin-api/rest/reference/inventory/location
def loadShopifyInventoryLevels(locationid):
    inv_levels = []
    oLocation = shopify.Location({'id': locationid})
    inventorycounts = recursive_get_inventory_levels(
        oLocation, inv_levels, limit=250)
    return inventorycounts


def recursive_get_inventory_levels(oLocation, inv_levels, page_info='', chunk=1, limit=''):
    """Fetch location inventory counts recursively."""
    cache = page_info
    # inv_levels.extend(shopify.Product.find(limit=limit, page_info=page_info))
    inv_levels.extend(oLocation.inventory_levels(
        limit=limit, page_info=page_info))
    cursor = shopify.ShopifyResource.connection.response.headers.get('Link')
    if cursor != None:
        for _ in cursor.split(','):
            if _.find('next') > 0:
                page_info = _.split(';')[0].strip('<>').split('page_info=')[1]
    # logging.info('chunk fetched: %s' % chunk)
    if cache != page_info:
        time.sleep(1)
        return recursive_get_inventory_levels(oLocation, inv_levels, page_info, chunk+1, limit)
    return inv_levels


inventorycounts = loadShopifyInventoryLevels(locationid)


def getInventoryCountFromShopifyLocation(inventory_item_id):
    available = 0
    for item in inventorycounts:
        if item.attributes["inventory_item_id"] == int(inventory_item_id):
            available = item.attributes["available"]
            break
    return available


def updateAllInventoryCounts():
    sps = shopify_products.ShopifyProducts()
    totalUpdateCount = 0
    totalNotUpdatedCount = 0
    for p in sps.dProducts.values():
        if updateInventoryCount(p):
            totalUpdateCount = totalUpdateCount + 1
        else:
            totalNotUpdatedCount = totalNotUpdatedCount + 1
    logging.info(
        f"Total inventory updates:{totalUpdateCount} Total no changes:{totalNotUpdatedCount}")


def updateInventoryProperties(shopify_variant):
    bSave = False
    if shopify_variant.inventory_management != "shopify":
        shopify_variant.inventory_management = "shopify"
        bSave = True
        # shopify_variant.save()
        # time.sleep(1)
        # logging.info("7sleep")
    if shopify_variant.fulfillment_service != "manual":
        bSave = True
        shopify_variant.fulfillment_service = "manual"

    if shopify_variant.inventory_policy != "deny":
        bSave = True
        shopify_variant.inventory_policy = "deny"

    if bSave:
        time.sleep(.6)
        shopify_variant.save()
        logging.info("10 sleep .6")


def updateInventoryNew(shopify_id, inventory_item_id, supplierInvCount):
    returnme = False
    sps = shopify_products.ShopifyProducts()
    prods = sps.dProducts
    oProduct = shopify.Product.find(shopify_id)
    for p in prods.values():
        if p.attributes["id"] == shopify_id:
            oProduct = p
            break

    pNum = oProduct.variants[0].sku
    bSave = False
    shopify_variant = oProduct.variants[0]
    if shopify_variant.inventory_management != "shopify":
        shopify_variant.inventory_management = "shopify"
        bSave = True
    if shopify_variant.fulfillment_service != "manual":
        bSave = True
        shopify_variant.fulfillment_service = "manual"

    if shopify_variant.inventory_policy != "deny":
        bSave = True
        shopify_variant.inventory_policy = "deny"

    if bSave:
        returnme = True
        time.sleep(.6)
        shopify_variant.save()

    bSave = True
    websitecount = getInventoryCountFromShopifyLocation(inventory_item_id)
    # websitecount = oProduct.variants[0].inventory_quantity
    supplierInvCount = int(supplierInvCount)
    if websitecount == None:
        websitecount = 0
    websitecount = int(websitecount)

    if websitecount > 5 and supplierInvCount > 5:
        # we don't care about inventory changes when the inventory is sufficient
        logging.info("    Inventory is above 5 for:"+pNum)
        pass

    else:

        supplierInvCount = int(supplierInvCount)
        if supplierInvCount <= 2 and websitecount == 0:
            pass
        if supplierInvCount <= 2:
            supplierInvCount = 0
        time.sleep(.6)
        if websitecount != supplierInvCount:
            # TODO wrap in try/catch
            inventory_level = shopify.InventoryLevel.set(
                int(locationid), inventory_item_id, supplierInvCount)
            logging.info("   Updated inventory from "+str(websitecount) +
                         " to " + str(supplierInvCount) + " for:"+pNum)
            bSave = True

    if bSave:
        returnme = True
        time.sleep(.6)
        shopify_variant.save()

    return returnme


def updateInventoryCount(shopifyProduct, suppliercount):

    shopifyproductid = ""
    pNum = ""

    pNum = shopifyProduct.variants[0].sku
    shopify_variant = shopifyProduct.variants[0]
    updateInventoryProperties(shopify_variant)

    updated = False
    if pNum != None:
        shopifyproductid = shopifyProduct.id
        try:
            iInventoryItemId = shopifyProduct.variants[0].inventory_item_id

            websitecount = shopifyProduct.variants[0].inventory_quantity

            if websitecount == None:
                websitecount = 0

            if websitecount > 5 and suppliercount > 5:
                # we don't care about inventory changes when the inventory is sufficient
                logging.info("Inventory is above 5 for:"+pNum)
                pass
            elif websitecount != suppliercount:
                suppliercount = int(suppliercount)
                inventory_level = shopify.InventoryLevel.set(
                    locationid, iInventoryItemId, suppliercount)
                time.sleep(1.5)
                logging.info("Updated inventory from "+str(websitecount) +
                             " to " + str(suppliercount) + " for:"+pNum)
                updated = True
            elif websitecount == suppliercount:
                logging.info("No inventory change for:"+pNum)
                pass
            else:
                logging.info("No change to inventory for:"+pNum)

        except Exception as e:
            logging.info("Exception: Cannot update Inventory Count for SKU:"+pNum +
                         " Problem with product id find. Did the id change, or was the product on the website removed?")
            logging.info(e)
    else:
        logging.info("Cannot update Inventory Count for SKU:"+pNum +
                     " Problem with product sku. there is no Sku for this product ")
    return updated


def getPrice(productnumber):
    # open the price file
    newprice = 100000
    with open('C:/Projects/CoasterAPI/coasterapi/prices/all_coaster_prices.json') as file_handle:
        jPrices = json.load(file_handle)
    for i in jPrices[0]["PriceList"]:
        if i['ProductNumber'] == productnumber:
            # logging.info(i['MAP'])
            # logging.info(i['Price'])
            theprice = i['Price']
            shipping = theprice * .17
            markupspread = theprice * .90
            newprice = theprice + shipping + markupspread

            break

    return newprice


def updateAllPrices():
    os.chdir("C:/Projects/CoasterAPI/coasterapi/cached_json")
    logging.info("Updating prices")
    for file in glob.glob("*.json"):
        # logging.info(file)
        with open('C:/Projects/CoasterAPI/coasterapi/cached_json/'+file) as json_file:
            coasterobj = json.load(json_file)
            updatePrice(coasterobj)


def resetShopifyCache():
    try:
        thefulljsonpath = os.path.join(thebaseshopifylogpath, thejsonfilename)
        if os.path.exists(thefulljsonpath):
            os.remove(thefulljsonpath)
        sps = shopify_products.ShopifyProducts()
        sps.reloadProducts()
    except Exception as e:
        print(e)


def cursor_based_bulk_fetch_products(limit=250):
    products = []

    # zzz
    usecache = False
    thefulljsonpath = os.path.join(thebaseshopifylogpath, thejsonfilename)

    # if the cache exists, use it. Otherwise, create the cache
    if os.path.exists(thefulljsonpath) and usecache:
        logging.debug("Loading Shopify products from cache")
        f = open(thefulljsonpath)

        json_str = f.read()
        allShopifyProducts = jsonpickle.decode(json_str)
    else:
        logging.debug("Loading Shopify products from Shopify")
        allShopifyProducts = get_products(products, limit=limit)
        f = open(thefulljsonpath, 'w')
        json_obj = jsonpickle.encode(allShopifyProducts)
        f.write(json_obj)
        f.close()
    return allShopifyProducts


def get_products(products, page_info='', chunk=1, limit=''):
    """Fetch products recursively."""
    cache = page_info
    products.extend(shopify.Product.find(limit=limit, page_info=page_info))
    cursor = shopify.ShopifyResource.connection.response.headers.get('Link')
    if cursor != None:
        for _ in cursor.split(','):
            if _.find('next') > 0:
                page_info = _.split(';')[0].strip('<>').split('page_info=')[1]
    # logging.info('chunk fetched: %s' % chunk)
    if cache != page_info:
        time.sleep(1)
        return get_products(products, page_info, chunk+1, limit)
    return products


def upsertShopifyProduct(productJSON, bUpdateImages=False):
    logging.info("shopify_helper_new->upsertSupifyProduct()")

    # return new, updated, nochange
    returnmenew = False
    returnmeupdated = False
    returnmeimages = False
    is_new_product = False
    # We don't want to create duplicates in the catalog
    # See if the product is already in the online catalog
    pNum = productJSON["ProductNumber"]
    vendor = productJSON["Vendor"]
    logging.info("    Acting on vendor:"+vendor+" product:"+pNum)
    sps = shopify_products.ShopifyProducts()
    oProduct = None
    try:
        oProduct = sps.dProductMapBySupplierSKU[pNum]
    except:
        oProduct = None

    if oProduct == None:
        oProduct = shopify.Product()
        is_new_product = True
        logging.info("    Product does not exist in Shopify: " + str(pNum))

    if is_new_product:
        bUpdateImages = True
        oProduct.title = productJSON["Name"]
        oProduct.vendor = productJSON["Vendor"]
        oProduct.body_html = productJSON["Description"]
        oProduct.product_type = productJSON["product_type"]
        oProduct.SKU = pNum

        variant = shopify.Variant(dict(price=productJSON["RRFO_PRICE"]))
        oProduct.variants = [variant]
        oProduct.variants[0].sku = pNum
        success = oProduct.save()  # returns false if the record is invalid
        returnmenew = True
        time.sleep(3)

    saveChanges = False
    # check for differences
    # Check for price change
    # zzz
    if "RRFO_Supplier_Inventory_Count" in productJSON:
        inventorycount = productJSON["RRFO_Supplier_Inventory_Count"]
        inventory_item_id = oProduct.attributes["variants"][0].attributes["inventory_item_id"]
        shopify_id = oProduct.attributes["id"]
        if updateInventoryNew(shopify_id, inventory_item_id, inventorycount):
            logging.info("    Inventory count updated")
            returnmeupdated = True
            # Don't set saveChanges because the updateInventory method handled the save
            # the save happens on the variant
            # saveChanges = True

    if ("%.2f" % float(oProduct.variants[0].price)) != ("%.2f" % float(productJSON["RRFO_PRICE"])):
        logging.info("    Price changed from:" +
                     oProduct.variants[0].price + " to:" + productJSON["RRFO_PRICE"])
        oProduct.variants[0].price = productJSON["RRFO_PRICE"]
        saveChanges = True

    # Check for tag changes

    if not myArrayCompare(oProduct.tags, productJSON["Tags"]):
        oProduct.tags = productJSON["Tags"]
        saveChanges = True
        logging.info("    Tags changed from:" +
                     oProduct.tags + "to:"+productJSON["Tags"])

    # check for change in description
    text = oProduct.body_html.replace('\n', '')
    if text != productJSON["Description"]:
        oProduct.body_html = productJSON["Description"]
        saveChanges = True
        logging.info("    Description changed")

    saveEnabled = True
    if saveChanges:
        logging.info("    Saving updates: "+pNum)
        returnmeupdated = True
        if saveEnabled:
            oProduct.save()
            time.sleep(1.5)

    # Create a new product
    try:
        if bUpdateImages:
            logging.info("    Updating images: "+pNum)
            time.sleep(.5)
            liveImages = shopify.Image.find(product_id=oProduct.id)
            for img_url in productJSON["Images"]:
                b_image_already_live = False
                # print(img_url)
                imgfilename = img_url.split('/')[-1].replace(" ", "_")
                for liveimage in liveImages:
                    if "products/" + imgfilename in liveimage.src:
                        b_image_already_live = True
                        break
                if not b_image_already_live:
                    image = shopify.Image({"product_id": oProduct.id})
                    image.src = img_url
                    time.sleep(.5)
                    image.save()
        return "New obj:"+str(returnmenew) + " Udated:"+str(returnmeupdated) + " Updated images:"+str(returnmeimages)
    except Exception as e:
        logging.error("    error loading product")
        logging.error(e)
        return "New obj:"+str(returnmenew) + " Udated:"+str(returnmeupdated) + " Updated images:"+str(returnmeimages)


headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'}


def ImageDl(url, filepath):
    attempts = 0
    while attempts < 5:
        try:
            r = requests.get(url, headers=headers, stream=True, timeout=30)
            if r.status_code == 200:
                # with open(os.path.join(path,filename),'wb') as f:
                with open(filepath, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)
                # print('Downloading image: {}'.format(filename))
            break
        except Exception as e:
            attempts += 1
            print(e)


def addProduct(productJSON):
    try:
        # Base attributes
        oProduct = shopify.Product()
        oProduct.title = productJSON["Name"]
        oProduct.vendor = productJSON["Vendor"]
        oProduct.body_html = productJSON["Description"]
        oProduct.SKU = productJSON["ProductNumber"]

        # Set the Price
        variant = shopify.Variant(dict(price=productJSON["MAP"]))
        variant.sku = productJSON["ProductNumber"]
        oProduct.variants = [variant]
        oProduct.save()

        # Add images by URL
        for url in productJSON["Images"]:
            # print("Adding image to Shopify: "+url)
            image = shopify.Image({"product_id": oProduct.id})
            image.src = url
            image.save()

        # Returns the shopify product ID so it can be stored with its corresponding SKU
        return oProduct.id
    except Exception as e:
        logging.info("Error adding SKU " +
                     productJSON["ProductNumber"] + " to Shopify: " + str(e))
        return -1

# Removes a product from Shopify


def deleteProduct(shopify_id):
    try:
        shopify.Product.delete(shopify_id)
        logging.info("Deleted product: " + str(shopify_id))
    except Exception as e:
        logging.info("Failed to delete product: " + str(shopify_id))
        logging.info(e)

# Updates the price on a Shopify product


def updatePrice(shopify_id, price):
    try:
        # zzz TODO replace this find method - only call save if the price has changed
        # TODO Only update price if there was a change
        oProduct = shopify.Product.find(shopify_id)
        oProduct.variants[0].price = price  # price
        oProduct.save()
    except Exception as e:
        logging.info("Failed to update price: " + str(shopify_id))
        logging.info(e)

# Updates the inventory on a Shopify product
# Delete this method


def updateInventory(shopify_id, quantity):
    try:
        # zzz
        sps = shopify_products.ShopifyProducts()
        prods = sps.dProducts
        # oProduct = shopify.Product.find(shopify_id)
        for p in prods.values():
            if p.attributes["id"] == shopify_id:
                oProduct = p
                break

        bSave = False
        shopify_variant = oProduct.variants[0]
        if shopify_variant.inventory_management != "shopify":
            shopify_variant.inventory_management = "shopify"
            bSave = True
        if shopify_variant.fulfillment_service != "manual":
            bSave = True
            shopify_variant.fulfillment_service = "manual"

        if shopify_variant.inventory_policy != "deny":
            bSave = True
            shopify_variant.inventory_policy = "deny"
        if oProduct.variants[0].inventory_available != quantity:
            oProduct.variants[0].inventory_available = quantity
            bSave = True
            # oProduct.save()
        if bSave:
            time.sleep(.6)
            shopify_variant.save()

    except Exception as e:
        logging.info("Failed to update inventory: " + str(shopify_id))
        logging.info(e)


def myArrayCompare(s1, s2):
    # convert the string to an array
    # remove all spaces from the string
    # sort the array
    if s1 == None:
        s1 = ""
    if s2 == None:
        s2 = ""
    s1 = s1.replace(" ", "")
    s2 = s2.replace(" ", "")
    a1 = s1.split(",")
    a2 = s2.split(",")
    a1 = list(set(a1))
    a2 = list(set(a2))
    a1 = sorted(a1)
    a2 = sorted(a2)
    return a1 == a2
