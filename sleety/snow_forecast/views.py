from django.shortcuts import render
import json
import requests
from .models import Resort
import plotly.graph_objs as go
import numpy as np
from django.views.generic import ListView
from blog.models import Post

def home(request):
    resorts = Resort.objects.all()

    # Extract latitude and longitude values into separate lists
    latitudes = [resort.lat for resort in resorts]
    longitudes = [resort.lon for resort in resorts]
    timezones = [resort.timezone for resort in resorts]
    base = [resort.base for resort in resorts]

    # Convert the lists to strings for the API request
    lat_str = ",".join(map(str, latitudes))
    lon_str = ",".join(map(str, longitudes))
    tz_str = ",".join(map(str, timezones))
    base_str = ",".join(map(str, base))

    # Make the API request using the constructed URL
    api_request = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&forecast_days=10&daily=snowfall_sum&timezone={tz_str}&elevation={base_str}")

    api = json.loads(api_request.content)

    # times = []
    # temperatures_2m = []

    # # Iterate through each item in the JSON data
    # for item in api:
    #     # Extract time and temperature_2m data
    #     times.append(item['hourly']['time'])
    #     temperatures_2m.append(item['hourly']['temperature_2m'])

            # Create a dictionary to store the data

       # Create a dictionary to store the data
    resort_data = {}
    resort_data_3_days = {}
    resort_data_7_days = {}

    # Iterate through each item in the JSON data
    for resort, item in zip(resorts, api):
        # Extract time and temperature_2m data
        times = item['daily']['time']
        snow_sum_cm = item['daily']['snowfall_sum'] 

         # Convert snow_sum from cm to inches
        snow_sum_inches = [round(cm * 0.393701,1) for cm in snow_sum_cm]

        #get the 3 and 7 day sums
        snow_sum_3_days = np.round(np.cumsum(snow_sum_inches[:3]),1)
        snow_sum_7_days = np.round(np.cumsum(snow_sum_inches[:7]),1)

        # Add data to the dictionary
        resort_data[resort.name] = {'Time': times, 'snow_sum_inches': snow_sum_inches}
        resort_data_3_days[resort.name] = {'Time': times[:3], 'snow_sum': [f"{val}\"" for val in snow_sum_3_days.tolist()]}
        resort_data_7_days[resort.name] = {'Time': times[:7], 'snow_sum': [f"{val}\"" for val in snow_sum_7_days.tolist()]}


        # Create a list of tuples with resort names and last day's snowfall totals
        three_day_snowfall_totals = [(resort_name, data['snow_sum'][-1]) for resort_name, data in resort_data_3_days.items()]
        seven_day_snowfall_totals = [(resort_name, data['snow_sum'][-1]) for resort_name, data in resort_data_7_days.items()]

        # Sort the list of tuples based on snowfall totals in descending order
        three_day_sorted_snowfall_totals = sorted(three_day_snowfall_totals, key=lambda x: x[1], reverse=True)
        seven_day_sorted_snowfall_totals = sorted(seven_day_snowfall_totals, key=lambda x: x[1], reverse=True)

    # Fetch the latest blog posts
    latest_blog_posts = Post.objects.all()[:5]  # Adjust the query as needed

    context = {
        'api': api,
        'three_day_sorted_snowfall_totals': three_day_sorted_snowfall_totals, 
        'seven_day_sorted_snowfall_totals': seven_day_sorted_snowfall_totals, 
        'resort_data_7_days': resort_data_7_days, 
        'latest_blog_posts': latest_blog_posts,  # Pass the latest blog posts to the template
    }
    
    return render(request, 'home.html', context)

def about(request):
    return render(request, 'about.html', {})