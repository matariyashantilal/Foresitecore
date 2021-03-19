from django.urls import path

from uttermost import views

urlpatterns = [
    path('cacheUttermostImages/',
         views.cache_uttermost_images, name="cache-uttermost-images"),
    path('updateinventory/',
         views.update_inventory, name="update-inventory-uttermost"),
    path('addproduct/update-all/',
         views.add_product, name="add-product-uttermost"),

]
