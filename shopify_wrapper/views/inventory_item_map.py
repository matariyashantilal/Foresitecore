import json
import logging
import os

from . import shopify_products


class InventoryItemIdMap:
    dTheMap = {"000_ProductSKU:product.variant[n].inventory_item_id": 1}
    sfileName = "MapInventoryItemId.json"

    def __init__(self):
        if os.path.exists(self.sfileName):
            with open(self.sfileName) as json_file:
                try:
                    self.dTheMap = json.load(json_file)
                except:
                    logging.info("creating new map file")
            # self.updateInventoryItemIdMap("ppp",1919)
        else:
            with open(self.sfileName, 'w') as json_file:
                json.dump(self.dTheMap, json_file)

    def updateInventoryItemIdMap(self, key, val):
        with open(self.sfileName, 'w') as fp:
            self.dTheMap[key] = val
            json.dump(self.dTheMap, fp, sort_keys=True, indent=4)

    def resetInventoryItemMap(self):
        self.dTheMap = {
            "000_ProductSKU:product.variant[n].inventory_item_id": 1}
        # prods = cursor_based_bulk_fetch_products()
        sps = shopify_products.ShopifyProducts()
        prods = sps.dProducts
        for p in prods.values():
            # logging.info("title:"+p.title)
            # logging.info("variant[0].inventory_item_id="+str(p.variants[0].inventory_item_id))
            livesku = p.variants[0].sku
            iii = p.variants[0].inventory_item_id
            self.updateInventoryItemIdMap(livesku, iii)
