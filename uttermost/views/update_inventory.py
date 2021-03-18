import os

from django.http import HttpResponse
from . import gmail_lib, manage_uttermost_products

manageuttermostproductsObj = manage_uttermost_products.ManageUttermostProducts()


def update_inventory(request):
    """Updates inventory for everything in the vendor's product list.
    """
    email_subject = os.environ.get("emailsubject_inventorycountsuttermost")
    EmailClass = gmail_lib.Gmail()

    thedownloadedfilename = EmailClass.DownloadAttachement(email_subject)

    if thedownloadedfilename:
        SupplierClass = manageuttermostproductsObj
        SupplierClass.updateInventoryCounts(thedownloadedfilename)
        return HttpResponse("Updated inventory for Uttermost")
    else:
        return HttpResponse("Inventory counts for Uttermost is up to date.")
