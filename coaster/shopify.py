import shopify
import time
import json
from json.decoder import JSONDecodeError
import shutil
from base64 import b64encode
import glob, os
import logging
import requests

#logging.basicConfig(filename='foresitefurniture.log',level=logging.DEBUG)
#logging.basicConfig(filename='foresitefurniture.log',level=logging.WARNING)
#logging.basicConfig(filename='foresitefurniture.log',level=logging.INFO)

locationid = os.environ.get("SHOPIFY_LOCATION")
thedir = os.environ.get("temp_directory_path")
thebaseshopifylogpath = os.path.join(thedir, 'foresitecore', 'shopify')
thejsonfilename = "allshopifyproducts."+os.environ.get("SHOPIFY_SHOP")+ ".json"
from pathlib import Path
Path(thebaseshopifylogpath).mkdir(parents=True, exist_ok=True)

# TODO introduct the ability to reset a product

currentDir = os.getcwd()

shopify.ShopifyResource.set_site(os.environ.get("SHOPIFY_SECUREURL"))


#shop = shopify.Shop.current()
# get all inventory counts for the location
# https://shopify.dev/docs/admin-api/rest/reference/inventory/location
def loadShopifyInventoryLevels(locationid):
    inv_levels = []
    oLocation = shopify.Location({'id':locationid})
    #allShopifyProducts = get_products(inv_levels,limit=250)
    #inventorycounts = oLocation.inventory_levels()
    inventorycounts = recursive_get_inventory_levels(oLocation, inv_levels,limit=250) 
    return inventorycounts

def recursive_get_inventory_levels(oLocation, inv_levels, page_info='', chunk=1, limit=''):
    """Fetch location inventory counts recursively."""
    cache = page_info
    #inv_levels.extend(shopify.Product.find(limit=limit, page_info=page_info))
    inv_levels.extend(oLocation.inventory_levels(limit=limit, page_info=page_info))
    cursor = shopify.ShopifyResource.connection.response.headers.get('Link')
    if cursor != None:
        for _ in cursor.split(','):
            if _.find('next') > 0:
                page_info = _.split(';')[0].strip('<>').split('page_info=')[1]
    #logging.info('chunk fetched: %s' % chunk)
    if cache != page_info:
        time.sleep(1)
        return recursive_get_inventory_levels(oLocation, inv_levels, page_info, chunk+1, limit)
    return inv_levels

inventorycounts = loadShopifyInventoryLevels(locationid)

# flag to toggle Shopify persist to live system
bPersistToShopify = True

# store the json object of each product. lookup by shopify id
class ShopifyProducts:
    dProducts = {}
    # get shopify product by coaster sku
    dProductMapBySupplierSKU = {}
    def __init__(self):
        if len(self.dProducts) == 0:
            prods = cursor_based_bulk_fetch_products()
            for p in prods:
                self.dProducts[p.id] = p
                self.dProductMapBySupplierSKU[p.variants[0].sku] = p

    def reloadProducts(self):
        self.dProducts = {}
        prods = cursor_based_bulk_fetch_products()
        for p in prods:
            self.dProducts[p.id] = p
 
    def uploadProduct(self,tempAvailabilityProductSKU,tempAvailabilityProductSKUList):
        if int(len(self.dProducts)) > int(0):
            for p in self.dProducts.values():
                if(p.variants[0].sku in tempAvailabilityProductSKU):
                    updateInventoryCount(p,tempAvailabilityProductSKUList[p.variants[0].sku])
		
#########################################
#########################################
#########################################

