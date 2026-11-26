from django.db import migrations, models


def sync_registered_players(apps, schema_editor):
    """The old counter was never updated: set it to the real number of places taken."""
    AirsoftGame = apps.get_model('main', 'AirsoftGame')
    GameRegistration = apps.get_model('main', 'GameRegistration')
    for game in AirsoftGame.objects.all():
        count = GameRegistration.objects.filter(
            game=game, participation_status='yes', is_waitlisted=False
        ).count()
        AirsoftGame.objects.filter(pk=game.pk).update(registered_players=count)


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_news_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameregistration',
            name='is_waitlisted',
            field=models.BooleanField(default=False, verbose_name='В листе ожидания'),
        ),
        migrations.AddField(
            model_name='gameregistration',
            name='waitlisted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='В очереди с'),
        ),
        migrations.RunPython(sync_registered_players, migrations.RunPython.noop),
    ]
