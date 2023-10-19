from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views import generic

from .forms import ProductModelForm
from .models import Product


class ProductListView(generic.ListView):
    template_name = "discover.html"
    queryset = Product.objects.all()


class ProductDetailView(generic.DetailView):
    template_name = "products/product.html"
    queryset = Product.objects.all()


class UserProductListView(LoginRequiredMixin, generic.ListView):
    # shoes the users, created products
    template_name = "products.html"

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)


class ProductCreateView(LoginRequiredMixin, generic.CreateView):
    template_name = "products/product_create.html"
    form_class = ProductModelForm

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.user = self.request.user
        instance.save()
        self.product = instance
        return super(ProductCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse("products:product-detail", kwargs={"slug": self.product.slug})


class ProductUpdateView(LoginRequiredMixin, generic.UpdateView):
    template_name = "products/product_update.html"
    form_class = ProductModelForm

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.user = self.request.user
        instance.save()
        return super(ProductCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse(
            "products:product-detail", kwargs={"slug": self.get_object().slug}
        )


class ProductDeleteView(LoginRequiredMixin, generic.UpdateView):
    template_name = "products/product_delete.html"
    form_class = ProductModelForm

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse("products:user-products")
