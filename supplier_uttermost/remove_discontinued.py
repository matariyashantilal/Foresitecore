import json
import os

import shopify
import shopify_helper_new
import xlrd


class removeproducts:
    shopify.ShopifyResource.set_site(os.environ.get("SHOPIFY_SECUREURL"))

    def test(self):
        return "hello uttermost remove"

    def get_item_numbers(self, file_of_discontinued):
        # loop through all shopify products
        # remove the product if is is discontinued and 0 inventory
        # remove the product if it is a box

        loc = os.environ.get("DISCONTINUED_PRODUCTS")
        wb = xlrd.open_workbook(loc)
        sheet = wb.sheet_by_index(0)
        counter = 0

        ''' Find Item Number from Excel'''

        ''' Finds what col Item Number is on" '''
        for x in range(sheet.ncols):
            name = str(sheet.cell_value(0, x))
            if name == 'Item Number':
                item_number_col = x
                break

        data = []
        ''' gets item numbers from "Item Number collumn'''
        for x in range(sheet.nrows):
            data.append(str(sheet.cell_value(x, item_number_col)))

        ''' Gets SKU from Shopify '''
        sps = shopify_helper_new.ShopifyProducts()

        ''' Object of each item from shopify, [our_SKU, shopify_SKU]. Saved as dictionary'''
        oProduct = sps.dProductMapBySupplierSKU

        ''' Makes list of our SKU'''
        SKU_shopify = []
        for key in oProduct.keys():
            SKU_shopify.append(key)

        ''' List of duplicates '''
        list_of_doubles = []
        for element in data:
            if element in SKU_shopify:
                list_of_doubles.append(element)

        '''Get Shopify SKU for Items in duplicate list'''
        for item in list_of_doubles:
            #print(item, oProduct[item])
            temp = str(oProduct[item])
            print(temp)
            product_ID = int(temp[8:-1])
            shopify.Product.delete(product_ID)
            print(f"DELETED {product_ID}")

    get_item_numbers('DISCONTINUED_PRODUCTS')
