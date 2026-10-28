from django.shortcuts import render

def show_discovery(request):
    return render(request, "discovery/index.html", {'placeholder_range': range(5)})

def show_recipe_detail(request, recipe_id):
    # TODO: Fetch idnya dari API
    return render(request, "discovery/recipe_detail.html", {'recipe_id': recipe_id})
