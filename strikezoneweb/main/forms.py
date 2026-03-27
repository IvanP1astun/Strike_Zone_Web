from django import forms
from .models import News


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ['title', 'content', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Заголовок'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Текст новости...'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
