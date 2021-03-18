import glob
import json
import logging
import os
from pathlib import Path

from django.http import HttpResponse
from . import shopify_products

thebaseshopifylogpath = os.environ.get("SHOPIFY_DIRECTORY_PATH")

thejsonfilename = "allshopifyproducts." + \
    str(os.environ.get("SHOPIFY_SHOP")) + ".json"

Path(str(thebaseshopifylogpath)).mkdir(parents=True, exist_ok=True)


def reset_shopify_cache(request):
    try:
        thefulljsonpath = os.path.join(thebaseshopifylogpath, thejsonfilename)
        if os.path.exists(thefulljsonpath):
            os.remove(thefulljsonpath)
        sps = shopify_products.ShopifyProducts()
        sps.reloadProducts()
        return HttpResponse("Reset shopify cache")
    except Exception as e:
        print(e)
