from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .notifications import send_telegram_message

User = get_user_model()


@receiver(post_save, sender=User)
def notify_new_user(sender, instance, created, **kwargs):
    if created:
        text = (
            f'👤 <b>Новый пользователь!</b>\n\n'
            f'Имя: {instance.username}\n'
            f'Email: {instance.email or "—"}'
        )
        send_telegram_message(text)
