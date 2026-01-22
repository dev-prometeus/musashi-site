from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.shortcuts import redirect
from django.template.loader import render_to_string
from .models import Product, Category
from .cart import Cart

import json


@require_http_methods(['GET', 'POST'])
def products(request):
    is_htmx_request = request.headers.get('HX-Request')
    page_number = request.GET.get('page', 1)  # 1 by default

    products_qs = Product.objects.all()
    per_page = 10

    # retrieve selected category IDs
    selected_category_ids = request.GET.getlist('category')

    if selected_category_ids:
        products_qs = products_qs.filter(
            categories__id__in=selected_category_ids).distinct()
        # if filters change, reset
        if not is_htmx_request:
            page_number = 1

    products_qs = products_qs.order_by('-date_modified')

    # paginator logic
    paginator = Paginator(products_qs, per_page)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        # if page is not an int, return first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # if HTMX request and page number is out of range, return empty content
        if is_htmx_request:
            return HttpResponse("")
        # if standard browser request, return last page
        page_obj = paginator.page(paginator.num_pages)

    # fetch all categories for filter menu
    categories = Category.objects.all().order_by('name')

    cart = Cart(request)

    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'is_htmx_request': is_htmx_request,
        'categories': categories,
        'selected_categories': selected_category_ids,
        'cart': cart,
    }

    # If the request comes from HTMX, return only the product grid HTML.
    if is_htmx_request:
        template = 'partials/_products_list.html'
    else:
        template = 'pages/products.html'

    # If the request is a standard browser load, return the full page
    return render(request, template, context)


@require_http_methods(['GET'])
def product(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)

    cart = Cart(request)

    context = {
        'product': product,
        'cart': cart,
    }

    return render(request, 'pages/product.html', context)


@require_http_methods(['GET'])
def cart(request):
    cart = Cart(request)
    context = {
        'cart': cart,
        'cart_lines': cart.lines(),
        'cart_subtotal': cart.subtotal(),
    }
    return render(request, 'pages/cart.html', context)


@require_http_methods(['GET', 'POST'])
def checkout(request):
    cart = Cart(request)
    context = {
        'cart': cart,
        'cart_lines': cart.lines(),
        'cart_subtotal': cart.subtotal(),
    }
    return render(request, 'pages/checkout.html', context)


@require_http_methods(['POST'])
def cart_clear(request):
    cart = Cart(request)
    cart.clear()

    next_url = request.GET.get('next') or request.POST.get('next') or request.META.get('HTTP_REFERER') or '/products/'
    return redirect(next_url)


@require_http_methods(['POST'])
def cart_toggle(request, product_id: int):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    now_in_cart = cart.toggle(product.id)
    message = f"Added {product.name} to cart" if now_in_cart else f"Removed {product.name} from cart"

    next_url = request.GET.get('next') or request.POST.get('next')
    is_htmx = request.headers.get('HX-Request')

    if not is_htmx:
        return redirect(next_url or product.get_absolute_url())

    button_html = render_to_string('partials/_cart_toggle_button.html', {
        'product': product,
        'cart': cart,
    }, request=request)

    count_html = render_to_string('partials/_cart_count.html', {
        'cart': cart,
    }, request=request)

    html = button_html + count_html
    response = HttpResponse(html)
    response['HX-Trigger'] = json.dumps({'toast': {'message': message}})
    return response