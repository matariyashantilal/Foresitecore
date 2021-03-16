import os

from django.http import HttpResponse

from uttermost import (import_email_from_gmail, get_uttermost_image_urls,
                       gmail_lib, manage_uttermost_products)

getuttermostimageurlsObj = get_uttermost_image_urls.GetUttermostImageUrls()
manageuttermostproductsObj = manage_uttermost_products.ManageUttermostProducts()


def cache_uttermost_images(request):
    return HttpResponse(getuttermostimageurlsObj.cache_uttermost_images_links())


def update_inventory(request):
    """Updates inventory for everything in the vendor's product list.
    """
    email_subject = os.environ.get("emailsubject_inventorycountsuttermost")
    EmailClass = gmail_lib.Gmail()

    thedownloadedfilename = EmailClass.DownloadAttachement(email_subject)
    print(thedownloadedfilename)
    if thedownloadedfilename:
        SupplierClass = manageuttermostproductsObj
        SupplierClass.updateInventoryCounts(thedownloadedfilename)
        return HttpResponse("Updated inventory for Uttermost")
    else:
        return HttpResponse("Inventory counts for Uttermost is up to date.")


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
