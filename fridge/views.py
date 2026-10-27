from django.shortcuts import render

TABS = [("fridge", "Fridge"), ("freezer", "Freezer"), ("pantry", "Pantry")]

ITEMS = [
    {"id": 1, "name": "Ayam", "amount": 1, "unit": "kg", "place": "freezer"},
    {"id": 2, "name": "Ikan", "amount": 3, "unit": "kg", "place": "freezer"},
    {"id": 3, "name": "Daging Sapi", "amount": 500, "unit": "g", "place": "freezer"},
    {"id": 4, "name": "Udang", "amount": 250, "unit": "g", "place": "freezer"},
    {"id": 5, "name": "Telur", "amount": 10, "unit": "pcs", "place": "fridge"},
    {"id": 6, "name": "Susu", "amount": 1, "unit": "l", "place": "fridge"},
    {"id": 7, "name": "Wortel", "amount": 500, "unit": "g", "place": "fridge"},
    {"id": 8, "name": "Tomat", "amount": 4, "unit": "pcs", "place": "fridge"},
    {"id": 9, "name": "Beras", "amount": 5, "unit": "kg", "place": "pantry"},
    {"id": 10, "name": "Gula", "amount": 1, "unit": "kg", "place": "pantry"},
    {"id": 11, "name": "Minyak Goreng", "amount": 2, "unit": "l", "place": "pantry"},
]


def show_fridge(request):
    tab = request.GET.get("tab", "fridge")
    if tab not in dict(TABS):
        tab = "fridge"
    q = request.GET.get("q", "").strip()

    items = [i for i in ITEMS if i["place"] == tab]
    if q:
        items = [i for i in items if q.lower() in i["name"].lower()]

    return render(request, "fridge/index.html", {
        "tabs": TABS,
        "tab": tab,
        "tab_label": dict(TABS)[tab],
        "q": q,
        "items": items,
    })