from django.shortcuts import render
from .models import Video


def videoindex(request):
    videos = Video.objects.all()
    return render(request, 'video_list.html', context={'videos':videos})


