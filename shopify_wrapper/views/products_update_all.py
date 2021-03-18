import json
import logging
import os

from coaster.views import api
from django.http import HttpResponse
from . import product

productObj = product.products()


def products_update_all(request):
    return_me = ""
    # get the category json
    jObj = api.call("GetCategoryList", {})
    for p in jObj:
        # get all the objects in a category
        # thefilter = saveFilter("getFilter?categoryCode="+p["CategoryCode"])
        # saveCoasterProduct(thefilter,"CompleteCategory-"+p["CategoryName"])
        args = {'CategoryCode': p["CategoryCode"]}
        data = api.call("GetFilter", args)
        filter = json.dumps(data).strip('"')
        # Call the coaster API to get all the info for the products into a dictionary of objects
        args = {'filterCode': filter}
        products = api.call("GetProductList", args)
        return_me += productObj.processProducts(products)
    return HttpResponse(return_me)
