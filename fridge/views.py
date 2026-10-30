import json
from decimal import Decimal
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .forms import InventoryItemForm
from .models import InventoryItem

TABS = InventoryItem.Place.choices
TAB_KEYS = {key for key, _ in TABS}


def api_login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Please sign in first."}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def format_amount(value):
    return format(Decimal(value).normalize(), "f")


def serialize(item):
    return {
        "id": item.id,
        "name": item.name,
        "amount": format_amount(item.amount),
        "unit": item.unit,
        "place": item.place,
    }


MAX_ITEMS_PER_USER = 500


def read_json(request):
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def form_errors(form):
    return {field: [str(e) for e in errs] for field, errs in form.errors.items()}


def filtered_items(request):
    tab = request.GET.get("tab", "fridge")
    if tab not in TAB_KEYS:
        tab = "fridge"
    q = request.GET.get("q", "").strip()[:80]
    items = InventoryItem.objects.filter(user=request.user, place=tab)
    if q:
        items = items.filter(name__icontains=q)
    return tab, q, items


@login_required
def show_fridge(request):
    tab, q, items = filtered_items(request)
    return render(request, "fridge/index.html", {
        "tabs": TABS,
        "units": InventoryItem.Unit.choices,
        "tab": tab,
        "q": q,
        "items": [serialize(i) for i in items],
    })


@require_GET
@api_login_required
def item_list(request):
    _, _, items = filtered_items(request)
    return JsonResponse({"items": [serialize(i) for i in items]})


@require_POST
@api_login_required
def item_create(request):
    data = read_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid data."}, status=400)

    if InventoryItem.objects.filter(user=request.user).count() >= MAX_ITEMS_PER_USER:
        return JsonResponse(
            {"error": f"You can store up to {MAX_ITEMS_PER_USER} items. Delete some items first."}, status=400
        )

    form = InventoryItemForm(data, user=request.user)
    if not form.is_valid():
        return JsonResponse({"errors": form_errors(form)}, status=400)

    item = form.save(commit=False)
    item.user = request.user
    item.save()
    return JsonResponse({"item": serialize(item)}, status=201)


@require_POST
@api_login_required
def item_update(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk, user=request.user)
    data = read_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid data."}, status=400)

    form = InventoryItemForm(data, instance=item, user=request.user)
    if not form.is_valid():
        return JsonResponse({"errors": form_errors(form)}, status=400)

    form.save()
    return JsonResponse({"item": serialize(item)})


@require_POST
@api_login_required
def item_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk, user=request.user)
    item.delete()
    return JsonResponse({"deleted": pk})