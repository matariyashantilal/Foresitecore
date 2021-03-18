import json
import logging
import os
from . import shopify_products


class ProductMapping:
    dTheMap = {"000_ProductSKU:product.id": 1}
    sfileName = "MapCoaster.json"

    def __init__(self):
        if os.path.exists(self.sfileName):
            with open(self.sfileName) as json_file:
                try:
                    self.dTheMap = json.load(json_file)
                except:
                    logging.info("creating new map file")
        else:
            with open(self.sfileName, 'w') as json_file:
                json.dump(self.dTheMap, json_file)

    def getShopifyID(self, sku):
        try:
            return self.dTheMap[sku]
        except:
            return 0

    def updateCoasterMap(self, key, val):
        with open(self.sfileName, 'w') as fp:
            self.dTheMap[key] = val
            json.dump(self.dTheMap, fp, sort_keys=True, indent=4)

    def resetProductMap(self):
        self.dTheMap = {"000_ProductSKU:product.id": 1}
        prods = shopify_products.cursor_based_bulk_fetch_products()
        for p in prods:
            # logging.info("title:"+p.title)
            # logging.info("variant[0].inventory_item_id="+str(p.variants[0].inventory_item_id))
            livesku = p.variants[0].sku
            thid = p.id
            self.updateCoasterMap(livesku, thid)
