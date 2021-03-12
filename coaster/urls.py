from django.urls import path

from coaster import views

urlpatterns = [
    path('scrape/update-all', views.scrape_all_product, name="scrape-update-all"),
    path('scrape/<productID>', views.scrape, name="scrape"),
    path('getsupplierinventorycounts/',
         views.get_supplier_inventory_counts, name="get-supplier-inventory-counts"),
    path('getproductinventorycount/<pNum>',
         views.get_product_inventory_count, name="get-product-inventory-count"),
    path('addproducts/<sku_list>',
         views.addProducts, name="add-product"),
    path('products-update-all/update-all',
         views.products_update_all, name="products-update-all"),
]
