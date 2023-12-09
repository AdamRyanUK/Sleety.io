from django.shortcuts import render
from .models import Resort

def countries(request):
    countries_queryset = Resort.objects.values('country').distinct()
    countries = set(item['country'] for item in countries_queryset)
    sorted_countries = sorted(countries)
    return {'countries': sorted_countries}

