# Generated by Django 4.2.7 on 2023-11-11 20:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("snow_forecast", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="resort",
            options={"ordering": ["name"], "verbose_name_plural": "Resorts"},
        ),
        migrations.AlterField(
            model_name="resort",
            name="name",
            field=models.CharField(
                blank=True,
                default="",
                max_length=100,
                null=True,
                verbose_name="name",
            ),
        ),
    ]
