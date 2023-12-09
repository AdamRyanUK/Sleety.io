# Generated by Django 4.2.6 on 2023-11-18 15:12

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0007_alter_post_category"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="post",
            name="category",
        ),
        migrations.AddField(
            model_name="post",
            name="category",
            field=models.CharField(default="uncategorized", max_length=255),
        ),
    ]