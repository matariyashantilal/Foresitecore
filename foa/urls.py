from django.urls import path

from foa import views

urlpatterns = [
    path('updateinventory',
         views.FoaProduct.updateInventory, name="update-inventory-foa"),
]
