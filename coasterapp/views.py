import json
import logging
import os

from django.http import HttpResponse

from coasterapp import coaster as Coaster

from coasterapp import shopify_helper_new
# import supplier_uttermost.manage_uttermost_products as Uttermost
# from lib_foresite import ImportEmailFromGmail, gmail_lib
from coasterapp.FOAProducts import main as FOA
from coasterapp.supplier_uttermost import (GetUttermostImageUrls,
                                           RemoveDiscontinued,
                                           manage_uttermost_products)

# from flask import Flask, render_template, request


logging.basicConfig(filename='foresitefurniture.log', level=logging.INFO)

# coaster = Flask(__name__)


# @coaster.route('/')
# def homepage():
#     return render_template('home.html')


def cacheUttermostImages(request):
    return HttpResponse(GetUttermostImageUrls.cache_uttermost_images_links())


# @coaster.route("/DeleteProducts")
# def deleteProducts():
#     supplier = request.args.get('supplier')
#     if supplier == "uttermost":
#         obj = Uttermost.removeproducts()
#         result = obj.test()
#     return result


def resetShopifyCache(request):
    shopify_helper_new.resetShopifyCache()
    return HttpResponse("Reset shopify cache")


def addProducts(request, vendor, sku_list):
    """Adds 1 or more comma delimited products from the vendor's product list and Shopify.
    """
    try:
        result = ""
        sku_list = sku_list.split(",")
        if (vendor == "coaster"):
            result = Coaster.add(sku_list)
        elif (vendor == "uttermost"):
            result = Uttermost.ManageUttermostProducts().updateShopifyForAllCatalogs()
        elif (vendor == "foa"):
            result = FOA.add(sku_list)
        else:
            result = vendor + " not recognized."

        if result == None:
            result = "Update return string for this vendor!!"
        return result
    except Exception as e:
        return HttpResponse("Failed to add Coaster products: " + str(e))


# @coaster.route("/removeproducts/<vendor>/<sku_list>")
# def removeProducts(vendor, sku_list):
#     """Removes 1 or more comma delimited products from the vendor's product list and Shopify
#     """
#     sku_list = sku_list.split(",")
#     if (vendor == "coaster"):
#         return Coaster.remove(sku_list)
#     elif (vendor == "uttermost"):
#         return "[TODO: Remove product (Uttermost)]"
#     elif (vendor == "foa"):
#         return FOA.remove(sku_list)
#     else:
#         return vendor + " not recognized."


def updatePrices(request, vendor):
    """Updates all the prices for a vendor.
    """
    if (vendor == "coaster"):
        return HttpResponse(Coaster.updatePrices())
    elif (vendor == "uttermost"):
        return HttpResponse("[TODO: Update prices (Uttermost)]")
    elif (vendor == "foa"):
        return HttpResponse("[TODO: Update prices (FOA)]")
    else:
        return HttpResponse(vendor + " not recognized.")


def getSupplierInventoryCounts(requets, vendor):
    """Gets inventory counts from the supplier
    """
    if (vendor == "coaster"):
        return HttpResponse(Coaster.getSupplierInventoryCounts())


def getProductInventoryCount(request, vendor, pNum):
    """Gets inventory counts from the supplier.
    """
    if (vendor == "coaster"):
        return HttpResponse(str(Coaster.getProductInventoryCount(pNum)))


def updateInventory(request, vendor):
    """Updates inventory for everything in the vendor's product list.
    """
    if (vendor == "coaster"):
        return HttpResponse(Coaster.updateInventory())
    elif (vendor == "uttermost"):
        email_subject = os.environ.get("emailsubject_inventorycountsuttermost")
        EmailClass = gmail_lib.Gmail()
        thedownloadedfilename = EmailClass.DownloadAttachement(email_subject)
        if thedownloadedfilename:
            SupplierClass = manage_uttermost_products.ManageUttermostProducts()
            SupplierClass.updateInventoryCounts(thedownloadedfilename)
            return HttpResponse("Updated inventory for Uttermost")
        else:
            return HttpResponse("Inventory counts for Uttermost is up to date.")
    elif (vendor == "foa"):
        return HttpResponse(FOA.updateInventory())
    else:
        return HttpResponse(vendor + " not recognized.")


def scrape(request, vendor, productID):
    """Scrape public content and cache it.
    """
    if (vendor == "coaster"):
        # return str(Coaster.scrape(productID))
        return HttpResponse(str(Coaster.scrape(productID)))


# @coaster.route("/updatemetadata/<vendor>")
# def updateMetaData(vendor):
#     """Updates all the meta data for a vendor.
#     """
#     if (vendor == "coaster"):
#         return "[TODO: Update meta data (Coaster)]"
#     elif (vendor == "uttermost"):
#         return "[TODO: Update meta data (Uttermost)]"
#     elif (vendor == "foa"):
#         return "[TODO: Update meta data (FOA)]"
#     else:
#         return vendor + " not recognized."


# @coaster.route("/createorder/<vendor>")
# def createOrder(vendor):
#     """Creates an order for a vendor.
#     """
#     if (vendor == "coaster"):
#         return "[TODO: Create order (Coaster)]"
#     elif (vendor == "uttermost"):
#         return "[TODO: Create order (Uttermost)]"
#     elif (vendor == "foa"):
#         return "[TODO: Create order (FOA)]"
#     else:
#         return vendor + " not recognized."


# @coaster.route("/getorders/<vendor>")
# def getOrders(vendor):
#     """Gets all orders for a vendor.
#     """
#     if (vendor == "coaster"):
#         return "[TODO: Get orders (Coaster)]"
#     elif (vendor == "uttermost"):
#         return "[TODO: Get orders (Uttermost)]"
#     elif (vendor == "foa"):
#         return "[TODO: Get orders (FOA)]"
#     else:
#         return vendor + " not recognized."
