from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0005_category_post_category"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="post",
            name="category",
        ),
        migrations.AddField(
            model_name="post",
            name="category",
            field=models.ManyToManyField(to="blog.Category"),  # Assuming your Category model is in the 'blog' app
        ),
    ]
