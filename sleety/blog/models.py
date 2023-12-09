from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import datetime, date
from django.utils.text import slugify
from ckeditor.fields import RichTextField

class Category(models.Model):
    category_name = models.CharField(max_length=255)

    def __str__(self):
        return self.category_name
    
    def get_absolute_url(self):
        return reverse('home', args=(str(self.id)))

class Post(models.Model):
    title = models.CharField(max_length=255)
    header_image = models.ImageField(null=True, blank=True, upload_to="images/")
    titletag = models.CharField(max_length=255, default="sleety.io")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = RichTextField(blank=True, null=True)
    # body = models.TextField()
    post_date = models.DateField(auto_now_add=True)
    category = models.CharField(max_length=255, default='uncategorized')
    category_slug = models.SlugField(blank=True)
    snippet = models.CharField(max_length=255)
    likes = models.ManyToManyField(User, related_name='blog_posts')

    def total_likes(self):
        return self.likes.count()

    def save(self, *args, **kwargs):
        self.category_slug = slugify(self.category)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title + ' | ' + str(self.author)
    
    def get_absolute_url(self):
        return reverse('article-detail', args=(str(self.id)))

class Comment(models.Model):
    post = models.ForeignKey(Post, related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=255)
    body = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)

    def total_likes(self):
        return self.likes.count()

    def __str__(self):
        return '%s - %s' % (self.post.title, self.name)
    


