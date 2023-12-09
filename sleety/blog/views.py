from typing import Any
from django.forms.models import BaseModelForm
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Post, Category, Comment
from .forms import PostForm, EditForm, CommentForm
from django.urls import reverse_lazy, reverse
from django.utils.text import slugify
from django.http import HttpResponse, HttpResponseRedirect

class BlogView(ListView):
    model = Post
    template_name= 'blog.html'
    ordering = ['-post_date']
    # ordering = ['-id']

def CategoryView(request, cats):
    category_slug = slugify(cats)  # Slugify the category name
    category_posts = Post.objects.filter(category_slug=category_slug)
    return render(request, 'categories.html', {'cats': cats.title(), 'category_posts': category_posts, 'category_slug': category_slug})

class BlogDetail(DetailView):
    model = Post
    template_name = 'blog_content.html'

    def get_context_data(self, *args, **kwargs):
        context = super(BlogDetail, self).get_context_data(*args, **kwargs)

        stuff = get_object_or_404(Post, id=self.kwargs['pk'])
        total_likes = stuff.total_likes()

        liked = False
        if stuff.likes.filter(id = self.request.user.id).exists():
            liked = True

        context["total_likes"] = total_likes
        context["liked"] = liked
        return context

class AddPost(CreateView):
    model = Post
    form_class = PostForm
    template_name = 'add_post.html'
    success_url = reverse_lazy('blog')
    # fields = '__all__'

class AddCategory(CreateView):
    model = Category
    # form_class = PostForm
    template_name = 'add_category.html'
    fields = '__all__'
    success_url = reverse_lazy('blog')

class UpdateBlog(UpdateView):
    model = Post
    form_class = EditForm
    template_name = 'update_post.html' 
    # fields = ['title', 'titletag', 'body']

class DeleteBlog(DeleteView):
    model = Post
    template_name = 'delete_post.html' 
    success_url = reverse_lazy('blog')

def LikeView(request, pk):
    post = get_object_or_404(Post, id=request.POST.get('post_id'))
    liked = False
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True

    return HttpResponseRedirect(reverse('article-detail', args =[str(pk)]))

# class AddComment(CreateView):
#     model = Comment
#     form_class = CommentForm
#     template_name = 'add_comment.html'
#     # fields = '__all__'

#     def form_valid(self, form):
#         form.instance.post_id = self.kwargs['pk']
#         response = super().form_valid(form)
#         self.success_url = reverse_lazy('article-detail', args=[str(self.kwargs['pk'])])
#         return response
#         # return super().form_valid(form)

class AddComment(CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'add_comment.html'

    def form_valid(self, form):
        form.instance.post_id = self.kwargs['pk']
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('article-detail', args=[str(self.kwargs['pk'])])


