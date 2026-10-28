from django.shortcuts import render
from comments.views import comment_section_context

def show_discovery(request):
    return render(request, "discovery/index.html", {'placeholder_range': range(5)})

def show_recipe_detail(request, recipe_id):
    # TODO: Fetch idnya dari API
    context = {'recipe_id': recipe_id}
    context.update(comment_section_context(request, recipe_id))
    return render(request, "discovery/recipe_detail.html", context)
