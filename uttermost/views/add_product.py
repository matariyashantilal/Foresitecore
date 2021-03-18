import os

from django.http import HttpResponse

from . import manage_uttermost_products

manageuttermostproductsObj = manage_uttermost_products.ManageUttermostProducts()


def add_product(request, sku_list):
    """Adds 1 or more comma delimited products from the  product list and Shopify.
    """
    try:
        result = ""
        sku_list = sku_list.split(",")
        result = manage_uttermost_products.ManageUttermostProducts().updateShopifyForAllCatalogs()
        if result == None:
            result = "Update return string for this vendor!!"
        return HttpResponse(result)
    except Exception as e:
        return HttpResponse("Failed to add Coaster products: " + str(e))
