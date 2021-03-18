from django.http import HttpResponse
from . import product

productObj = product.products()


def add_product(request, sku_list):
    """Adds 1 or more comma delimited products from the vendor's product list and Shopify.
    """
    try:
        result = ""
        sku_list = sku_list.split(",")
        result = productObj.addList(sku_list)
        if result == None:
            result = "Update return string for this vendor!!"
        return HttpResponse(result)
    except Exception as e:
        return HttpResponse("Failed to add Coaster products: " + str(e))