class InventoryItemIdMap:
    dTheMap = {"000_ProductSKU:product.variant[n].inventory_item_id":1}
    sfileName = "MapInventoryItemId.json"
    def __init__(self):
        if os.path.exists(self.sfileName):
            with open(self.sfileName) as json_file: 
                try:
                    self.dTheMap = json.load(json_file) 
                except:
                    logging.info("creating new map file")
            #self.updateInventoryItemIdMap("ppp",1919)
        else:
            with open(self.sfileName,'w') as json_file: 
                json.dump(self.dTheMap, json_file)

    def updateInventoryItemIdMap(self,key,val):
        with open(self.sfileName, 'w') as fp:
            self.dTheMap[key]=val
            json.dump(self.dTheMap, fp,sort_keys=True,indent=4)
    
    def resetInventoryItemMap(self):
        self.dTheMap = {"000_ProductSKU:product.variant[n].inventory_item_id":1}
        #prods = cursor_based_bulk_fetch_products()
        sps = ShopifyProducts()
        prods = sps.dProducts
        for p in prods.values():
            #logging.info("title:"+p.title)
            #logging.info("variant[0].inventory_item_id="+str(p.variants[0].inventory_item_id))
            livesku = p.variants[0].sku
            iii = p.variants[0].inventory_item_id
            self.updateInventoryItemIdMap(livesku,iii)

#########################################
#########################################
#########################################

# Shopify id lookup by Coaster SKU
class ProductMapping:
    dTheMap = {"000_ProductSKU:product.id":1}
    sfileName = "MapCoaster.json"
    def __init__(self):
        if os.path.exists(self.sfileName):
            with open(self.sfileName) as json_file: 
                try:
                    self.dTheMap = json.load(json_file) 
                except:
                    logging.info("creating new map file")
        else:
            with open(self.sfileName,'w') as json_file: 
                json.dump(self.dTheMap, json_file)

    def getShopifyID(self,sku):
        try:
            return self.dTheMap[sku]
        except:
            return 0

    def updateCoasterMap(self,key,val):
        with open(self.sfileName, 'w') as fp:
            self.dTheMap[key]=val
            json.dump(self.dTheMap, fp,sort_keys=True,indent=4)

    def resetProductMap(self):
        self.dTheMap = {"000_ProductSKU:product.id":1}
        prods = cursor_based_bulk_fetch_products()
        for p in prods:
            #logging.info("title:"+p.title)
            #logging.info("variant[0].inventory_item_id="+str(p.variants[0].inventory_item_id))
            livesku = p.variants[0].sku
            thid = p.id
            self.updateCoasterMap(livesku,thid)

#########################################
#########################################
#########################################

#def upsertLiveShopifyProduct(objShopifyProduct):
#
#
#    sps = ShopifyProducts()
#    # check live products for deletion
#    # Delete products that match a certain criteria
#
#
#    sProductType = ""
#    pNum = objShopifyProduct.variants[0].sku
#    oLiveProduct = sps.dProductMapBySupplierSKU[pNum]
#    #coasterfilepath = 'C:/Projects/CoasterAPI/coasterapi/coasterwebjson/'+ pNum +".json"
#    #if os.path.exists(coasterfilepath):
#    #    with open(coasterfilepath,encoding='utf-8') as json_file:
#    #        jCoasterWeb = json.load(json_file)
#    #        tags = ','.join(jCoasterWeb["Breadcrumb"])
#    #        #new_product.tags = tags
#    #        sProductType = jCoasterWeb["Breadcrumb"][-1]
#    #    # update the product title
#    #    if objShopifyProduct.title != jCoasterWeb["Title"]: 
#    #        objShopifyProduct.title =  jCoasterWeb["Title"]
#    #        try:
#    #            success = objShopifyProduct.save() #returns false if the record is invalid
#    #            time.sleep(1)
#    #            logging.info("sleep upsertLiveShopifyProduct save with new title")
#    #        except Exception as e:
#    #            logging.info("Cannot update title for "+pNum+". Problem with product id find. Did the id change, or was the product on the website removed?")
#    #            logging.info(e)
#    #            return
#
#
#    try:
#        price = getPrice(pNum)
#        if objShopifyProduct.variants[0].price != price:
#            logging.info("Updated price for:"+pNum)
#            objShopifyProduct.variants[0].price = price
#            if bPersistToShopify:
#                objShopifyProduct.variants[0].save()
#                time.sleep(1)
#    except Exception as e:
#        logging.info("Cannot update price for "+pNum+". Problem with product id find. Did the id change, or was the product on the website removed?")
#        logging.info(e)
#        return



############################################################
##
## Inventory
##
############################################################
def getInventoryCountFromShopifyLocation(inventory_item_id):
    available = 0
    for item in inventorycounts:
        if item.attributes["inventory_item_id"] == int(inventory_item_id):
            available = item.attributes["available"]
            break
    return available

