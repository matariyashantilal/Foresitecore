import json
import os
import shutil
from pprint import pprint
from urllib.parse import urljoin

import requests
from django.conf import settings
from lxml import html

cat_links = [
    'https://www.uttermost.com/Accent-Furniture-View-All/',
    'https://www.uttermost.com/Mirrors-View-All/',
    'https://www.uttermost.com/Alternative-Wall-Decor-View-All/',
    'https://www.uttermost.com/Art-View-All/',
    'https://www.uttermost.com/Clocks-View-All/',
    'https://www.uttermost.com/Lamps-View-All/',
    'https://www.uttermost.com/Rugs-View-All/',
    'https://www.uttermost.com/Lighting-View-All/',
    'https://www.uttermost.com/Accessories-View-All/'
]


class GetUttermostImageUrls:

    def get_links(self, url):
        base_url = url
        r = requests.get(url)
        if r.ok:
            attr = html.fromstring(r.content)
            links = attr.xpath('//a[@class="thumbnail__nameLink"]/@href')
            yield links
            
            pageCount = attr.xpath(
                'normalize-space(string(//div[@class="gridControls__itemCount"]))')

            pageCount = pageCount.split(' ')[-1]
            pageCount = round(int(pageCount)/96)

            for i in range(1, pageCount):
                i += 1
                url = '{0}?pageNumber={1}'.format(base_url, str(i))
                r = requests.get(url)
                attr = html.fromstring(r.content)
                links = attr.xpath('//a[@class="thumbnail__nameLink"]/@href')
                yield links

    def scrape_uttermost_product_images(self, link):
        """Scrape images link of product using the product link of Uttermost.
        """
        product_url = urljoin(settings.UTTERMOST_BASE_URL, link)
        r = requests.get(product_url)
        if r.ok:
            attr = html.fromstring(r.content)
            images = attr.xpath(
                '//div[@class="product__altImageSlider flexslider"]//li[@class="slide product__altImage"]/img/@src')
            product_code = attr.xpath(
                'normalize-space(substring-after(//p[@class="product__property product__code"],"#"))')

            if images:
                return {
                    "productID": product_code,
                    "images": [l.split('?')[0]for l in images]
                }

        return {}

    def cache_uttermost_images_links(self):
        thejsonfilename = 'uttermost_images_scraped_data.json'
        
        thefulljsonpath = os.path.join(
            settings.UTTERMOST_TEMP_DIR, thejsonfilename)
        
        cached_json_file = os.path.join(
            settings.CACHE_BACKUP_DIR, thejsonfilename)
        
               
        if os.path.exists(cached_json_file):
            # Copy the cached json file in the temporary directory.
            shutil.copy(cached_json_file, settings.UTTERMOST_TEMP_DIR)
            return('Already cached in Cache Backup.')
        else:
            with open(thefulljsonpath, 'w') as f:
                data = {'products': [], 'urls': []}
           
        
                for cat_link in cat_links:
                    for links in self.get_links(cat_link):
                        for link in links:
                            if link not in data['urls']:
                                dictx = self.scrape_uttermost_product_images(
                                    link)
                             
                                if dictx:
                                    data["products"].append(dictx)
                                    data["urls"].append(link)
                json.dump(data, f, sort_keys=True, indent=4)

            shutil.copy(thefulljsonpath, settings.CACHE_BACKUP_DIR)
            return('Scraped images links of uttermost and stored in a JSON file.')
