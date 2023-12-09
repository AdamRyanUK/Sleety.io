from django.urls import path 
# from . import views
from .views import BlogView, BlogDetail, AddPost, LikeView, UpdateBlog, DeleteBlog, AddCategory, CategoryView, AddComment


urlpatterns = [
    # path('blog/', views.blog, name="blog"),
    path('blog/', BlogView.as_view(), name = "blog"),
    path('article/<int:pk>', BlogDetail.as_view(), name="article-detail"),
    path('addpost/', AddPost.as_view(), name="add-post"),
    path('article/<int:pk>/comment/', AddComment.as_view(), name="add-comment"),
    path('addcategory/', AddCategory.as_view(), name="add-category"),
    path('category/<slug:cats>/', CategoryView, name="category"),
    path('article/editpost/<int:pk>', UpdateBlog.as_view(), name="editblog"),
    path('article/<int:pk>/delete', DeleteBlog.as_view(), name="deleteblog"),
    path('like/<int:pk>', LikeView, name="like-post")
]