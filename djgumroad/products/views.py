import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from stripe.error import SignatureVerificationError

from .forms import ProductModelForm
from .models import Product, PurchasedProduct

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()


class ProductListView(generic.ListView):
    template_name = "discover.html"
    queryset = Product.objects.filter(active=True)


class ProductDetailView(generic.DetailView):
    template_name = "products/product.html"
    queryset = Product.objects.all()
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super(ProductDetailView, self).get_context_data(**kwargs)
        product = self.get_object()
        has_access = False
        if self.request.user.is_authenticated:
            if product in self.request.user.userlibrary.products.all():
                has_access = True
        context.update(
            {"STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY, "has_access": has_access}
        )
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

        customer = None
        customer_email = None
        if request.user.is_authenticated:
            if request.user.stripe_customer_id:
                customer = request.user.stripe_customer_id
            else:
                customer_email = request.user.email
        product_image_urls = []
        if product.cover:
            product_image_urls.append(product.cover.url)
        session = stripe.checkout.Session.create(
            customer=customer,
            customer_email=customer_email,
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": product.name,
                            # "images": product_image_urls,
                        },
                        "unit_amount": product.price,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=domain + reverse("success"),
            cancel_url=domain + reverse("discover"),
            metadata={"product_id": product.id},
        )

        return JsonResponse({"id": session.id})


class SuccessView(generic.TemplateView):
    template_name = "success.html"


@csrf_exempt
def stripe_webhook(request, *args, **kwargs):
    CHECKOUT_SESSION_COMPLETED = "checkout.session.completed"
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as e:
        print(e)
        return HttpResponse(status=400)
    except SignatureVerificationError as e:
        print(e)
        return HttpResponse(status=400)

    # listen for successful payments
    if event["type"] == CHECKOUT_SESSION_COMPLETED:
        print(event)

        product_id = event["data"]["object"]["metadata"]["product_id"]
        product = Product.objects.get(id=product_id)

        stripe_customer_id = event["data"]["object"]["customer"]  # Fix this issue
        try:
            user = User.objects.get(stripe_customer_id=stripe_customer_id)
            user.userlibrary.products.add(product)
            # give access to this product
        except User.DoesNotExist:
            # assign the customer_id to the corresponding user
            stripe_customer_email = event["data"]["object"]["customer_details"]["email"]

            try:
                user = User.objects.get(email=stripe_customer_email)
                user.stripe_customer_id = stripe_customer_id
                user.save()
                user.userlibrary.products.add(product)
            except User.DoesNotExist:
                PurchasedProduct.objects.create(
                    email=stripe_customer_email,
                    product=product,
                )

                # send an email and ask them to create an account
                send_mail(
                    subject="Create an account to access your content",
                    message="Please signup to access your latest purchase",
                    recipient_list=[stripe_customer_email],
                    from_email="test@test.com",
                )

                # this was an anonymous checkout
                # TODO: handle anonymous checkout
                print("User does not exist")
                pass
            # give access to this product

    # who paid for what?

    # give access to the user for the product they purchased

    return HttpResponse()