def updateAllInventoryCounts():
    sps = ShopifyProducts()
    totalUpdateCount = 0
    totalNotUpdatedCount = 0
    for p in sps.dProducts.values():
        if updateInventoryCount(p):
            totalUpdateCount = totalUpdateCount + 1
        else:
            totalNotUpdatedCount = totalNotUpdatedCount +1
    logging.info(f"Total inventory updates:{totalUpdateCount} Total no changes:{totalNotUpdatedCount}")

#oLocation = shopify.Location.find(locationid)
#oLocation2 = shopify.Location({'id':locationid})
#oLocation = shopify.Location(locationid)

def updateInventoryProperties(shopify_variant):
    bSave = False
    if shopify_variant.inventory_management != "shopify":
        shopify_variant.inventory_management = "shopify"
        bSave = True
        #shopify_variant.save()
        #time.sleep(1)
        #logging.info("7sleep")
    if shopify_variant.fulfillment_service != "manual":
        bSave = True
        shopify_variant.fulfillment_service = "manual"
        #shopify_variant.save()
        #time.sleep(1)
        #logging.info("8sleep")
    # manage exception list
    #inventoryOrderExceptions=["603270PP","723262","723271"]
    #if sCoasterSKU in inventoryOrderExceptions:
    #    if shopify_variant.inventory_policy != "continue":
    #        bSave = True
    #        shopify_variant.inventory_policy = "continue"
    #        #shopify_variant.save()
    #        #time.sleep(1)
    #        #logging.info("9sleep")
    #else:
    if shopify_variant.inventory_policy != "deny":
        bSave = True
        shopify_variant.inventory_policy = "deny"
            #shopify_variant.save()
            #time.sleep(1)
            #logging.info("10 sleep")
    if bSave:
        time.sleep(.6)
        shopify_variant.save()
        logging.info("10 sleep .6")

#zzz
# TODO Bring the business logic from the updateInventory method here and collapse the code
def updateInventoryNew(shopify_id, inventory_item_id, supplierInvCount):
    returnme = False
    sps = ShopifyProducts()
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
    # manage exception list
    #inventoryOrderExceptions=["603270PP","723262","723271"]
    # TODO Read the exceptions list, by vendor, from a Google spreadsheet. Or, add to the admin portal
    #if sCoasterSKU in inventoryOrderExceptions:
    #    if shopify_variant.inventory_policy != "continue":
    #        bSave = True
    #        shopify_variant.inventory_policy = "continue"
    #        #shopify_variant.save()
    #        #time.sleep(1)
    #        #logging.info("9sleep")
    #else:
    if shopify_variant.inventory_policy != "deny":
        bSave = True
        shopify_variant.inventory_policy = "deny"
    
    if bSave:
        returnme = True
        time.sleep(.6)
        shopify_variant.save()

    bSave = True
    #######################################
    # Code for inventory count manipulation
    #
    #
    websitecount = getInventoryCountFromShopifyLocation(inventory_item_id)
    #websitecount = oProduct.variants[0].inventory_quantity
    supplierInvCount=int(supplierInvCount)
    if websitecount == None:
        websitecount = 0
    websitecount=int(websitecount)
    # TODO only update the level if the count is below 5 or the shopify count is below 5
    # 
    #if websitecount == supplierInvCount:
    #    #logging.info("    No inventory change for:"+pNum)
    #    pass
    # Use cases:
    #   websitecount = 1, supplierInvCount = 1  Shopify warehouse location should be set to 0
    #   websitecount = 4, supplierInvCount = 4  Shopify warehouse location should be set to 0
    if websitecount > 5 and supplierInvCount > 5:
        # we don't care about inventory changes when the inventory is sufficient
        logging.info("    Inventory is above 5 for:"+pNum)
        pass

    else:
        # if there is only one or two in stock, don't show as available on our website
        #elif coastercount <= 1:
        #    coastercount = 0
        supplierInvCount=int(supplierInvCount)
        if supplierInvCount <= 2 and websitecount == 0:
            pass
        if supplierInvCount <= 2:
            supplierInvCount = 0
        time.sleep(.6)
        if websitecount != supplierInvCount:
            # TODO wrap in try/catch
            inventory_level = shopify.InventoryLevel.set(int(locationid), inventory_item_id, supplierInvCount)
            logging.info("   Updated inventory from "+str(websitecount)+" to " + str(supplierInvCount) + " for:"+pNum )
            bSave = True

    ##
    ##########################

    if bSave:
        returnme = True
        time.sleep(.6)
        shopify_variant.save()
    
    return returnme

