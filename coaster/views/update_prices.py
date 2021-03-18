import logging
import os

from coaster.views import api
from django.conf import settings
from django.http import HttpResponse
from shopify_wrapper import views as shopify
from shopify_wrapper.views import productObj

# Set up logging config
logging.basicConfig(filename='coaster.log', level=logging.WARNING)


def update_prices(request):
    """Updates all the prices for a vendor.
    """
    try:
        sps = shopify.ShopifyProducts()
        for p in sps.dProducts.values():
            if p.attributes["vendor"] == "Coaster":
                # get the suppliers inventory count for this product
                pNum = p.attributes["variants"][0].sku
                price = productObj.getPrice(pNum)
                shopify_id = p.attributes["id"]
                shopify.updatePrice(shopify_id, price)

        return HttpResponse("Updated RRFO prices for Coaster on the Shopify site")

    except Exception as e:
        # remove unneccesary variable
        logging.info("Cannot update price for "
                     ". Problem with product id find. Did the id change, or was the product on the website removed?")
        logging.info(e)
        return HttpResponse("Cannot update price")
