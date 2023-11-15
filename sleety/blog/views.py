from django.shortcuts import render
from django.views.generic import ListView, DetailView
from .models import Post

# # Create your views here.
# def blog(request):
#     return render(request, 'blog.html', {})

class BlogView(ListView):
    model = Post
    template_name= 'blog.html'

class BlogDetail(DetailView):
    model = Post
    template_name = 'blog_content.html'