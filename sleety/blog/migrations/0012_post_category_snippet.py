# Generated by Django 4.2.6 on 2023-11-18 20:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0011_alter_post_body"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="category_snippet",
            field=models.CharField(
                default="Click link above to read blog post", max_length=255
            ),
        ),
    ]
