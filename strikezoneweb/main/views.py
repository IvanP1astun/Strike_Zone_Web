from django.shortcuts import render


def index(request):
    return render(request, 'main/index.html')


def rules(request):
    return render(request, 'main/rules.html')


def about(request):
    return render(request, 'main/about.html')


def catalog(request):
    return render(request, 'catalog/catalog.html')


def profile(request):
    return render(request, 'profile/profile.html')
