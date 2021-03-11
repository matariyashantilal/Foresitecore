import shopify
import time
import requests
import json
from json.decoder import JSONDecodeError
import shutil
from base64 import b64encode
import glob, os
import logging

#logging.basicConfig(filename='foresitefurniture.log',level=logging.DEBUG)
#logging.basicConfig(filename='foresitefurniture.log',level=logging.WARNING)
logging.basicConfig(filename='foresitefurniture.log',level=logging.INFO)

# TODO introduct the ability to reset a product

currentDir = os.getcwd()

shopify.ShopifyResource.set_site(os.environ.get("SHOPIFY_SECUREURL"))
uttermostfile = os.environ.get("UTERMOST_CATALOG")
#shop = shopify.Shop.current()

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
#    sSupplierSKU = objShopifyProduct.variants[0].sku
#    oLiveProduct = sps.dProductMapBySupplierSKU[sSupplierSKU]
#    #coasterfilepath = 'C:/Projects/CoasterAPI/coasterapi/coasterwebjson/'+ sSupplierSKU +".json"
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
#    #            logging.info("Cannot update title for "+sSupplierSKU+". Problem with product id find. Did the id change, or was the product on the website removed?")
#    #            logging.info(e)
#    #            return
#
#
#    try:
#        price = getPrice(sSupplierSKU)
#        if objShopifyProduct.variants[0].price != price:
#            logging.info("Updated price for:"+sSupplierSKU)
#            objShopifyProduct.variants[0].price = price
#            if bPersistToShopify:
#                objShopifyProduct.variants[0].save()
#                time.sleep(1)
#    except Exception as e:
#        logging.info("Cannot update price for "+sSupplierSKU+". Problem with product id find. Did the id change, or was the product on the website removed?")
#        logging.info(e)
#        return


# get the supplemental images and information from the screen scrape data
def upsertShopifyProduct(productJSON,bUpdateImages=True):

    is_new_product = False
    # We don't want to create duplicates in the catalog
    # See if the product is already in the online catalog 
    sps = ShopifyProducts()
    sSupplierSKU = productJSON["ProductNumber"]
    oProduct = None
    try:
        oProduct = sps.dProductMapBySupplierSKU[sSupplierSKU]
    except:
        oProduct = None

    if oProduct == None:
        oProduct = shopify.Product()
        is_new_product = True
        logging.info("Product does not exist in Shopify: "+ str(sSupplierSKU))
    else:
        logging.info("Product already exists: "+sSupplierSKU)

    if is_new_product: 
        oProduct.title = productJSON["Name"]
        oProduct.vendor = productJSON["Vendor"]
        oProduct.body_html = productJSON["Description"]
        oProduct.product_type = ""
        print(sSupplierSKU)
        oProduct.SKU = sSupplierSKU
       
        #theprice = getPrice(sSupplierSKU)
        # Set the Price
        variant = shopify.Variant(dict(price=productJSON["MAP"])) # attributes can     be set at creation
        oProduct.variants = [variant]
        oProduct.variants[0].sku = sSupplierSKU
        success = oProduct.save() #returns false if the record is invalid
        time.sleep(1)
    bUpdateProduct = False
    # check for differences
    if oProduct.tags != productJSON["Tags"]:
        oProduct.tags = productJSON["Tags"]
        bUpdateProduct = True
    if oProduct.body_html != productJSON["Description"]:
        oProduct.body_html = productJSON["Description"]
        bUpdateProduct = True
    
    if bUpdateProduct:
        oProduct.save()
        time.sleep(1.5)

    # Create a new product
    try:
        logging.info("placeholder code to add images ")

        # https://community.shopify.com/c/Shopify-APIs-SDKs/Python-Shopify-API-attach-or-add-a-image-from-url-scr/td-p/547528
        #if bUpdatedProduct:
        #    if bPersistToShopify:
        #        #success = oProduct.save() #returns false if the record is invalid
        #        #time.sleep(1)
        #        #logging.info("2sleep save new product")
        #        # save the product id to the json file
        #        #cm.updateCoasterMap(sSupplierSKU, oProduct.id)
        #        # TODO fix this update. it is no longer needed. zzz
        #        #iiim.updateInventoryItemIdMap(sSupplierSKU,oProduct.variants[0].inventory_item_id)
        #        #shopifyproductid = cm.dTheMap[sSupplierSKU] 
        #        #resetInventory(productJSON)
        #    else:
        #        logging.info("skipped save of product:" + sSupplierSKU)
        #else:
        #    logging.info("no changes to product")
