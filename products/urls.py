from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.products, name='products'),
    path('cart', views.cart, name='cart'),
    path('cart/', views.cart),
    path('cart/clear', views.cart_clear, name='cart_clear'),
    path('cart/toggle/<int:product_id>', views.cart_toggle, name='cart_toggle'),
    path('checkout', views.checkout, name='checkout'),
    path('checkout/', views.checkout),
    path('<slug:product_slug>', views.product, name='product'),
]
