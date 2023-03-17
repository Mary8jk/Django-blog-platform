# добавить новый файл с миграцией. создать файл '0002_add_group.py'
# нужно убедиться, что файл с первой миграцией называется так `0001_initial.py`
# после того как будет создан этот файл можно запускать:
# python manage.py migrate
# новый файл миграции -->

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='group',
            field=models.TextField(blank=True, max_length=400, null=True),
        ),
    ]
