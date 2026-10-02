from django.shortcuts import render

def show_discovery(request):
    return render(request, "discovery/index.html")