from django.urls import path

from shopify_wrapper import views

urlpatterns = [
    path('addproducts/<sku_list>',
         views.add_product, name="add-product-coaster"),
    path('products/update-all',
         views.products_update_all, name="products-update-all"),
    path('resetshopifyproducts/',
         views.reset_shopify_cache, name="reset-shopify-products"),

]