# only update the inventory count
def updateInventoryCount(shopifyProduct, suppliercount):
#def updateInventoryCount(shopify_id, quantity):
    
    #if(type(coasterJSONObj)!=list):
    #    logging.info("This is an invalid produt JSON object")
    #    return
    # Get a specific product
    shopifyproductid = "" 
    pNum = "" 
    # TODO fix location ID
    #shopify.InventoryLevel.set(locationid, shopify_id, 5)
    #shopify.InventoryLevel.set(locationid, shopify_id, quantity)
    pNum = shopifyProduct.variants[0].sku
    shopify_variant = shopifyProduct.variants[0]
    updateInventoryProperties(shopify_variant)

    updated=False
    if pNum != None:
        shopifyproductid = shopifyProduct.id 
        try:
            iInventoryItemId = shopifyProduct.variants[0].inventory_item_id 
            # https://community.shopify.com/c/Shopify-APIs-SDKs/Inventory-item-does-not-have-inventory-tracking-enabled/td-p/612845
            # https://shopify.dev/docs/admin-api/rest/reference/products/product-variant?api[version]=2020-04
            # TODO move these out to a separate function. these are rare events which need the variant object. The inventory change doesn't need the variant object
            # TODO increase processing time by eliminating the call to InventoryLevel
            # TODO cache the shopify inventory level set to either True or False 
            # TODO create a function to reset the inventory cache
            #logging.info("--10.1 sleep-get live inventory level available")
            #time.sleep(.5)
            websitecount = shopifyProduct.variants[0].inventory_quantity
            #websitecount = shopify.InventoryLevel.connect(locationid,iInventoryItemId).available
            #time.sleep(.5)

            if websitecount == None:
                websitecount = 0
            
            # make sure the website never shows only one in stock
            #if websitecount == 1:
            #    websitecount = 0

            #coastercount = inventoryCount.getInventoryCount(pNum)
            # TODO only update the level if the coaster count is below 5 or the shopify count is below 5? think this through
            if websitecount > 5 and suppliercount > 5:
                # we don't care about inventory changes when the inventory is sufficient
                logging.info("Inventory is above 5 for:"+pNum)
                pass
            elif websitecount != suppliercount:
                # if there is only one in stock, don't show as available on our website
                #if coastercount <= 1 and websitecount == 0:
                #    return updated
                #if coastercount > 6 and websitecount > 6:
                #    return updated
                #elif coastercount <= 1:
                #    coastercount = 0
                suppliercount=int(suppliercount)
                inventory_level = shopify.InventoryLevel.set(locationid, iInventoryItemId, suppliercount)
                time.sleep(1.5)
                logging.info("Updated inventory from "+str(websitecount)+" to " + str(suppliercount) + " for:"+pNum )
                updated = True
            elif websitecount == suppliercount:
                logging.info("No inventory change for:"+pNum)
                pass
            # skip if the counts haven't changed
            #elif websitecount < 3 and coastercount > 3:
            #    inventory_level = shopify.InventoryLevel.set(locationid, iInventoryItemId, coastercount)
            #    time.sleep(.5)
            #    logging.info("--11.1 sleep-set inventory level")
            #    logging.info("Updated inventory from "+str(websitecount)+" to "+str(coastercount)+" for:"+pNum )
            #    updated = True
            ## set the website to out of stock if coaster has 2 or less in inventory
            #elif websitecount > 3 and coastercount < 2:
            #    inventory_level = shopify.InventoryLevel.set(locationid, iInventoryItemId, 0)
            #    time.sleep(.5)
            #    logging.info("--11.2 sleep-set inventory level")
            #    logging.info("Updated inventory from "+str(websitecount)+" to 0 for:"+pNum )
            #    updated = True
            else:
                logging.info("No change to inventory for:"+pNum )

                
        except Exception as e:
            logging.info("Exception: Cannot update Inventory Count for SKU:"+pNum+" Problem with product id find. Did the id change, or was the product on the website removed?")
            logging.info(e)
    else:
        logging.info("Cannot update Inventory Count for SKU:"+pNum+" Problem with product sku. there is no Sku for this product ")
    return updated

