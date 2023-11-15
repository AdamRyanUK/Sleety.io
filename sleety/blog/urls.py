from django.urls import path 
# from . import views
from .views import BlogView, BlogDetail


urlpatterns = [
    # path('blog/', views.blog, name="blog"),
    path('blog/', BlogView.as_view(), name = "blog"),
    path('article/<int:pk>', BlogDetail.as_view(), name="article-detail"),
]