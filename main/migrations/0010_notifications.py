from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_gameregistration_waitlist'),
    ]

    operations = [
        migrations.AddField(
            model_name='airsoftgame',
            name='reminder_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Напоминание отправлено'),
        ),
        migrations.AddField(
            model_name='profile',
            name='notify_email',
            field=models.BooleanField(default=True, verbose_name='Уведомления на email'),
        ),
        migrations.AddField(
            model_name='profile',
            name='notify_telegram',
            field=models.BooleanField(default=True, verbose_name='Уведомления в Telegram'),
        ),
        migrations.AddField(
            model_name='profile',
            name='notification_language',
            field=models.CharField(default='ru', max_length=8, verbose_name='Язык уведомлений'),
        ),
        migrations.AddField(
            model_name='profile',
            name='telegram_chat_id',
            field=models.BigIntegerField(blank=True, null=True, unique=True, verbose_name='Telegram chat ID'),
        ),
        migrations.AddField(
            model_name='profile',
            name='telegram_link_token',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Telegram link token'),
        ),
    ]