############################################################
##
## Prices
##
############################################################

def getPrice(productnumber):
    # open the price file
    newprice = 100000
    with open('C:/Projects/CoasterAPI/coasterapi/prices/all_coaster_prices.json') as file_handle:
        jPrices = json.load(file_handle)
    for i in jPrices[0]["PriceList"]:
        if i['ProductNumber'] == productnumber:
            #logging.info(i['MAP'])
            #logging.info(i['Price'])
            theprice = i['Price']
            shipping = theprice *.17
            markupspread = theprice * .90
            newprice = theprice + shipping + markupspread

            break

    return newprice

# TODO delete this method
def updateAllPrices():
    # default location id:36481335376
    #API_VERSION = "2020-04"
    #shop_url = "https://%s:%s@red-rock-luxury-furniture-2.myshopify.com/admin/api/%s" % (config.data["API_KEY"], config.data["PASSWORD"], API_VERSION)
    #shopify.ShopifyResource.set_site(shop_url)
    #shop = shopify.Shop.current()

    # open each json file in the directory
    os.chdir("C:/Projects/CoasterAPI/coasterapi/cached_json")
    logging.info("Updating prices")
    for file in glob.glob("*.json"):
        #logging.info(file)
        with open('C:/Projects/CoasterAPI/coasterapi/cached_json/'+file) as json_file:
            coasterobj = json.load(json_file)
            updatePrice(coasterobj)
        #images = data[0]["ListNextGenImages"]

############################################################
############################################################
############################################################
# https://stackoverflow.com/questions/43575659/how-to-get-all-product-id-from-shopify-python-api
# https://www.shopify.com/partners/blog/relative-pagination
# https://github.com/Shopify/shopify_api/pull/594/files

#def get_all_resources(resource, **kwargs):
#    resource_count = resource.count(**kwargs)
#    resources = []
#    if resource_count > 0:
#        for page in range(1, ((resource_count-1) // 150) + 2):
#            kwargs.update({"limit" : 150, "page" : page})
#            resources.extend(resource.find(**kwargs))
#    return resources

def resetShopifyCache():
    try:
        thefulljsonpath = os.path.join(thebaseshopifylogpath, thejsonfilename)
        if os.path.exists(thefulljsonpath):
            os.remove(thefulljsonpath)
        sps = ShopifyProducts()
        sps.reloadProducts()
    except Exception as e:
        print(e)

def cursor_based_bulk_fetch_products(limit=250):
    products = []

    #zzz
    usecache=False
    thefulljsonpath = os.path.join(thebaseshopifylogpath, thejsonfilename)

    # if the cache exists, use it. Otherwise, create the cache
    if os.path.exists(thefulljsonpath) and usecache:
        logging.debug("Loading Shopify products from cache")
        f = open(thefulljsonpath)
        import jsonpickle
        json_str = f.read()
        allShopifyProducts = jsonpickle.decode(json_str)
        #with open(thefulljsonpath) as outfile2:
        #    allShopifyProducts = json.load(outfile2)
    else:
        logging.debug("Loading Shopify products from Shopify")
        allShopifyProducts = get_products(products,limit=limit)
        f = open(thefulljsonpath, 'w')
        import jsonpickle
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
    #logging.info('chunk fetched: %s' % chunk)
    if cache != page_info:
        time.sleep(1)
        return get_products(products, page_info, chunk+1, limit)
    return products

#prods = cursor_based_bulk_fetch_products()

# TODO delete all products that are zero inventory and are IsDiscontinued
# Deletes a product by its Shopify product ID (not the vendor's SKU)
############################################################
############################################################
############################################################

