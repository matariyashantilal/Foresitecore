from django.urls import path

from shopify_module import views

urlpatterns = [
    path('addproducts/<sku_list>',
         views.addProducts, name="add-product"),
    path('products-update-all/update-all',
         views.products_update_all, name="products-update-all"),
    path('resetshopifyproducts/',
         views.reset_shopify_cache, name="resetshopifyproducts"),

]
