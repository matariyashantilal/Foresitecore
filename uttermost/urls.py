from django.urls import path

from uttermost import views

urlpatterns = [
    path('addproducts/<sku_list>',
         views.add_product, name="add-product-uttermost"),
    path('cacheUttermostImages/',
         views.cache_uttermost_images, name="cache-uttermost-images"),
    path('updateinventory',
         views.update_inventory, name="update-inventory-uttermost"),

]