# get the supplemental images and information from the screen scrape data 
def upsertShopifyProduct(productJSON,bUpdateImages=False):
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
    sps = ShopifyProducts()
    oProduct = None
    try:
        oProduct = sps.dProductMapBySupplierSKU[pNum]
    except:
        oProduct = None

    if oProduct == None:
        oProduct = shopify.Product()
        is_new_product = True
        logging.info("    Product does not exist in Shopify: "+ str(pNum))

    if is_new_product: 
        bUpdateImages = True
        oProduct.title = productJSON["Name"]
        oProduct.vendor = productJSON["Vendor"]
        oProduct.body_html = productJSON["Description"]
        oProduct.product_type = productJSON["product_type"]
        #print(pNum)
        oProduct.SKU = pNum

        #theprice = getPrice(pNum)
        # Set the Price
        variant = shopify.Variant(dict(price=productJSON["RRFO_PRICE"])) # attributes can     be set at creation
        oProduct.variants = [variant]
        oProduct.variants[0].sku = pNum
        success = oProduct.save() #returns false if the record is invalid
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
            returnmeupdated=True
            # Don't set saveChanges because the updateInventory method handled the save
            # the save happens on the variant
            #saveChanges = True

    if ("%.2f" % float(oProduct.variants[0].price)) != ("%.2f" % float(productJSON["RRFO_PRICE"])):
        logging.info("    Price changed from:"+ oProduct.variants[0].price + " to:"+ productJSON["RRFO_PRICE"])
        oProduct.variants[0].price = productJSON["RRFO_PRICE"]
        saveChanges = True

    # Check for tag changes
    if not myArrayCompare(oProduct.tags,productJSON["Tags"]):
        oProduct.tags = productJSON["Tags"]
        saveChanges = True
        logging.info("    Tags changed from:"+oProduct.tags + "to:"+productJSON["Tags"])

    # check for change in description
    text = oProduct.body_html.replace('\n','')
    if text != productJSON["Description"]:
        oProduct.body_html = productJSON["Description"]
        saveChanges = True
        logging.info("    Description changed")
    
    saveEnabled = True
    if saveChanges:
        logging.info("    Saving updates: "+pNum)
        returnmeupdated=True
        if saveEnabled:
            oProduct.save()
            time.sleep(1.5)

    # Create a new product
    try:
        # https://community.shopify.com/c/Shopify-APIs-SDKs/Python-Shopify-API-attach-or-add-a-image-from-url-scr/td-p/547528
        #if bUpdatedProduct:
        #    if bPersistToShopify:
        #        #success = oProduct.save() #returns false if the record is invalid
        #        #time.sleep(1)
        #        #logging.info("2sleep save new product")
        #        # save the product id to the json file
        #        #cm.updateCoasterMap(pNum, oProduct.id)
        #        # TODO fix this update. it is no longer needed. 
        #        #iiim.updateInventoryItemIdMap(pNum,oProduct.variants[0].inventory_item_id)
        #        #shopifyproductid = cm.dTheMap[pNum] 
        #        #resetInventory(productJSON)
        #    else:
        #        logging.info("skipped save of product:" + pNum)
        #else:
        #    logging.info("no changes to product")
            #productJSON[0]["shopifyproductid"] = oProduct.id
            #filename ='C:/Projects/CoasterAPI/coasterapi/cached_json/'+ pNum+ ".json"
            #with open(filename, "w") as outfile:
            #    json.dump(productJSON, outfile)

        # images = shopify.Image.find(product_id=productJSON[0]["shopifyproductid"])
        # im[0]
        # im.attributes
        # 
        #if bPersistToShopify:
        # Don't add the images if they already exist on the live shopify site
        # Need to verify if images really get added twice
        # need to verify if all these sleeps are necessary
        if bUpdateImages: 
            logging.info("    Updating images: "+pNum)
            time.sleep(.5)
            liveImages = shopify.Image.find(product_id=oProduct.id)
            for img_url in productJSON["Images"]:
                b_image_already_live = False
                #print(img_url)
                imgfilename = img_url.split('/')[-1].replace(" ","_")
                for liveimage in liveImages:
                    if "products/" + imgfilename in liveimage.src:
                        b_image_already_live = True
                        break
                if not b_image_already_live:
                    #print("add the image to shopify:"+img)
                    #filecheck = os.path.join(currentDir,imgfilename)
                    #ImageDl(img,filecheck)
                    #shopifyimage = shopify.Image({"product_id":oProduct.id})
                    # Add images by URL
                    #print("Adding image to Shopify: "+url)
                    image = shopify.Image({"product_id":oProduct.id})
                    image.src = img_url
                    time.sleep(.5)
                    image.save()
                    #with open(filecheck, "rb") as f:
                    #    shopifyimage.attach_image(f.read(), filename=imgfilename)
                    #    shopifyimage.save()
                    #    returnmeimages = True 
                    #    time.sleep(4)
                        #print("added image to shopify")
                    #os.remove(filecheck)
        return "New obj:"+str(returnmenew) + " Udated:"+str(returnmeupdated) + " Updated images:"+str(returnmeimages)
    except Exception as e:
        logging.error("    error loading product")
        logging.error(e)
        return "New obj:"+str(returnmenew) + " Udated:"+str(returnmeupdated) + " Updated images:"+str(returnmeimages)

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'}

