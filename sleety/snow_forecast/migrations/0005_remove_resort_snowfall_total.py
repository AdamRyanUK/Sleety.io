# Generated by Django 4.2.7 on 2023-11-12 20:22

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("snow_forecast", "0004_alter_resort_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="resort",
            name="snowfall_total",
        ),
    ]
