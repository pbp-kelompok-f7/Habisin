from django.shortcuts import render

def show_bookmarks(request):
    return render(request, "bookmarks/index.html", {'placeholder_range': range(5)})