def ImageDl(url,filepath):
    attempts = 0
    while attempts < 5:
        try:
            r = requests.get(url,headers=headers,stream=True,timeout=30)
            if r.status_code == 200:
                #with open(os.path.join(path,filename),'wb') as f:
                with open(filepath,'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw,f)
                #print('Downloading image: {}'.format(filename))
            break
        except Exception as e:
            attempts+=1
            print(e)

# New functions adjusted written by Brandon. 
# Hopefully we can merge these with the others so all the vendors use the same flow.
# Adds a product to ShopifyJ 

# Let's use the upsert method instead of this one 
# TODO - remove this method
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
            #print("Adding image to Shopify: "+url)
            image = shopify.Image({"product_id":oProduct.id})
            image.src = url
            image.save()

        # Returns the shopify product ID so it can be stored with its corresponding SKU
        return oProduct.id
    except Exception as e:
        logging.info("Error adding SKU " + productJSON["ProductNumber"] + " to Shopify: " + str(e))
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
#zzz TODO replace this find method - only call save if the price has changed
# TODO Only update price if there was a change
        oProduct = shopify.Product.find(shopify_id)
        oProduct.variants[0].price = price # price
        oProduct.save()
    except Exception as e:
        logging.info("Failed to update price: " + str(shopify_id))
        logging.info(e)

# Updates the inventory on a Shopify product
# Delete this method
def updateInventory(shopify_id, quantity):
    try:
        #zzz
        sps = ShopifyProducts()
        prods = sps.dProducts
        #oProduct = shopify.Product.find(shopify_id)
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
        # manage exception list
        #inventoryOrderExceptions=["603270PP","723262","723271"]
        #if sCoasterSKU in inventoryOrderExceptions:
        #    if shopify_variant.inventory_policy != "continue":
        #        bSave = True
        #        shopify_variant.inventory_policy = "continue"
        #        #shopify_variant.save()
        #        #time.sleep(1)
        #        #logging.info("9sleep")
        #else:
        if shopify_variant.inventory_policy != "deny":
            bSave = True
            shopify_variant.inventory_policy = "deny"
        if oProduct.variants[0].inventory_available != quantity:
            oProduct.variants[0].inventory_available = quantity
            bSave = True
            #oProduct.save()
        if bSave:
            time.sleep(.6)
            shopify_variant.save()

    except Exception as e:
        logging.info("Failed to update inventory: " + str(shopify_id))
        logging.info(e)


def myArrayCompare(s1,s2):
    # convert the string to an array
    # remove all spaces from the string
    # sort the array
    if s1 == None:
        s1 = ""
    if s2 == None:
        s2 = ""
    s1=s1.replace(" ","")
    s2=s2.replace(" ","")
    a1 = s1.split(",")
    a2 = s2.split(",")
    a1 = list(set(a1))
    a2 = list(set(a2))
    a1 = sorted(a1)
    a2 = sorted(a2)
    return a1 == a2
