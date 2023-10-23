import stripe
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import JsonResponse

# from django.shortcuts import redirect
from django.urls import reverse
from django.views import generic

from .forms import ProductModelForm
from .models import Product

stripe.api_key = settings.STRIPE_SECRET_KEY


class ProductListView(generic.ListView):
    template_name = "discover.html"
    queryset = Product.objects.filter(active=True)


class ProductDetailView(generic.DetailView):
    template_name = "products/product.html"
    queryset = Product.objects.all()
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super(ProductDetailView, self).get_context_data(**kwargs)
        context.update({"STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY})
        return context


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
        return super(ProductUpdateView, self).form_valid(form)

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


class CreateCheckoutSessionView(generic.View):
    def post(self, request, *args, **kwargs):
        product = Product.objects.get(slug=self.kwargs["slug"])
        domain = "https://domain.com"  # to be used for production
        if settings.DEBUG:
            domain = "http://127.0.0.1:8000"
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": product.name,
                        },
                        "unit_amount": product.price,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=domain + reverse("success"),
            cancel_url=domain + reverse("discover"),
        )

        return JsonResponse({"id": session.id})

        # try:
        #     checkout_session = stripe.checkout.Session.create(
        #         line_items=[
        #             {
        #                 "price_data": {
        #                     "currency": "usd",
        #                     "product_data": {
        #                         "name": "T-shirt",
        #                     },
        #                     "unit_amount": 2000,
        #                 },
        #                 "quantity": 1,
        #             }
        #         ],
        #         mode="payment",
        #         success_url=domain + reverse("success"),
        #         cancel_url=domain + reverse("discover"),
        #         # automatic_tax={"enabled": True},
        #     )
        # except Exception as e:
        #     return str(e)

        # # return redirect(checkout_session.url, code=303)
        # # return reverse('create-checkout-session')
        # return JsonResponse({"id": checkout_session.id})


class SuccessView(generic.TemplateView):
    template_name = "success.html"
