from supplier_uttermost.lib_foresite import ImportEmailFromGmail, gmail_lib
import os

from django.http import HttpResponse

from supplier_uttermost import get_uttermost_image_urls, manage_uttermost_products

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
    if thedownloadedfilename:
        SupplierClass = manageuttermostproductsObj.ManageUttermostProducts()
        SupplierClass.updateInventoryCounts(thedownloadedfilename)
        return HttpResponse("Updated inventory for Uttermost")
    else:
        return HttpResponse("Inventory counts for Uttermost is up to date.")
