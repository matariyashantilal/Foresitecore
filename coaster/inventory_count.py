import json
import os

from django.conf import settings


class InventoryCount:
    """Count inventory item
    """
    dInventoryCount = {}
    dTheMap = {}
    thefilename = "inventory_coaster.json"

    def getInventoryCount(self, productnumber):
        try:
            # TODO loop through each warehouse and add the counts together
            return self.dTheMap[productnumber]
        except:
            return 0

    def __init__(self):
        inventory_coaster_json_path = os.path.join(
            settings.COASTER_DIRECTORY_PATH, self.thefilename)

        if not os.path.exists(inventory_coaster_json_path):
            os.mknod(inventory_coaster_json_path)
        with open(inventory_coaster_json_path) as file_handle:
            jInventory = json.load(file_handle)

        # TODO create the map for each warehouse location
        # TODO read the inventory count from shopify for the Hurricane warehouse
        # The current code combines the inventory count from both warehouses
        for i in jInventory[0]["InventoryList"]:
            self.dTheMap[i['ProductNumber']] = int(i['QtyAvail'])
        # TODO fix this to handle a dynamic number of locations
        for i in jInventory[1]["InventoryList"]:
            self.dTheMap[i['ProductNumber']] += int(i['QtyAvail'])
