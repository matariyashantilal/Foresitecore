from django.urls import path
from django.views.generic import TemplateView

from coasterapp import views

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html')),
    
    path('scrape/<vendor>/<productID>', views.scrape, name="scrape"),

    path('getsupplierinventorycounts/<vendor>',
         views.getSupplierInventoryCounts, name="get-supplier-inventory-counts"),
    path('addproducts/<vendor>/<sku_list>',
         views.addProducts, name="add-products"),
    path('cacheuttermostimages/',
         views.cacheUttermostImages, name="cache-uttermost-images"),
    path('updateinventory/<vendor>/',
         views.updateInventory, name="update-inventory"),
    path('getproductinventorycount/<vendor>/<pNum>',
         views.getProductInventoryCount, name="get-product-inventory-count"),
    path('resetshopifyproducts/',
         views.resetShopifyCache, name="reset-shopify-products"),
    path('updateprices/<vendor>',
         views.updatePrices, name="update-prices"),
]
