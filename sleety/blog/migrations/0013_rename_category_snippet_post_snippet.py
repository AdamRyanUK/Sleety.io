# Generated by Django 4.2.6 on 2023-11-18 20:55

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0012_post_category_snippet"),
    ]

    operations = [
        migrations.RenameField(
            model_name="post",
            old_name="category_snippet",
            new_name="snippet",
        ),
    ]
