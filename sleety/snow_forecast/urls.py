from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from snow_forecast.views import home, about, resorts, forecast, graphs, dynamic_lookup_view


urlpatterns = [
   path('', views.home, name="home"), 
   path('about/', views.about, name="about"), 
   path('resorts/', views.resorts, name='resorts'),
   path('forecast/', views.forecast, name='forecast'),
   path('graphs/', views.graphs, name='graphs'),
   path('practice/<str:name>/', views.dynamic_lookup_view, name='practice'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)