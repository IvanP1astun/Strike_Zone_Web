from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy


from .models import News, Catalog
from .forms import NewsForm


def home(request):
    """Главная страница с новостями."""
    news_list = News.objects.filter(is_published=True)[:10]
    return render(request, 'main/index.html', {'news_list': news_list})


class NewsListView(ListView):
    """Список последних 10-и новостей."""
    model = News
    template_name = 'main/index.html'
    context_object_name = 'news_list'
    paginate_by = 10

    def get_queryset(self):
        return News.objects.filter(is_published=True)


class NewsCreateView(CreateView):
    """Создание новой новости. Доступно только для админов и модераторов."""
    model = News
    form_class = NewsForm
    template_name = 'main/news_form.html'
    success_url = reverse_lazy('home')

    def dispatch(self, request, *args, **kwargs):
        """Проверка: только админы и модераторы"""
        if not (request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name='moderators').exists()):
            return render(request, 'main/403.html', status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Автоматически устанавливаем автора новости."""
        form.instance.author = self.request.user
        return super().form_valid(form)


def post(request):
    return render(request, 'main/post.html')


def rules(request):
    return render(request, 'main/rules.html')


def about(request):
    return render(request, 'main/about.html')


def catalog(request):
    """Страница со списком каталогов"""
    catalogs = Catalog.objects.all()
    return render(request, 'catalog/catalog.html', {'catalogs': catalogs})


def catalog_detail(request, pk):
    """Детальная страница каталога"""
    catalog = get_object_or_404(Catalog, pk=pk)
    return render(request, 'catalog/catalog_detail.html', {'catalog': catalog})


def profile(request):
    return render(request, 'profile/profile.html')
