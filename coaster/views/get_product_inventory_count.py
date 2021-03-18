import os

from . import api, inventory_count, scraper
from django.conf import settings
from django.http import HttpResponse
from shopify_wrapper.views import productObj

# Set up logging config

# scraper class object
scrapeObj = scraper.Scraper()


def get_product_inventory_count(request, pNum):
    inventoryCount = inventory_count.InventoryCount()
    inventorycount = inventoryCount.getInventoryCount(pNum)
    return HttpResponse(inventorycount)
