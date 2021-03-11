import json
import logging
import os

import requests
from django.conf import settings
from lxml import html

# from settings import COASTER_SEARCH_URL, COASTER_TEMP_DIR, TEMP_DIR


class Scraper:
    """Scarper class which defines all the utility methods which helps us to scrape the data from the Coaster.
    """
    count_success = 0
    count_skipped = 0
    count_used_cache = 0
    count_scraped = 0
    count_total = 0

    def __init__(self):
        skipped_count = 0

    def resetcounts(self):
        count_success = 0
        count_skipped = 0
        count_used_cache = 0
        count_scraped = 0
        count_total = 0

    def nextGen(self, data) -> [str]:
        """Takes a product (JSON dictionary) and returns a list of nextgen image URLs"""
        images = []
        try:
            if data["NumNextGenImages"] == 0:
                logging.info("There are no nextgen images for:" +
                             data["ProductNumber"])
                return
            for imagePath in data["ListNextGenImages"].split(","):
                images.append(
                    "https://assets.coastercenter.com/nextgenimages/"+imagePath)
            return images
        except Exception as e:
            logging.error("Error loading nextgen images for:" +
                          data["ProductNumber"])
            logging.error(e)

    def scrape(self, pNum):
        thejsonfilename = "coaster_scrape_" + pNum + ".json"
        thefulljsonpath = os.path.join(
            settings.COASTER_TEMP_DIR, thejsonfilename)
        try:
            self.count_total += 1

            if pNum.endswith('B1') or pNum.endswith('B2') or pNum.endswith('B3'):
                p = {}
                self.count_skipped += 1
            elif not os.path.exists(thefulljsonpath):
                r = requests.get(settings.COASTER_SEARCH_URL.format(pNum))
                if not r.ok:
                    raise Exception(
                        'Invalid response code from server: '.format(r.status_code))
                uttr = html.fromstring(r.content)
                url = uttr.xpath('//a[@class="product-img-thumb"]/@href')
                if len(url) > 0:
                    p = self.parse(url[0], pNum)
                    self.count_scraped += 1
                else:
                    with open(thefulljsonpath, 'w+') as outfile2:
                        json.dump({}, outfile2)
                    p = {}
                    self.count_skipped += 1
            else:
                with open(thefulljsonpath) as outfile2:
                    p = json.load(outfile2)
                    self.count_used_cache += 1
            return p

        except Exception as e:
            with open(thefulljsonpath, 'w+') as outfile2:
                json.dump({}, outfile2)
            # drop a json file for this part number so we don't try again
            logging.error(
                "Failed to download public images for product " + pNum)
            logging.error(e)

    def parse(self, url, pNum):
        """It'll be used to grab dimensions and other data from the product page
        """
        r = requests.get(url)
        if r.ok:
            attr = html.fromstring(r.content)
            item = {}
            item["Title"] = attr.xpath(
                'normalize-space(string(//h1[@class="h2 mb-1"]))')
            item["SKU"] = attr.xpath(
                'normalize-space(substring-after(//li[contains(text(),"SKU:")],"SKU: "))')
            item["Url"] = url
            item["Breadcrumb"] = attr.xpath(
                '//div[@class="col-12 small"]/a/text()')
            item["Description"] = attr.xpath(
                'normalize-space(string(//p[@id="product-description"]))')
            item["Features"] = [x.strip() for x in attr.xpath(
                '//div[@id="product-features"]//li/text()') if x]
            item["Dimensions_Weight"] = list(filter(
                None, [x.strip() for x in attr.xpath('//div[@id="dimensions"]//ul//text()') if x]))
            item["Collection"] = attr.xpath(
                'normalize-space(substring-after(//li[contains(text(),"Collection:")],"Collection: "))')
            item["Brand"] = attr.xpath(
                'normalize-space(string(//h2[@class="h6 sub-h"]))')
            item["Images"] = attr.xpath(
                '//div[@id="product-gallery-thumbs"]//a/@href')

            # Save the json to a file
            thejsonfilename = "coaster_scrape_" + pNum + ".json"
            with open(os.path.join(settings.COASTER_TEMP_DIR, thejsonfilename), 'w+') as outfile2:
                json.dump(item, outfile2)
            return item
        else:
            raise Exception(
                'Invalid response code from server: '.format(r.status_code))
