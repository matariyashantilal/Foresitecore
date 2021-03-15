import json
import logging
import os
import sys
import tempfile

import excel2json
import pandas as pd
import requests
from django.conf import settings
from lxml import html

from uttermost import (get_uttermost_image_urls,
                                manage_uttermost_products)
from uttermost import views as shopify

getuttermostimageurlsObj = get_uttermost_image_urls.GetUttermostImageUrls()

file_handler = logging.FileHandler(filename='uttermost.log')
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger('LOGGER_NAME')


class ManageUttermostProducts:

    def updateInventoryCounts(self, fileName):
        fileExtension = fileName.split(".")[1]
        if fileExtension == "xls" or fileExtension == "xlsx" or fileExtension == "XLS" or fileExtension == "XLSX":
            attachment_dir = tempfile.gettempdir()
            filePath = os.path.join(attachment_dir, fileName)
            excel2json.convert_from_file(filePath)
            if os.path.exists(attachment_dir+"/Uttermost Item Availability.json"):
                os.remove(filePath)
                # logger.info("Get shopify products")
                sps = shopify.ShopifyProducts()

                AvailabilityProduct = {}
                with open(attachment_dir+"/Uttermost Item Availability.json") as file_handle:
                    AvailabilityProduct = json.load(file_handle)

                tempAvailabilityProductSKU = []
                tempAvailabilityProductSKUList = dict()

                for p in AvailabilityProduct:
                    tempAvailabilityProductSKU.append(p["SKU"])
                    # This will need some custom logic to get the ETA.
                    # Did India already implement the custom action?
                    tempAvailabilityProductSKUList[p["SKU"]
                                                   ] = p["EC Qty"] + p["WC Qty"]
                    # shopify_helper_new.updateInventoryCount()
                sps.uploadProduct(tempAvailabilityProductSKU,
                                  tempAvailabilityProductSKUList)
                # logger.info("Products has been updated successfully on shopify.")
            else:
                os.remove(filePath)
                # logger.info("Json has not created.")

    def updateShopifyForAllCatalogs(self):
        """Updates the shopify for all the catalogs (Uttermost, Whitelist, Overstock).
        """
        # Uttermost file
        self.loadUttermostCatalog(os.environ.get(
            "UTERMOST_CATALOG"), "Uttermost")

        # Whitelist file
        self.loadUttermostCatalog(os.environ.get(
            "WHITELIST_CATALOG"), "Red Rock Furiture Outlet")

        # Oversock file
        self.loadUttermostCatalog(os.environ.get(
            "OVERSTOCK_CATALOG"), "Uttermost")

        return "Update: Success"

    def scrape_images_for_product(self, productID, newJsonObj):
        r = requests.get(settings.UTTERMOST_SEARCH_URL.format(productID))
        if r.ok:
            uttr = html.fromstring(r.content)
            url = uttr.xpath('//a[@class="thumbnail__imageLink"]/@href')
            if url:
                url = '%s%s' % (settings.UTTERMOST_BASE_URL, url[0])
                dictx = getuttermostimageurlsObj.scrape_uttermost_product_images(
                    str(url))
                if dictx:
                    newJsonObj["Images"] = dictx["images"]

    def loadUttermostCatalog(self, catalogfile, vendor):
        """
        Get the Overstock catalog: UttermostSampleSet/Uttermost Summer 20/Overstock/Overstock.xlsx

        Get the white label catalog: UttermostSampleSet/White Label/White Label Price List.xlsx

        Example excel file:
        'Item Number':'01018 B'
        'Marketing Description':'This Solid Wood Frame Features A Black Finish With Heavy Distressing. Mirror Is Beveled. May Be Hung Either Horizontal Or Vertical.'
        'UPC Number':'792977010181'
        'Product Name':'Uttermost Palmer Dark Wood Mirror'
        'Collection':'Palmer'
        'Minimum Order':'1'
        'Wholesale Price':'$261.00'
        'Drop Ship Fee':'$15.00'
        'Lamp Prepack Fee':'$0.00'
        'Total Utt. Price':'$276.00'
        'MAP':'$574.20'
        'Voltage':''
        'Material':'Wood'
        'Overall Depth':'3'
        'Overall Width':'40'
        'Overall Height':'70'
        'Mirror/Glass Depth':'0.187'
        'Mirror/Glass Width':'30'
        'Mirror/Glass Height':'60'
        'Shipping Weight':'72'
        'Product Weight':'57.2'
        'Diameter':''
        'Ship Method':'LOOSE'
        'Box Size':'44.9 L x 5.7 W x 74.9 T'
        'Unit of Measure':'inches'
        'Shipping Class':'Motor Freight'
        'Finish/Frame Description':'Heavily Distressed Black Stain.'
        'Chain Finish':''
        '# of Lights':''
        'Shade Description':''
        'Shade Size':''
        'Wattage':''
        'Bulb Qty':''
        'Bulb Type':''
        'Socket Type':''
        'Disclaimer':''
        'Chain specification':''
        'Country of Orgin':'China'
        'Designer':'NA'
        'Category':'Mirrors'
        'SubCategory':'Large Rectangular Mirrors'
        'Product Attribute 1':"Uttermost's Mirrors Combine Premium Quality Materials With Unique High-style Design."
        'Product Attribute 2':'With The Advanced Product Engineering And Packaging Reinforcement, Uttermost Maintains Some Of The Lowest Damage Rates In The Industry.  Each Product Is Designed, Manufactured And Packaged With Shipping In Mind. '

        'Related Items':''
        'CA Prop 65 Chemical':'TITANIUM DIOXIDE'
        'CA Prop 65 Chemical Warning':'WARNING: This product can expose you to chemicals including titanium dioxide which is known to the State of California to cause cancer. For more information, go to www.P65Warnings.ca.gov/furniture.'
        'Fabric Content':''
        'Cleaning Code':''
        'Cubes':'11.09'
        """
        # Reads the excel file
        df = pd.read_excel(catalogfile)
        result = df.to_json(orient="records")
        rows = json.loads(result)
        
        
        for row in rows:
            body_html = ''.join((
                row["Marketing Description"],
                "<p><br><b>Dimensions:</b> " + str(row["Overall Width"]) + " W X " + str(row["Overall Height"]) + " H X " + str(
                    row["Overall Depth"]) + " D (" + str(row["Unit of Measure"]) + ")",
                "<br><b>Weight:</b> " + str(row["Product Weight"]), "</p>"))
            try:
                map_value = row["MAP"]
            except:
                map_value = int(row["Promo Price"]) * 2

            SubCategory_test = ''
            try:
                SubCategory_test = row['SubCategory']
            except:
                pass

            newJsonObj = {
                "ProductNumber": str(row["Item Number"]),
                "MAP": map_value,
                "product_type": row['Category'],
                "RRFO_PRICE": 0,
                "Name": row["Product Name"],
                "Vendor": vendor,
                "Description": body_html,
                "Tags": row['Category'] + ',' + SubCategory_test,
            }
            thejsonfilename = 'uttermost_images_scraped_data.json'
            thefulljsonpath = os.path.join(
                settings.UTTERMOST_TEMP_DIR, thejsonfilename)
          
            print("thefulljsonpath",thefulljsonpath)
            if os.path.exists(thefulljsonpath):
                with open(thefulljsonpath) as f:
                    data = json.load(f)
                    counter = 0
                    products = data['products']
                    for product in products:
                        if product["productID"] == str(row["Item Number"]):
                            break
                        counter += 1
                    if counter != len(products) - 1:
                        newJsonObj['Images'] = products[counter]['images']
                    else:
                        self.scrape_images_for_product(
                            str(row["Item Number"]), newJsonObj)
            else:
                self.scrape_images_for_product(
                    str(row["Item Number"]), newJsonObj)
            shopify.upsertShopifyProduct(
                newJsonObj, bUpdateImages=True)

        return rows
