from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_notifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameregistration',
            name='attended',
            field=models.BooleanField(blank=True, null=True, verbose_name='Присутствовал'),
        ),
    ]
