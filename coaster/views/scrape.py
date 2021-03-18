import logging
import os

from coaster.views import api, inventory_count, scraper
from django.conf import settings
from django.http import HttpResponse
from shopify_wrapper import views as shopify
from shopify_wrapper.views import productObj


# scraper class object
scrapeObj = scraper.Scraper()


def scrape(request, productID):
    """Scrape product based on productID.
    """
    scrapedata = scrapeObj.scrape(productID)
    return HttpResponse("Scraped:"+productID)
