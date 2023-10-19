from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic

from .models import Product


class ProductListView(generic.ListView):
    template_name = "discover.html"
    queryset = Product.objects.all()


class ProductDetailView(generic.DetailView):
    template_name = "products/product.html"
    queryset = Product.objects.all()


class UserProductListView(LoginRequiredMixin, generic.ListView):
    # shoes the users, created products
    template_name = "discover.html"

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)
