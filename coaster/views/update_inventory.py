import json
import os

from coaster.views import api, inventory_count, scraper
from django.conf import settings
from django.http import HttpResponse
from shopify_wrapper import views as shopify
from shopify_wrapper.views import productObj



# scraper class object
scrapeObj = scraper.Scraper()


def update_inventory(request):
    """Updates inventory for everything in the vendor's product list.
    """
    inventoryCount = inventory_count.InventoryCount()
    sps = shopify.ShopifyProducts()
    for p in sps.dProducts.values():
        if p.attributes["vendor"] == "Coaster":
            # get the suppliers inventory count for this product.
            sSupplierSKU = p.attributes["variants"][0].sku
            inventorycount = inventoryCount.getInventoryCount(sSupplierSKU)
            inventory_item_id = p.attributes["variants"][0].attributes["inventory_item_id"]
            shopify_id = p.attributes["id"]
            shopify.updateInventoryNew(
                shopify_id, inventory_item_id, inventorycount)
    return HttpResponse("Updated Coaster inventory counts on the Shopify site")
