from django.urls import path
from . import views 

urlpatterns = [ 
    path('video-list/', views.videoindex, name="videos"), 
]