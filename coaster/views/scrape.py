from coaster.views import scraper
from django.http import HttpResponse

# scraper class object
scrapeObj = scraper.Scraper()


def scrape(request, productID):
    """Scrape product based on productID.
    """
    scrapedata = scrapeObj.scrape(productID)
    return HttpResponse("Scraped:"+productID)
