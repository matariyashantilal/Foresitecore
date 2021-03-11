from django.urls import path

from coaster import views

urlpatterns = [
    path('scrape/update-all', views.scrape_all_product, name="scrape-update-all"),
    path('scrape/<productID>', views.scrape, name="scrape"),
    path('getsupplierinventorycounts/',
         views.get_supplier_inventory_counts, name="get-supplier-inventory-counts"),
]
