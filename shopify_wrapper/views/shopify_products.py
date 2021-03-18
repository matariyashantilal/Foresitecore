import logging

from . import shopify_products
from .common_function import *


class ShopifyProducts:
    dProducts = {}
    # get shopify product by coaster sku
    dProductMapBySupplierSKU = {}

    def __init__(self):
        if len(self.dProducts) == 0:
            prods = shopify_products.cursor_based_bulk_fetch_products()
            for p in prods:
                self.dProducts[p.id] = p
                self.dProductMapBySupplierSKU[p.variants[0].sku] = p

    def reloadProducts(self):
        self.dProducts = {}
        prods = cursor_based_bulk_fetch_products()
        for p in prods:
            self.dProducts[p.id] = p

    def uploadProduct(self, tempAvailabilityProductSKU, tempAvailabilityProductSKUList):
        if int(len(self.dProducts)) > int(0):
            for p in self.dProducts.values():
                if(p.variants[0].sku in tempAvailabilityProductSKU):
                    updateInventoryCount(
                        p, tempAvailabilityProductSKUList[p.variants[0].sku])
