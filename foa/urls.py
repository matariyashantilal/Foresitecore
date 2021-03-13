from django.urls import path

from foa import views

urlpatterns = [
    path('updateinventory',
         views.FoaProduct.updateInventory, name="update-inventory-foa"),
    path('addproducts/<sku_list>',
         views.add_product, name="add-product-foa"),
]
