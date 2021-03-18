from . import api, inventory_count, scraper
from django.http import HttpResponse



def get_product_inventory_count(request, pNum):
    inventoryCount = inventory_count.InventoryCount()
    inventorycount = inventoryCount.getInventoryCount(pNum)
    return HttpResponse(inventorycount)
