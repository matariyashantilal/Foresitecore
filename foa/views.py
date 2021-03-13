import os

from django.http import HttpResponse
from django.shortcuts import render
from shopify_wrapper import views as shopify
from zeep import Client

# Routes that need to be supported:
# X addproducts -> adds product(s) (or a list of products?) to Shopify
# X removeproducts -> removes product(s) from Shopify
# updateprices -> for every item listed
# - updateinventory -> for every item listed
# updatemetadata -> for every item listed
# createorder -> there's nothing in the API to support this (maybe customer.info?)
# getorders -> also has nothing in the API


user = os.environ.get("FOA_USER")
key = os.environ.get("FOA_API_KEY")
client = Client("https://www.foagroup.com/api/v2_soap/?wsdl")
product_file = "./foa/products.txt"


# API Documentation (with examples in PHP): https://www.foagroup.com/help.php

# Adds 1 or more (new, unique) products to products.txt and Shopify


class FoaProduct:

    def add(self, sku_list):
        return_text = ""
        for sku in sku_list:
            try:
                # Make sure the SKU doesn't already exist in products.txt
                with open(product_file, 'r+') as file:
                    for line in file:
                        if line[0:len(sku)+1] == sku + "\t":
                            #raise Exception("Duplicate product")
                            donothing = ""

                session = client.service.login(username=user, apiKey=key)
                # $attributes = (object)array('additional_attributes' => array('priority', 'eta'));
                # $result = $proxy->catalogProductInfo($sessionId,'SM6072-LV', null, $attributes);
                result = client.service.catalogProductInfo(session, sku, storeView="", attributes={
                    'priority', 'eta'}, identifierType="sku")
                images = client.service.catalogProductAttributeMediaList(
                    session, sku, storeView="", identifierType="sku")
                # Add the product to Shopify
                product = {"ProductNumber": result["sku"],
                           "Name": result["meta_title"][23:],
                           "Vendor": "Furniture of America",
                           "Description": result["short_description"],
                           "MAP": result["price"],
                           "Tags": "",
                           "Images": []}
                for image in images:
                    product["Images"].append(image["url"])
                id = shopify.addProduct(product)
                if id == -1:
                    raise Exception("Shopify error")

                # Append the SKU and the shopify product ID to products.txt
                with open(product_file, 'a') as file:
                    file.write(sku + '\t' + str(id) + '\n')

                return_text += "Added FOA product " + sku + "<br>"
            except Exception as e:
                return_text += "Failed to add FOA product " + \
                    sku + ": " + str(e) + "<br>"

    # Remove this SKU from products.txt, then use the corresponding Shopify product id to remove it from Shopify

    def remove(self, sku_list):
        return_text = ""
        for sku in sku_list:
            try:
                success = False
                with open(product_file, "r") as file:
                    lines = file.readlines()
                with open(product_file, "w") as file:
                    for line in lines:
                        if line[0:len(sku)+1] != sku + "\t":
                            file.write(line)
                        else:
                            # If this is the correct line, grab the product id and use it to remove the product from Shopify
                            shopify_id = line.strip("\n").split("\t")
                            shopify_id = shopify_id[1]
                            success = True
                if not success:
                    raise Exception("SKU not found in products.txt")

                # Delete the product from Shopify
                shopify.deleteProduct(shopify_id)
                return_text += "Removed FOA product " + sku + "<br>"
            except Exception as e:
                return_text += "Failed to remove FOA product " + \
                    sku + ": " + str(e) + "<br>"
        return return_text

    # Updates the inventory for everything in products.txt

    def updateInventory(self):
        # 1. Read in products.txt, separating SKU's and product ID's into 2 lists
        with open(product_file, "r") as file:
            lines = file.readlines()
        sku_list = []
        product_list = []
        for line in lines:
            pair = line.strip("\n").split("\t")
            sku_list.append(pair[0])
            product_list.append(pair[1])
        # 2. Call the FOA api to get an array of inventory objects
        session = client.service.login(username=user, apiKey=key)
        result = client.service.catalogInventoryStockItemList(
            session, products=sku_list)
        # $result = $proxy->catalogInventoryStockItemList($sessionId, array('1', '2'));
        client.service.endSession(session)
        # 3. Call the Shopify api to update inventory for each FOA product
        for index, shopify_id in enumerate(product_list):
            shopify.updateInventory(
                shopify_id, result[index]["qty"])
        return HttpResponse("FOA inventory updated (" + result.count() + " products)")

    # To make an API call, use this format:
    # result = client.service.[command name](session, [args])
    # optional parameters are actually mandatory, but can be left as blank strings/empty arrays
    # if there's an "identifierType" parameter, the product/productId parameter is a product_id by default and a SKU if identifierType="sku"

    # Example API usage:

    # Pull the full product list and write it to a file
    # result = client.service.catalogProductList(session, filters={}, storeView="")
    # with open('Products.txt', 'w') as f:
    #    for item in result:
    #        f.write("%s\n" % item)

    # Pull the data for a single product (title, description, price, etc).
    #result = client.service.catalogProductInfo(session, productId="159", storeView="", attributes={}, identifierType="")
    #result = client.service.catalogProductInfo(session, productId="CM3185DG-HB", storeView="", attributes={}, identifierType="SKU")

    # Grab inventory for an array of product IDs - works with the product ID or the SKU, don't need to specify which
    # result = client.service.catalogInventoryStockItemList(session, products={"CM7295CK-BED", "162", "175"})

    # Grab images for a product. Returns an array of objects where result[0]["url"] is the URL for the first image
    #result = client.service.catalogProductAttributeMediaList(session, product="159", storeView="", identifierType="")
    #x = result[0]["url"]
    # updateInventory()


def add_product(request, sku_list):
    """Adds 1 or more comma delimited products from the vendor's product list and Shopify.
    """
    try:
        result = ""
        sku_list = sku_list.split(",")
        result = FoaProduct().add(sku_list)
        if result == None:
            result = "Update return string for this vendor!!"
        return HttpResponse(result)
    except Exception as e:
        return HttpResponse("Failed to add Coaster products: " + str(e))
