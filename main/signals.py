from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .notifications import send_telegram_message


User = get_user_model()


@receiver(post_save, sender=User)
def notify_new_user(sender, instance, created, **kwargs):
    if created:
        text = f"👤 *Новый пользователь!*\n\nИмя: {instance.username}\nEmail: {instance.email}"
        send_telegram_message(text)
