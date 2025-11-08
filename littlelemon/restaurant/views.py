from django.shortcuts import render, get_object_or_404
from .models import Menu

def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def book(request):
    return render(request, 'book.html')

def menu(request):
    items = Menu.objects.all().order_by('name')
    return render(request, 'menu.html', {'items': items})


def menu_item(request, pk):
    item = get_object_or_404(Menu, pk=pk)
    return render(request, 'menu_item.html', {'item': item})
