from django.urls import path

from supplier_uttermost import views

urlpatterns = [
    path('cacheUttermostImages/',
         views.cache_uttermost_images, name="cache-uttermost-images"),
    path('updateinventory',
         views.update_inventory, name="update-inventory-uttermost"),
    path('addproducts/<sku_list>',
         views.add_product, name="add-product-uttermost"),
]
