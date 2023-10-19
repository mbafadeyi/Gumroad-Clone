from django.urls import path
from products import views

app_name = "products"
urlpatterns = [
    path("<slug>/", views.ProductDetailView.as_view(), name="product-detail"),
]
