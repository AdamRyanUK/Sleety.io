# Generated by Django 4.2.6 on 2023-11-21 15:09

from django.db import migrations
import embed_video.fields


class Migration(migrations.Migration):
    dependencies = [
        ("videos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="video",
            name="url",
            field=embed_video.fields.EmbedVideoField(null=True),
        ),
    ]
