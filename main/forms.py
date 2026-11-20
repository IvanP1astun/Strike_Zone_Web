from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import GameRegistration, News, Profile, AirsoftGame

User = get_user_model()


class NewsForm(forms.ModelForm):
    """Форма для создания новости"""

    class Meta:
        model = News
        fields = ["title", "content", "image", "is_published"]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Заголовок новости')
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': _('Текст новости...')
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'title': _('Заголовок'),
            'content': _('Содержание'),
            'image': _('Изображение (необязательно)'),
            'is_published': _('Опубликовать'),
        }


class GameCreateForm(forms.ModelForm):
    """Форма создания игры (только для командиров)"""

    class Meta:
        model = AirsoftGame
        fields = [
            'name',
            'date',
            'description',
            'location',
            'price',
            'max_players',
            'image',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Название игры')
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Описание игры...')
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Место проведения')
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Стоимость участия')
            }),
            'max_players': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Максимум игроков')
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'name': _('Название игры'),
            'date': _('Дата проведения'),
            'description': _('Описание'),
            'location': _('Место проведения'),
            'price': _('Стоимость участия (₽)'),
            'max_players': _('Максимум игроков'),
            'image': _('Изображение (необязательно)'),
            'is_active': _('Игра активна (видна на сайте)'),
        }

    def clean_date(self):
        """Проверка: дата не должна быть в прошлом"""
        date = self.cleaned_data.get('date')
        if date and date < timezone.now().date():
            raise forms.ValidationError(_('Дата игры не может быть в прошлом!'))
        return date


class GameRegistrationForm(forms.ModelForm):
    """Форма регистрации на игру"""

    class Meta:
        model = GameRegistration
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "callsign",
            "participation_status",
            "has_car",
            "has_equipment",
            "comment",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Введите имя")}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Введите фамилию")}
            ),
            "phone_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+7 (999) 123-45-67"}
            ),
            "callsign": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Ваш позывной (необязательно)"),
                }
            ),
            "participation_status": forms.Select(attrs={"class": "form-select"}),
            "has_car": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "has_equipment": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("Дополнительная информация..."),
                }
            ),
        }
        labels = {
            "first_name": _("Имя"),
            "last_name": _("Фамилия"),
            "phone_number": _("Номер телефона"),
            "callsign": _("Позывной (необязательно)"),
            "participation_status": _("Статус участия"),
            "has_car": _("У меня есть автомобиль"),
            "has_equipment": _("Наличие амуниции"),
            "comment": _("Комментарий"),
        }

    def __init__(self, *args, **kwargs):
        """Инициализация формы с данными пользователя"""
        user = kwargs.pop("user", None)
        game = kwargs.pop("game", None)
        super().__init__(*args, **kwargs)

        # Сохраняем game для валидации
        self.game = game

        if user and user.is_authenticated:
            # Автоматически заполняем поля из профиля пользователя
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name

            if hasattr(user, "profile"):
                profile = user.profile
                if profile.phone_number:
                    self.fields["phone_number"].initial = profile.phone_number
                if profile.callsign:
                    self.fields["callsign"].initial = profile.callsign

            self.fields["first_name"].required = False
            self.fields["last_name"].required = False
            self.fields["phone_number"].required = False

    def clean_phone_number(self):
        """Проверка, что номер телефона не зарегистрирован на эту игру"""
        phone = self.cleaned_data.get("phone_number")

        if not phone:
            return phone

        # Проверяем только если есть game
        if hasattr(self, "game") and self.game:
            # Ищем регистрацию с таким номером на эту игру
            existing = GameRegistration.objects.filter(
                game=self.game, phone_number=phone
            ).first()

            # Если нашли и это не текущая регистрация (при редактировании)
            if existing and existing.id != self.instance.id:
                # Если пользователь авторизован и это его регистрация - пропускаем
                if hasattr(self, "user") and self.user and self.user.is_authenticated:
                    if existing.user == self.user:
                        return phone

                raise forms.ValidationError(
                    _(
                        "❌ Этот номер телефона уже зарегистрирован на эту игру. "
                        "Пожалуйста, используйте другой номер или войдите в аккаунт, "
                        "которым вы регистрировались."
                    )
                )

        return phone

    def clean(self):
        """Дополнительная проверка всей формы"""
        cleaned_data = super().clean()
        return cleaned_data


class GameRegistrationEditForm(forms.ModelForm):
    """Форма редактирования регистрации (для авторизованных)"""

    class Meta:
        model = GameRegistration
        fields = [
            "participation_status",
            "has_car",
            "has_equipment",
            "comment",
        ]
        widgets = {
            "participation_status": forms.Select(attrs={"class": "form-select"}),
            "has_car": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "has_equipment": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("Дополнительная информация..."),
                }
            ),
        }
        labels = {
            "participation_status": _("Статус участия"),
            "has_car": _("У меня есть автомобиль"),
            "has_equipment": _("Наличие амуниции"),
            "comment": _("Комментарий"),
        }


class CustomUserCreationForm(UserCreationForm):
    """Форма регистрации пользователя"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email"}
        ),
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Имя")}),
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Фамилия")}
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Имя пользователя")}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget = forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Пароль")}
        )
        self.fields["password2"].widget = forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Подтверждение пароля")}
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Форма авторизации"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget = forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Имя пользователя")}
        )
        self.fields["password"].widget = forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": _("Пароль")}
        )


class ProfileForm(forms.ModelForm):
    """Форма редактирования профиля"""

    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Имя")}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Фамилия")}
        ),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email"}
        ),
    )

    class Meta:
        model = Profile
        fields = [
            "avatar",
            "birth_date",
            "callsign",
            "phone_number",
            "bio",
        ]
        widgets = {
            "avatar": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "callsign": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("Ваш позывной")}
            ),
            "phone_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+7 (999) 123-45-67"}
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": _("Расскажите о себе..."),
                }
            ),
        }
        labels = {
            "avatar": _("Аватар"),
            "birth_date": _("День рождения"),
            "callsign": _("Позывной"),
            "phone_number": _("Номер телефона"),
            "bio": _("О себе"),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email

    def save(self, user=None, commit=True):
        """Сохраняем изменения в User и Profile"""
        profile = super().save(commit=False)

        if user:
            user.first_name = self.cleaned_data.get("first_name", "")
            user.last_name = self.cleaned_data.get("last_name", "")
            user.email = self.cleaned_data.get("email", "")
            if commit:
                user.save()

        if commit:
            profile.save()

        return profile