#
            #productJSON[0]["shopifyproductid"] = oProduct.id
            #filename ='C:/Projects/CoasterAPI/coasterapi/cached_json/'+ sSupplierSKU+ ".json"
            #with open(filename, "w") as outfile:
            #    json.dump(productJSON, outfile)

        # images = shopify.Image.find(product_id=productJSON[0]["shopifyproductid"])
        # im[0]
        # im.attributes
        # 
        #if bPersistToShopify:
        if bUpdateImages:
            liveImages = shopify.Image.find(product_id=oProduct.id)
            for img in productJSON["Images"]:
                b_image_already_live = False
                #print(img)
                imgfilename = img.split('/')[-1].replace(" ","_")
                for liveimage in liveImages:
                    if "products/" + imgfilename in liveimage.src:
                        b_image_already_live = True
                        break
                if not b_image_already_live:
                    print("add the image to shopify:"+img)
                    filecheck = os.path.join(currentDir,imgfilename)
                    ImageDl(img,filecheck)
                    shopifyimage = shopify.Image({"product_id":oProduct.id})
                    with open(filecheck, "rb") as f:
                        shopifyimage.attach_image(f.read(), filename=imgfilename)
                        shopifyimage.save()
                        time.sleep(1)
                        print("added image to shopify")
                    os.remove(filecheck)
                
    except Exception as e:
        logging.info("error loading product")
        logging.info(e)

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

############################################################
##
## Inventory
##
############################################################

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

# only update the inventory count
def updateInventoryCount(shopifyProduct):
    #if(type(coasterJSONObj)!=list):
    #    logging.info("This is an invalid produt JSON object")
    #    return
    # Get a specific product
    shopifyproductid = "" 
    sSupplierSKU = "" 
    locationid = 1
    # TODO fix location ID
    
    sSupplierSKU = shopifyProduct.variants[0].sku
    updated=False
    if sSupplierSKU != None:
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
            if websitecount == None:
                websitecount = 0
            
            # make sure the website never shows only one in stock
            #if websitecount == 1:
            #    websitecount = 0

            coastercount = inventoryCount.getInventoryCount(sSupplierSKU)
            # TODO only update the level if the coaster count is below 5 or the shopify count is below 5? think this through
            if websitecount > 5 and coastercount > 5:
                # we don't care about inventory changes when the inventory is sufficient
                logging.info("Inventory is above 5 for:"+sSupplierSKU)
                pass
            elif websitecount != coastercount:
                # if there is only one in stock, don't show as available on our website
                #if coastercount <= 1 and websitecount == 0:
                #    return updated
                #if coastercount > 6 and websitecount > 6:
                #    return updated
                #elif coastercount <= 1:
                #    coastercount = 0
                inventory_level = shopify.InventoryLevel.set(locationid, iInventoryItemId, coastercount)
                time.sleep(.5)
                logging.info("Updated inventory from "+str(websitecount)+" to " + str(coastercount) + " for:"+sSupplierSKU )
                updated = True
            elif websitecount == coastercount:
                logging.info("No inventory change for:"+sSupplierSKU)
                pass
            # skip if the counts haven't changed
            #elif websitecount < 3 and coastercount > 3:
            #    inventory_level = shopify.InventoryLevel.set(locationid, iInventoryItemId, coastercount)
            #    time.sleep(.5)
            #    logging.info("--11.1 sleep-set inventory level")
            #    logging.info("Updated inventory from "+str(websitecount)+" to "+str(coastercount)+" for:"+sSupplierSKU )
            #    updated = True
            ## set the website to out of stock if coaster has 2 or less in inventory
            #elif websitecount > 3 and coastercount < 2:
            #    inventory_level = shopify.InventoryLevel.set(locationid, iInventoryItemId, 0)
            #    time.sleep(.5)
            #    logging.info("--11.2 sleep-set inventory level")
            #    logging.info("Updated inventory from "+str(websitecount)+" to 0 for:"+sSupplierSKU )
            #    updated = True
            else:
                logging.info("No change to inventory for:"+sSupplierSKU )

                
        except Exception as e:
            logging.info("Exception: Cannot update Inventory Count for SKU:"+sSupplierSKU+" Problem with product id find. Did the id change, or was the product on the website removed?")
            logging.info(e)
    else:
        logging.info("Cannot update Inventory Count for SKU:"+sSupplierSKU+" Problem with product sku. there is no Sku for this product ")
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

def updatePrice(coasterJSONObj):
    if(type(coasterJSONObj)!=list):
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
            logging.info("Cannot update price for "+sSupplierSKU+". Problem with product id find. Did the id change, or was the product on the website removed?")
            logging.info(e)
            return
    else:
        logging.info("Cannot update price for "+sSupplierSKU+". Problem with product id find. Did the id change, or was the product on the website removed?")
        return

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


def cursor_based_bulk_fetch_products(limit=250):
    products = []
    return get_products(products,limit=limit)


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
        return get_products(products, page_info, chunk+1, limit)
    return products


#prods = cursor_based_bulk_fetch_products()

#"100186B1": 4482243788867,
#"100186B2": 4482243919939,
# TODO delete all products that are zero inventory and are IsDiscontinued
def deleteProduct(shopifyproductid):
    time.sleep(1)
    try:
        shopify.Product.delete(shopifyproductid)
        logging.info("Deleted product"+str(shopifyproductid))
    except Exception as e:
        logging.info("Exception- could not delete product:"+str(shopifyproductid))
        logging.info(e)


############################################################
############################################################
############################################################