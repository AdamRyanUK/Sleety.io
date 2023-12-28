from django.shortcuts import render
import json
from django.shortcuts import redirect
import requests
from .models import Resort
from plotly.offline import plot
import plotly.graph_objs as go
from plotly.graph_objs import Scatter
import numpy as np
from django.views.generic import ListView
from blog.models import Post
from datetime import datetime, date, time 
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseServerError
import pandas as pd
from .forms import ResortForm
from .icons import weather_icons, weather_icons_night
from .sleety_score import calculate_conditions_base, calculate_conditions_mid, calculate_conditions_top
from .api import get_openweather_data
from .functions import path_to_image_html, calculate_temperature_for_array, only_rain, estimate_snowmelt, calculate_melt_adjusted_base_snowpack, calculate_melt_adjusted_mid_snowpack, calculate_melt_adjusted_top_snowpack 
from django.urls import reverse
from plotly.subplots import make_subplots
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize

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
    api_request = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&forecast_days=10&daily=snowfall_sum&timezone={tz_str}&elevation={base_str}&models=gfs_seamless")

    api = json.loads(api_request.content)

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
    latest_blog_posts = Post.objects.all()[:10]  # Adjust the query as needed

    #give the website the resort info 
    resorts = Resort.objects.all()
    
    context = {
        'api': api,
        'three_day_sorted_snowfall_totals': three_day_sorted_snowfall_totals, 
        'seven_day_sorted_snowfall_totals': seven_day_sorted_snowfall_totals, 
        'resort_data_7_days': resort_data_7_days, 
        'latest_blog_posts': latest_blog_posts,  # Pass the latest blog posts to the template
        'resorts': resorts,
    }
    
    return render(request, 'home.html', context)

def dynamic_lookup_view(request, name):
    obj = Resort.objects.get(name=name)
    
    if request.method == 'POST':
        selected_resort_name = request.POST.get('resort')
        # Update the obj here
        obj.name = selected_resort_name
        obj.save()
    
    context = {
        "resort": obj
    }
    return render(request, "practice.html", context)

def forecast(request):
    
    df, daily_final, selected_resort = get_openweather_data(request)

    resort_name = selected_resort


    # Retrieve the resort object
    resort = Resort.objects.get(name=resort_name)
    ###Daily 
    #Convert date column (which is the index) to datetime
    daily_final.index = pd.to_datetime(daily_final.index)

    #create bootstrap button column in df usind this datetime field.
    # Correct usage of {% url %} tag

    
    # button_html = '<button class="myButton">hourly forecast</button>'
    # daily_final['hourly_link'] = button_html

# Assuming you have a DataFrame named daily_final
    # button_html = '<button class="myButton" id="button_{index}">hourly forecast</button>'
    # daily_final['hourly_link'] = [button_html.format(index=i) for i, _ in enumerate(daily_final.index)]
    button_html_b = '<button class="myButton" id="button_{index}" data-date="{date}">hourly forecast</button>'
    daily_final['hourly_link'] = [button_html_b.format(index=i, date=date.strftime('%Y-%m-%d')) for i, date in enumerate(daily_final.index)]

    daily_base = daily_final[[
        'night', 
        'morning',
        'afternoon', 
        'evening', 
        'base_temp',
        'base_precip',
        'base_winds',
        'base_sleety_index', 
        'hourly_link'
        ]]

    daily_mid = daily_final[[
        'night',
        'morning',
        'afternoon',
        'evening',
        'mid_temp',
        'mid_precip',
        'mid_winds',
        'mid_sleety_index', 
        'hourly_link'
    ]]

    daily_top = daily_final[[
        'night', 'morning', 'afternoon', 'evening',
        'top_temp',
        'top_precip',
        'top_winds',
        'top_sleety_index',
        'hourly_link'
    ]]

    daily_base_f = daily_final[[
        'night',
        'morning',
        'afternoon',
        'evening',
        'base_temp_f',
        'base_precip',
        'base_winds',
        'base_sleety_index',
        'hourly_link'
    ]]

    daily_mid_f = daily_final[[
        'night',
        'morning',
        'afternoon',
        'evening',
        'mid_temp_f',
        'mid_precip',
        'mid_winds',
        'mid_sleety_index',
        'hourly_link'
    ]]

    daily_top_f = daily_final[[
        'night', 'morning', 'afternoon', 'evening',
        'top_temp_f',
        'top_precip',
        'top_winds',
        'top_sleety_index',
        'hourly_link'
    ]]

    daily_base = daily_base.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False,
                                    formatters={('morning'): path_to_image_html,
                                                ('afternoon'): path_to_image_html,
                                                ('evening'): path_to_image_html,
                                                ('night'): path_to_image_html})
    daily_mid = daily_mid.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False,
                                  formatters={('morning'): path_to_image_html,
                                              ('afternoon'): path_to_image_html,
                                              ('evening'): path_to_image_html,
                                              ('night'): path_to_image_html})
    daily_top = daily_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False,
                                  formatters={('morning'): path_to_image_html,
                                              ('afternoon'): path_to_image_html,
                                              ('evening'): path_to_image_html,
                                              ('night'): path_to_image_html})
    daily_base_f = daily_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False,
                                        formatters={('morning'): path_to_image_html,
                                                    ('afternoon'): path_to_image_html,
                                                    ('evening'): path_to_image_html,
                                                    ('night'): path_to_image_html})
    daily_mid_f = daily_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False,
                                      formatters={('morning'): path_to_image_html,
                                                  ('afternoon'): path_to_image_html,
                                                  ('evening'): path_to_image_html,
                                                  ('night'): path_to_image_html})
    daily_top_f = daily_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False,
                                      formatters={('morning'): path_to_image_html,
                                                  ('afternoon'): path_to_image_html,
                                                  ('evening'): path_to_image_html,
                                                  ('night'): path_to_image_html})
    
    #hourly defining the datatable 
    df_base = df[['date','hour', 'weather_icon', 'weather_code_copy', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']]   
    df_mid = df[['date','hour', 'weather_icon', 'weather_code_copy', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']]   
    df_top = df[['date','hour', 'weather_icon', 'weather_code_copy', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']]   
    df_base_f = df[['date','hour', 'weather_icon', 'weather_code_copy', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']]   
    df_mid_f = df[['date','hour', 'weather_icon', 'weather_code_copy', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']]   
    df_top_f = df[['date','hour', 'weather_icon', 'weather_code_copy', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']]   

    # Group by 'date'
    grouped_by_date_base = df_base.groupby('date')
    grouped_by_date_mid = df_mid.groupby('date')
    grouped_by_date_top = df_top.groupby('date')
    grouped_by_date_base_f = df_base_f.groupby('date')
    grouped_by_date_mid_f = df_mid_f.groupby('date')
    grouped_by_date_top_f = df_top_f.groupby('date')

    ### BASE CELCIUS HOURLY DATA #####
    # Access data for a specific date, for example, the first date in your DataFram 
    first_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[0])
    first_hourly_base = first_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    first_hourly_base.columns.name = first_hourly_base.index.name
    first_hourly_base.index.name = None
    
    second_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[1])
    second_hourly_base = second_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    second_hourly_base.columns.name = second_hourly_base.index.name
    second_hourly_base.index.name = None

    third_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[2])
    third_hourly_base = third_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    third_hourly_base.columns.name = third_hourly_base.index.name
    third_hourly_base.index.name = None

    fourth_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[3])
    fourth_hourly_base = fourth_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    fourth_hourly_base.columns.name = fourth_hourly_base.index.name
    fourth_hourly_base.index.name = None
    
    fifth_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[4])
    fifth_hourly_base = fifth_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    fifth_hourly_base.columns.name = fifth_hourly_base.index.name
    fifth_hourly_base.index.name = None
    
    sixth_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[5])
    sixth_hourly_base = sixth_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    sixth_hourly_base.columns.name = sixth_hourly_base.index.name
    sixth_hourly_base.index.name = None
    
    seventh_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[6])
    seventh_hourly_base = seventh_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    seventh_hourly_base.columns.name = seventh_hourly_base.index.name
    seventh_hourly_base.index.name = None
    
    eighth_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[7])
    eighth_hourly_base = eighth_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    eighth_hourly_base.columns.name = eighth_hourly_base.index.name
    eighth_hourly_base.index.name = None
    
    ninth_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[8])
    ninth_hourly_base = ninth_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    ninth_hourly_base.columns.name = ninth_hourly_base.index.name
    ninth_hourly_base.index.name = None
    
    tenth_date_data = grouped_by_date_base.get_group(list(grouped_by_date_base.groups.keys())[9])
    tenth_hourly_base = tenth_date_data[['hour', 'weather_icon', 'base_temp_hourly_icons', 'base_feelslike_hourly_icons', 'base_precip', 'base_winds_hourly']].set_index('hour')
    tenth_hourly_base.columns.name = tenth_hourly_base.index.name
    tenth_hourly_base.index.name = None

    ### MID CELCIUS HOURLY DATA #####
    # Access data for a specific date, for example, the first date in your DataFram 
    first_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[0])
    first_hourly_mid = first_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    first_hourly_mid.columns.name = first_hourly_mid.index.name
    first_hourly_mid.index.name = None
    
    second_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[1])
    second_hourly_mid = second_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    second_hourly_mid.columns.name = first_hourly_mid.index.name
    second_hourly_mid.index.name = None

    third_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[2])
    third_hourly_mid = third_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    third_hourly_mid.columns.name = first_hourly_mid.index.name
    third_hourly_mid.index.name = None

    fourth_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[3])
    fourth_hourly_mid = fourth_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    fourth_hourly_mid.columns.name = fourth_hourly_mid.index.name
    fourth_hourly_mid.index.name = None
    
    fifth_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[4])
    fifth_hourly_mid = fifth_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    fifth_hourly_mid.columns.name = fifth_hourly_mid.index.name
    fifth_hourly_mid.index.name = None
    
    sixth_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[5])
    sixth_hourly_mid = sixth_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    sixth_hourly_mid.columns.name = sixth_hourly_mid.index.name
    sixth_hourly_mid.index.name = None
    
    seventh_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[6])
    seventh_hourly_mid = seventh_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    seventh_hourly_mid.columns.name = seventh_hourly_mid.index.name
    seventh_hourly_mid.index.name = None
    
    eighth_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[7])
    eighth_hourly_mid = eighth_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    eighth_hourly_mid.columns.name = eighth_hourly_mid.index.name
    eighth_hourly_mid.index.name = None
    
    ninth_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[8])
    ninth_hourly_mid = ninth_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    ninth_hourly_mid.columns.name = ninth_hourly_mid.index.name
    ninth_hourly_mid.index.name = None
    
    tenth_date_data = grouped_by_date_mid.get_group(list(grouped_by_date_mid.groups.keys())[9])
    tenth_hourly_mid = tenth_date_data[['hour', 'weather_icon', 'mid_temp_hourly_icons', 'mid_feelslike_hourly_icons', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    tenth_hourly_mid.columns.name = tenth_hourly_mid.index.name
    tenth_hourly_mid.index.name = None

    ### TOP CELCIUS HOURLY DATA #####
# Access data for a specific date, for example, the first date in your DataFram 
    ### TOP CELCIUS HOURLY DATA #####
# Access data for a specific date, for example, the first date in your DataFram 
    first_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[0])
    first_hourly_top = first_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    first_hourly_top.columns.name = first_hourly_top.index.name
    first_hourly_top.index.name = None

    second_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[1])
    second_hourly_top = second_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    second_hourly_top.columns.name = second_hourly_top.index.name
    second_hourly_top.index.name = None

    third_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[2])
    third_hourly_top = third_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    third_hourly_top.columns.name = third_hourly_top.index.name
    third_hourly_top.index.name = None

    fourth_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[3])
    fourth_hourly_top = fourth_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    fourth_hourly_top.columns.name = fourth_hourly_top.index.name
    fourth_hourly_top.index.name = None

    fifth_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[4])
    fifth_hourly_top = fifth_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    fifth_hourly_top.columns.name = fifth_hourly_top.index.name
    fifth_hourly_top.index.name = None

    sixth_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[5])
    sixth_hourly_top = sixth_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    sixth_hourly_top.columns.name = sixth_hourly_top.index.name
    sixth_hourly_top.index.name = None

    seventh_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[6])
    seventh_hourly_top = seventh_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    seventh_hourly_top.columns.name = seventh_hourly_top.index.name
    seventh_hourly_top.index.name = None

    eighth_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[7])
    eighth_hourly_top = eighth_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    eighth_hourly_top.columns.name = eighth_hourly_top.index.name
    eighth_hourly_top.index.name = None

    ninth_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[8])
    ninth_hourly_top = ninth_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    ninth_hourly_top.columns.name = ninth_hourly_top.index.name
    ninth_hourly_top.index.name = None

    tenth_date_data = grouped_by_date_top.get_group(list(grouped_by_date_top.groups.keys())[9])
    tenth_hourly_top = tenth_date_data[['hour', 'weather_icon', 'top_temp_hourly_icons', 'top_feelslike_hourly_icons', 'top_precip', 'top_winds_hourly']].set_index('hour')
    tenth_hourly_top.columns.name = tenth_hourly_top.index.name
    tenth_hourly_top.index.name = None

    ### BASE FAHRENHEIT HOURLY DATA #####
    # Access data for a specific date, for example, the first date in your DataFram 
    first_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[0])
    first_hourly_base_f = first_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    first_hourly_base_f.columns.name = first_hourly_base_f.index.name
    first_hourly_base_f.index.name = None
    
    second_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[1])
    second_hourly_base_f = second_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    second_hourly_base_f.columns.name = second_hourly_base_f.index.name
    second_hourly_base_f.index.name = None

    third_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[2])
    third_hourly_base_f = third_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    third_hourly_base_f.columns.name = third_hourly_base_f.index.name
    third_hourly_base_f.index.name = None

    fourth_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[3])
    fourth_hourly_base_f = fourth_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    fourth_hourly_base_f.columns.name = fourth_hourly_base_f.index.name
    fourth_hourly_base_f.index.name = None
    
    fifth_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[4])
    fifth_hourly_base_f = fifth_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    fifth_hourly_base_f.columns.name = fifth_hourly_base_f.index.name
    fifth_hourly_base_f.index.name = None
    
    sixth_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[5])
    sixth_hourly_base_f = sixth_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    sixth_hourly_base_f.columns.name = sixth_hourly_base_f.index.name
    sixth_hourly_base_f.index.name = None
    
    seventh_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[6])
    seventh_hourly_base_f = seventh_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    seventh_hourly_base_f.columns.name = seventh_hourly_base_f.index.name
    seventh_hourly_base_f.index.name = None
    
    eighth_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[7])
    eighth_hourly_base_f = eighth_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    eighth_hourly_base_f.columns.name = eighth_hourly_base_f.index.name
    eighth_hourly_base_f.index.name = None
    
    ninth_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[8])
    ninth_hourly_base_f = ninth_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    ninth_hourly_base_f.columns.name = ninth_hourly_base_f.index.name
    ninth_hourly_base_f.index.name = None
    
    tenth_date_data_f = grouped_by_date_base_f.get_group(list(grouped_by_date_base_f.groups.keys())[9])
    tenth_hourly_base_f = tenth_date_data_f[['hour', 'weather_icon', 'base_temp_hourly_icons_f', 'base_feelslike_hourly_icons_f', 'base_precip', 'base_winds_hourly']].set_index('hour')
    tenth_hourly_base_f.columns.name = tenth_hourly_base_f.index.name
    tenth_hourly_base_f.index.name = None

    ### MID fahrenheit HOURLY DATA #####
# Access data for a specific date, for example, the first date in your DataFrame
    first_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[0])
    first_hourly_mid_f = first_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    first_hourly_mid_f.columns.name = first_hourly_mid_f.index.name
    first_hourly_mid_f.index.name = None

    second_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[1])
    second_hourly_mid_f = second_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    second_hourly_mid_f.columns.name = second_hourly_mid_f.index.name
    second_hourly_mid_f.index.name = None

    third_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[2])
    third_hourly_mid_f = third_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    third_hourly_mid_f.columns.name = third_hourly_mid_f.index.name
    third_hourly_mid_f.index.name = None

    fourth_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[3])
    fourth_hourly_mid_f = fourth_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    fourth_hourly_mid_f.columns.name = fourth_hourly_mid_f.index.name
    fourth_hourly_mid_f.index.name = None

    fifth_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[4])
    fifth_hourly_mid_f = fifth_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    fifth_hourly_mid_f.columns.name = fifth_hourly_mid_f.index.name
    fifth_hourly_mid_f.index.name = None

    sixth_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[5])
    sixth_hourly_mid_f = sixth_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    sixth_hourly_mid_f.columns.name = sixth_hourly_mid_f.index.name
    sixth_hourly_mid_f.index.name = None

    seventh_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[6])
    seventh_hourly_mid_f = seventh_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    seventh_hourly_mid_f.columns.name = seventh_hourly_mid_f.index.name
    seventh_hourly_mid_f.index.name = None

    eighth_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[7])
    eighth_hourly_mid_f = eighth_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    eighth_hourly_mid_f.columns.name = eighth_hourly_mid_f.index.name
    eighth_hourly_mid_f.index.name = None

    ninth_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[8])
    ninth_hourly_mid_f = ninth_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    ninth_hourly_mid_f.columns.name = ninth_hourly_mid_f.index.name
    ninth_hourly_mid_f.index.name = None

    tenth_date_data_f = grouped_by_date_mid_f.get_group(list(grouped_by_date_mid_f.groups.keys())[9])
    tenth_hourly_mid_f = tenth_date_data_f[['hour', 'weather_icon', 'mid_temp_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'mid_precip', 'mid_winds_hourly']].set_index('hour')
    tenth_hourly_mid_f.columns.name = tenth_hourly_mid_f.index.name
    tenth_hourly_mid_f.index.name = None

    #TOP FAHRENHEIT

    first_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[0])
    first_hourly_top_f = first_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    first_hourly_top_f.columns.name = first_hourly_top_f.index.name
    first_hourly_top_f.index.name = None

    second_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[1])
    second_hourly_top_f = second_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    second_hourly_top_f.columns.name = second_hourly_top_f.index.name
    second_hourly_top_f.index.name = None

    third_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[2])
    third_hourly_top_f = third_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    third_hourly_top_f.columns.name = third_hourly_top_f.index.name
    third_hourly_top_f.index.name = None

    fourth_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[3])
    fourth_hourly_top_f = fourth_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    fourth_hourly_top_f.columns.name = fourth_hourly_top_f.index.name
    fourth_hourly_top_f.index.name = None

    fifth_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[4])
    fifth_hourly_top_f = fifth_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    fifth_hourly_top_f.columns.name = fifth_hourly_top_f.index.name
    fifth_hourly_top_f.index.name = None

    sixth_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[5])
    sixth_hourly_top_f = sixth_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    sixth_hourly_top_f.columns.name = sixth_hourly_top_f.index.name
    sixth_hourly_top_f.index.name = None

    seventh_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[6])
    seventh_hourly_top_f = seventh_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    seventh_hourly_top_f.columns.name = seventh_hourly_top_f.index.name
    seventh_hourly_top_f.index.name = None

    eighth_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[7])
    eighth_hourly_top_f = eighth_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    eighth_hourly_top_f.columns.name = eighth_hourly_top_f.index.name
    eighth_hourly_top_f.index.name = None

    ninth_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[8])
    ninth_hourly_top_f = ninth_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    ninth_hourly_top_f.columns.name = ninth_hourly_top_f.index.name
    ninth_hourly_top_f.index.name = None

    tenth_date_data_f = grouped_by_date_top_f.get_group(list(grouped_by_date_top_f.groups.keys())[9])
    tenth_hourly_top_f = tenth_date_data_f[['hour', 'weather_icon', 'top_temp_hourly_icons_f', 'top_feelslike_hourly_icons_f', 'top_precip', 'top_winds_hourly']].set_index('hour')
    tenth_hourly_top_f.columns.name = tenth_hourly_top_f.index.name
    tenth_hourly_top_f.index.name = None

    #####FINAL RENDERED HOURLY DF's##########


    dataframes_base = {
    'first_hourly_base': first_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    'second_hourly_base': second_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    'third_hourly_base': third_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    'fourth_hourly_base' : fourth_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    'fifth_hourly_base': fifth_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    'sixth_hourly_base': sixth_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    'seventh_hourly_base': seventh_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    'eighth_hourly_base': eighth_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    'ninth_hourly_base': ninth_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    'tenth_hourly_base':tenth_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),             
    }
    
    dataframes_mid = {
        'first_hourly_mid': first_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
        'second_hourly_mid' : second_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
        'third_hourly_mid' : third_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
        'fourth_hourly_mid' : fourth_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
        'fifth_hourly_mid' : fifth_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
        'sixth_hourly_mid' : sixth_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
        'seventh_hourly_mid' : seventh_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
        'eighth_hourly_mid' : eighth_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
        'ninth_hourly_mid' : ninth_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
        'tenth_hourly_mid' : tenth_hourly_mid.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html}),
    }

    dataframes_top = {
    'first_hourly_top': first_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'second_hourly_top': second_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'third_hourly_top': third_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'fourth_hourly_top': fourth_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'fifth_hourly_top': fifth_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'sixth_hourly_top': sixth_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'seventh_hourly_top': seventh_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'eighth_hourly_top': eighth_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'ninth_hourly_top': ninth_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'tenth_hourly_top': tenth_hourly_top.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
}
    
    dataframes_base_f = {
    'first_hourly_base_f': first_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'second_hourly_base_f': second_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'third_hourly_base_f': third_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'fourth_hourly_base_f': fourth_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'fifth_hourly_base_f': fifth_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'sixth_hourly_base_f': sixth_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'seventh_hourly_base_f': seventh_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'eighth_hourly_base_f': eighth_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'ninth_hourly_base_f': ninth_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'tenth_hourly_base_f': tenth_hourly_base_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
}

    dataframes_mid_f = {
    'first_hourly_mid_f': first_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'second_hourly_mid_f': second_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'third_hourly_mid_f': third_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'fourth_hourly_mid_f': fourth_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'fifth_hourly_mid_f': fifth_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'sixth_hourly_mid_f': sixth_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'seventh_hourly_mid_f': seventh_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'eighth_hourly_mid_f': eighth_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'ninth_hourly_mid_f': ninth_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'tenth_hourly_mid_f': tenth_hourly_mid_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
}

    dataframes_top_f = {
    'first_hourly_top_f': first_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'second_hourly_top_f': second_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'third_hourly_top_f': third_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'fourth_hourly_top_f': fourth_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'fifth_hourly_top_f': fifth_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'sixth_hourly_top_f': sixth_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'seventh_hourly_top_f': seventh_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'eighth_hourly_top_f': eighth_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'ninth_hourly_top_f': ninth_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
    'tenth_hourly_top_f': tenth_hourly_top_f.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={'weather_icon': path_to_image_html}),
}


    df_hourly_mid_c = first_hourly_base.to_html(classes='table table-striped table-bordered table-hover table-sm',escape=False , formatters={'weather_icon':path_to_image_html})
    resorts = Resort.objects.all()
    
    context = {
    # 'daily_final': daily_final,
    'selected_resort': selected_resort,
    'dataframes_base':dataframes_base,
    'dataframes_mid': dataframes_mid,
    'dataframes_top': dataframes_top,
    'dataframes_base_f':dataframes_base_f,
    'dataframes_mid_f': dataframes_mid_f,
    'dataframes_top_f': dataframes_top_f,
    'df_review': df_hourly_mid_c,
    'hourly_df': df.to_html(),
    'daily_base': daily_base,
    'daily_mid':daily_mid,
    'daily_top':daily_top,
    'daily_base_f': daily_base_f,
    'daily_mid_f':daily_mid_f,
    'daily_top_f':daily_top_f,
    'resort': resort,
    'resorts': resorts,
}

    # request.session['hourly_df'] = df
    request.session['selected_resort'] = selected_resort.to_json()
    df['datetime'] = df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

    df = df[[
    'datetime',
    'precipitation',
    'temperature_2m',
    'temp_mid',
    'temp_top',
    'temperature_850hPa',
    'base_snowfall_total',
    'mid_snowfall_total',
    'top_snowfall_total',
    'base_cumulative_snowfall',
    'mid_cumulative_snowfall',
    'top_cumulative_snowfall',
    'wind_speed_base',
    'wind_gusts_base',
    'wind_speed_mid',
    'wind_gusts_mid',
    'wind_speed_top',
    'wind_gusts_top',
    'cloud_cover',
    'direct_radiation',
    'feelslike_base_min',
    'feelslike_mid_min',
    'feelslike_top_min',
    'feelslike_base_max'
]]

    df_dict = df.to_dict()
    request.session['df'] = df_dict
    request.session.save()

    return render(request, 'forecast.html', context)

def graphs(request, selected_resort):
    
    serialized_resort_data = request.session.get('selected_resort')

    if serialized_resort_data:
        # Recreate the Resort object from the serialized data
        selected_resort = Resort.from_json(serialized_resort_data)
    else:
        # Handle the case when 'selected_resort' is not in the session
        selected_resort = None

    df_dict = request.session.get('df')
    df = pd.DataFrame.from_dict(df_dict)

    resort_name = selected_resort

    # Retrieve the resort object
    resort = Resort.objects.get(name=resort_name)

    #processing data for temp array. 
    df['time'] = pd.to_datetime(df['datetime'])

    #create the only rain column 
    df['only_rain_base'] = df.apply(lambda row: only_rain(row['precipitation'], row['temperature_2m']), axis=1)
    df['only_rain_mid'] = df.apply(lambda row: only_rain(row['precipitation'], row['temp_mid']), axis=1)
    df['only_rain_top'] = df.apply(lambda row: only_rain(row['precipitation'], row['temp_top']), axis=1)

    # Sample data (replace this with your actual data)
    hourly_temp_1500m = df['temperature_850hPa']
    dates = df['time']

    # Heights at 100m intervals from 0m to 4000m
    heights = list(range(0, 4100, 100))

    # Create a new DataFrame with heights as the index and dates as columns
    new_df = pd.DataFrame(index=heights, columns=dates, dtype=float)

    # Apply the function to calculate temperatures at different heights and fill the new DataFrame
    for height in heights:
        new_df.loc[height, :] = hourly_temp_1500m.apply(lambda x: calculate_temperature_for_array(x, height)).values

    # Increase the interpolation range
    interpolated_df = new_df.interpolate(method='cubic', axis=1, limit_area='inside', limit_direction='both', limit=5)

    # Apply a rolling window for additional smoothing
    smoothed_df = interpolated_df.rolling(window=5, axis=1, min_periods=1, center=True).mean()

    # Convert the DataFrame to a NumPy array
    data_array = smoothed_df.values
    
    # # creating graphs for base elevation in Celcius
    df['snowmelt'] = df.apply(lambda row: estimate_snowmelt(row['temperature_2m'], row['only_rain_base']), axis=1)
    base_hourly_snowfall = df['base_snowfall_total']
    base_hourly_rainfall = df['only_rain_base']
    base_cumulative_snowfall = df['base_cumulative_snowfall']
    base_melt_adjusted_snowpack = calculate_melt_adjusted_base_snowpack(df)
    # wind_speed_base = df['wind_speed_base']
    # base_wind_gusts = df['wind_gusts_base']

    elevation = 100  # Change this to your desired elevation

    fig = make_subplots(
        rows=5, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.02,
        subplot_titles=("Sunshine vs. Cloud", "Temperatures", "Rain vs. Snow", "Wind", "Sleety Index"),
        row_heights=[0.45, 0.85, 0.35, 0.25, 0.1]  # Adjust these values as needed
    )

    fig.add_trace(
        go.Scatter(
            x=df.time,
            y=[50]*len(df),  # Baseline at y=100
            mode='lines',
            line=dict(width=0),  # Invisible line
            showlegend=False,
        )
    )

    # Create an area trace for cloud cover
    fig.add_trace(
        go.Scatter(
            x=df.time,
            y=df['cloud_cover'] + elevation-50,  # Varying thickness over time, elevated
            fill='tonexty',  # Fill to next y-value
            fillcolor='rgba(128, 128, 128, 0.5)',  # Semi-transparent grey
            line=dict(color='rgba(128, 128, 128, 1)'),  # Grey line
            line_shape='spline',  # This line makes the line rounded
            name='Cloud Cover',
            showlegend=False,
        )
    )
    # Assuming df['direct_radiation'] contains the direct radiation data
# Assuming df['direct_radiation'] contains the direct radiation data
    for i in range(len(df)):
        fig.add_trace(
            go.Bar(
                x=[df.time[i]],
                y=[elevation-50],
                marker=dict(
                    color='yellow',
                    line=dict(color='yellow', width=3),
                    opacity=max(0, min(df['direct_radiation'][i] / max(df['direct_radiation']), 1))  # Normalize to [0,1]
                ),
                showlegend=False,
                # hoverinfo='none'
            ),
            row=1,  # Change this to the row number where you want the bars
            col=1
        )


    fig.add_trace(
        go.Heatmap(
            z=data_array,
            x=smoothed_df.columns,
            y=heights,
            showscale=False,
            colorscale='balance',
            zmid=0,
            showlegend=False,
            colorbar=dict(showticklabels=False) 
        ),
        row=2, col=1
    )
    # Add the bar plot for mid_hourly_snowfall to the second subplot
    fig.add_trace(
        go.Bar(
            x=df.time,
            y=base_hourly_snowfall,
            name='Base Hourly Snowfall',
            marker=dict(color='blue'),
            showlegend=False
        ),
        row=3, col=1
    )

    # Add the bar plot for mid_hourly_rainfall to the third subplot
    fig.add_trace(
        go.Bar(
            x=df.time,
            y=base_hourly_rainfall,
            name='base Hourly Rainfall',
            marker=dict(color='red'),
            showlegend=False
        ),
        row=3, col=1
    )
    # Add the line plot for mid_cumulative_snowfall to the third subplot
    fig.add_trace(
        go.Line(
            x=df.time,
            y=base_melt_adjusted_snowpack,
            name='base Cumulative Snowfall',
            marker=dict(color='blue'),
            showlegend=False
        ),
        row=3, col=1
    )

    # Smooth the data
    smooth_window = 5
    wind_speed_smooth = np.convolve(df['wind_speed_base'], np.ones(smooth_window)/smooth_window, mode='valid')
    base_wind_gusts_smooth = np.convolve(df['wind_gusts_base'], np.ones(smooth_window)/smooth_window, mode='valid')

    # Ensure gusts line does not go below wind speed line
    base_wind_gusts_smooth = np.maximum(base_wind_gusts_smooth, wind_speed_smooth)

    # Add the scatter plot for mid_wind_speed with a central line
    fig.add_trace(
        go.Scatter(
            x=df['time'][smooth_window//2:-smooth_window//2+1],
            y=wind_speed_smooth,
            mode='lines',
            name='base Wind Speed',
            line=dict(color='green', shape='spline'),
            showlegend=False
        ),
        row=4, col=1
    )

    # Add the scatter plot for mid_wind_gusts with confidence intervals
    fig.add_trace(
        go.Scatter(
            x=df['time'][smooth_window//2:-smooth_window//2+1],
            y=base_wind_gusts_smooth,
            mode='lines',
            name='Base Wind Gusts',
            line=dict(color='purple', shape='spline'),
            fill='tonexty',  # Fill to the line below (gusts line)
            fillcolor='rgba(128,0,128,0.3)',  # Adjust color and opacity as needed
            showlegend=False
        ),
        row=4, col=1
    )
            


    def calculate_conditions(row):
            
            score = 0

            # Sunny weather
            if row['direct_radiation'] > 50:
                score += 2
                
            # Cloud Cover
            if row['cloud_cover'] <90:
                score += 2

            # Feelslike temp 
            if row['feelslike_base_min'] > -10:
                score += 3

            # Low wind speed
            if row['wind_speed_base'] < 15:  # Adjust the threshold as needed
                score += 2

            # Significant fresh snow in the last 24 hours
            if row['base_cumulative_snowfall'] > 20:  # Adjust the threshold as needed
                score += 3

            return score
        
    # Add a new column 'sleety_score' to your DataFrame
    df['sleety_score'] = df.apply(calculate_conditions, axis=1)

    for i in range(len(df)):
        fig.add_trace(
            go.Bar(
                x=[df.time[i]],
                y=[elevation-90],
                marker=dict(
                    color='green',
                    line=dict(color='green', width=3),
                    opacity=df['sleety_score'][i] / max(df['sleety_score'])  # Normalize to [0,1]
                ),
                showlegend=False,
    #             hoverinfo='none'
            ),
            row=5,  # Change this to the row number where you want the bars
            col=1
        )

    # Add horizontal lines at 1500m, 2000m, and 2500m to the first subplot
    fig.add_shape(type="line", x0=smoothed_df.columns[1], y0=resort.base, x1=smoothed_df.columns[-1], y1=resort.base, line=dict(color="Black", width=2, dash="dash"), row=2, col=1)
    fig.add_shape(type="line", x0=smoothed_df.columns[1], y0=resort.mid, x1=smoothed_df.columns[-1], y1=resort.mid, line=dict(color="Black", width=2, dash="dash"), row=2, col=1)
    fig.add_shape(type="line", x0=smoothed_df.columns[1], y0=resort.top, x1=smoothed_df.columns[-1], y1=resort.top, line=dict(color="Black", width=2, dash="dash"), row=2, col=1)

    # Set labels and title
    fig.update_layout(
        title='Base Graphs',
        xaxis_title='Datetime',
        autosize=False,
        width=1200,
        height=900,
        yaxis=dict(),
        showlegend=False,
    )

    fig.update_coloraxes(showscale=False) 
    # fig.update_yaxes(showticklabels=False)

    # Show the plot
    plot_base_c = plot(fig, output_type='div', include_plotlyjs=False, link_text='', show_link=False)

    # ############################################
    # #creating graphs for mid elevation in Celcius
    # ############################################

    df['snowmelt'] = df.apply(lambda row: estimate_snowmelt(row['temp_mid'], row['only_rain_mid']), axis=1)
    mid_hourly_snowfall = df['mid_snowfall_total']
    mid_hourly_rainfall = df['only_rain_mid']
    mid_cumulative_snowfall = df['mid_cumulative_snowfall']
    mid_melt_adjusted_snowpack = calculate_melt_adjusted_mid_snowpack(df)
    wind_speed_mid = df['wind_speed_mid']
    mid_wind_gusts = df['wind_gusts_mid']


    elevation = 100  # Change this to your desired elevation

    fig = make_subplots(
        rows=5, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.02,
        subplot_titles=("Sunshine vs. Cloud", "Temperatures", "Rain vs. Snow", "Wind", "Sleety Index"),
        row_heights=[0.45, 0.85, 0.35, 0.25, 0.1]  # Adjust these values as needed
    )

    fig.add_trace(
        go.Scatter(
            x=df.time,
            y=[50]*len(df),  # Baseline at y=100
            mode='lines',
            line=dict(width=0),  # Invisible line
            showlegend=False,
        )
    )

    # Create an area trace for cloud cover
    fig.add_trace(
        go.Scatter(
            x=df.time,
            y=df['cloud_cover'] + elevation-50,  # Varying thickness over time, elevated
            fill='tonexty',  # Fill to next y-value
            fillcolor='rgba(128, 128, 128, 0.5)',  # Semi-transparent grey
            line=dict(color='rgba(128, 128, 128, 1)'),  # Grey line
            line_shape='spline',  # This line makes the line rounded
            name='Cloud Cover',
            showlegend=False,
        )
    )
    # Assuming df['direct_radiation'] contains the direct radiation data
# Assuming df['direct_radiation'] contains the direct radiation data
    for i in range(len(df)):
        fig.add_trace(
            go.Bar(
                x=[df.time[i]],
                y=[elevation-50],
                marker=dict(
                    color='yellow',
                    line=dict(color='yellow', width=3),
                    opacity=max(0, min(df['direct_radiation'][i] / max(df['direct_radiation']), 1))  # Normalize to [0,1]
                ),
                showlegend=False,
                # hoverinfo='none'
            ),
            row=1,  # Change this to the row number where you want the bars
            col=1
        )

    fig.add_trace(
        go.Heatmap(
            z=data_array,
            x=smoothed_df.columns,
            y=heights,
            showscale=False,
            colorscale='balance',
            zmid=0,
            showlegend=False,
            colorbar=dict(showticklabels=False) 
        ),
        row=2, col=1
    )
    # Add the bar plot for mid_hourly_snowfall to the second subplot
    fig.add_trace(
        go.Bar(
            x=df.time,
            y=mid_hourly_snowfall,
            name='Mid Hourly Snowfall',
            marker=dict(color='blue'),
            showlegend=False
        ),
        row=3, col=1
    )

    # Add the bar plot for mid_hourly_rainfall to the third subplot
    fig.add_trace(
        go.Bar(
            x=df.time,
            y=mid_hourly_rainfall,
            name='Mid Hourly Rainfall',
            marker=dict(color='red'),
            showlegend=False
        ),
        row=3, col=1
    )
    # Add the line plot for mid_cumulative_snowfall to the third subplot
    fig.add_trace(
        go.Line(
            x=df.time,
            y=mid_melt_adjusted_snowpack,
            name='Mid Cumulative Snowfall',
            marker=dict(color='blue'),
            showlegend=False
        ),
        row=3, col=1
    )

    # Smooth the data
    smooth_window = 5
    wind_speed_smooth = np.convolve(wind_speed_mid, np.ones(smooth_window)/smooth_window, mode='valid')
    mid_wind_gusts_smooth = np.convolve(mid_wind_gusts, np.ones(smooth_window)/smooth_window, mode='valid')

    # Ensure gusts line does not go below wind speed line
    mid_wind_gusts_smooth = np.maximum(mid_wind_gusts_smooth, wind_speed_smooth)

    # Add the scatter plot for mid_wind_speed with a central line
    fig.add_trace(
        go.Scatter(
            x=df['time'][smooth_window//2:-smooth_window//2+1],
            y=wind_speed_smooth,
            mode='lines',
            name='mid Wind Speed',
            line=dict(color='green', shape='spline'),
            showlegend=False
        ),
        row=4, col=1
    )

    # Add the scatter plot for mid_wind_gusts with confidence intervals
    fig.add_trace(
        go.Scatter(
            x=df['time'][smooth_window//2:-smooth_window//2+1],
            y=base_wind_gusts_smooth,
            mode='lines',
            name='Mid Wind Gusts',
            line=dict(color='purple', shape='spline'),
            fill='tonexty',  # Fill to the line below (gusts line)
            fillcolor='rgba(128,0,128,0.3)',  # Adjust color and opacity as needed
            showlegend=False
        ),
        row=4, col=1
    )
            
    def calculate_conditions(row):
            
            score = 0

            # Sunny weather
            if row['direct_radiation'] > 50:
                score += 2
                
            # Cloud Cover
            if row['cloud_cover'] <90:
                score += 2

            # Feelslike temp 
            if row['feelslike_base_min'] > -10:
                score += 3

            # Low wind speed
            if row['wind_speed_mid'] < 15:  # Adjust the threshold as needed
                score += 2

            # Significant fresh snow in the last 24 hours
            if row['mid_cumulative_snowfall'] > 20:  # Adjust the threshold as needed
                score += 3

            return score
        
    # Add a new column 'sleety_score' to your DataFrame
    df['sleety_score'] = df.apply(calculate_conditions, axis=1)

    for i in range(len(df)):
        fig.add_trace(
            go.Bar(
                x=[df.time[i]],
                y=[elevation-90],
                marker=dict(
                    color='green',
                    line=dict(color='green', width=3),
                    opacity=df['sleety_score'][i] / max(df['sleety_score'])  # Normalize to [0,1]
                ),
                showlegend=False,
    #             hoverinfo='none'
            ),
            row=5,  # Change this to the row number where you want the bars
            col=1
        )

    # Add horizontal lines at 1500m, 2000m, and 2500m to the first subplot
    fig.add_shape(type="line", x0=smoothed_df.columns[1], y0=resort.base, x1=smoothed_df.columns[-1], y1=resort.base, line=dict(color="Black", width=2, dash="dash"), row=2, col=1)
    fig.add_shape(type="line", x0=smoothed_df.columns[1], y0=resort.mid, x1=smoothed_df.columns[-1], y1=resort.mid, line=dict(color="Black", width=2, dash="dash"), row=2, col=1)
    fig.add_shape(type="line", x0=smoothed_df.columns[1], y0=resort.top, x1=smoothed_df.columns[-1], y1=resort.top, line=dict(color="Black", width=2, dash="dash"), row=2, col=1)

    # Set labels and title
    fig.update_layout(
        title='Mid Graphs',
        xaxis_title='Datetime',
        autosize=False,
        width=1200,
        height=900,
        yaxis=dict(),
        showlegend=False,
    )

    fig.update_coloraxes(showscale=False) 
    # fig.update_yaxes(showticklabels=False)

    # Show the plot
    plot_mid_c = plot(fig, output_type='div', include_plotlyjs=False, link_text='', show_link=False)

    # ############################################
    # #creating graphs for top elevation in Celcius
    # ############################################

    df['snowmelt'] = df.apply(lambda row: estimate_snowmelt(row['temp_top'], row['only_rain_top']), axis=1)
    top_hourly_snowfall = df['top_snowfall_total']
    top_hourly_rainfall = df['only_rain_top']
    top_cumulative_snowfall = df['top_cumulative_snowfall']
    top_melt_adjusted_snowpack = calculate_melt_adjusted_top_snowpack(df)
    wind_speed_top = df['wind_speed_top']
    top_wind_gusts = df['wind_gusts_top']


    elevation = 100  # Change this to your desired elevation

    fig = make_subplots(
        rows=5, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.02,
        subplot_titles=("Sunshine vs. Cloud", "Temperatures", "Rain vs. Snow", "Wind", "Sleety Index"),
        row_heights=[0.45, 0.85, 0.35, 0.25, 0.1]  # Adjust these values as needed
    )

    fig.add_trace(
        go.Scatter(
            x=df.time,
            y=[50]*len(df),  # Baseline at y=100
            mode='lines',
            line=dict(width=0),  # Invisible line
            showlegend=False,
        )
    )

    # Create an area trace for cloud cover
    fig.add_trace(
        go.Scatter(
            x=df.time,
            y=df['cloud_cover'] + elevation-50,  # Varying thickness over time, elevated
            fill='tonexty',  # Fill to next y-value
            fillcolor='rgba(128, 128, 128, 0.5)',  # Semi-transparent grey
            line=dict(color='rgba(128, 128, 128, 1)'),  # Grey line
            line_shape='spline',  # This line makes the line rounded
            name='Cloud Cover',
            showlegend=False,
        )
    )
    # Assuming df['direct_radiation'] contains the direct radiation data
# Assuming df['direct_radiation'] contains the direct radiation data
    for i in range(len(df)):
        fig.add_trace(
            go.Bar(
                x=[df.time[i]],
                y=[elevation-50],
                marker=dict(
                    color='yellow',
                    line=dict(color='yellow', width=3),
                    opacity=max(0, min(df['direct_radiation'][i] / max(df['direct_radiation']), 1))  # Normalize to [0,1]
                ),
                showlegend=False,
                # hoverinfo='none'
            ),
            row=1,  # Change this to the row number where you want the bars
            col=1
        )


    fig.add_trace(
        go.Heatmap(
            z=data_array,
            x=smoothed_df.columns,
            y=heights,
            showscale=False,
            colorscale='balance',
            zmid=0,
            showlegend=False,
            colorbar=dict(showticklabels=False) 
        ),
        row=2, col=1
    )
    # Add the bar plot for mid_hourly_snowfall to the second subplot
    fig.add_trace(
        go.Bar(
            x=df.time,
            y=top_hourly_snowfall,
            name='Top Hourly Snowfall',
            marker=dict(color='blue'),
            showlegend=False
        ),
        row=3, col=1
    )

    # Add the bar plot for mid_hourly_rainfall to the third subplot
    fig.add_trace(
        go.Bar(
            x=df.time,
            y=top_hourly_rainfall,
            name='Top Hourly Rainfall',
            marker=dict(color='red'),
            showlegend=False
        ),
        row=3, col=1
    )
    # Add the line plot for mid_cumulative_snowfall to the third subplot
    fig.add_trace(
        go.Line(
            x=df.time,
            y=top_melt_adjusted_snowpack,
            name='Top Cumulative Snowfall',
            marker=dict(color='blue'),
            showlegend=False
        ),
        row=3, col=1
    )

    # Smooth the data
    smooth_window = 5
    wind_speed_smooth = np.convolve(wind_speed_top, np.ones(smooth_window)/smooth_window, mode='valid')
    top_wind_gusts_smooth = np.convolve(top_wind_gusts, np.ones(smooth_window)/smooth_window, mode='valid')

    # Ensure gusts line does not go below wind speed line
    top_wind_gusts_smooth = np.maximum(top_wind_gusts_smooth, wind_speed_smooth)

    # Add the scatter plot for mid_wind_speed with a central line
    fig.add_trace(
        go.Scatter(
            x=df['time'][smooth_window//2:-smooth_window//2+1],
            y=wind_speed_smooth,
            mode='lines',
            name='top Wind Speed',
            line=dict(color='green', shape='spline'),
            showlegend=False
        ),
        row=4, col=1
    )

    # Add the scatter plot for mid_wind_gusts with confidence intervals
    fig.add_trace(
        go.Scatter(
            x=df['time'][smooth_window//2:-smooth_window//2+1],
            y=top_wind_gusts_smooth,
            mode='lines',
            name='Top Wind Gusts',
            line=dict(color='purple', shape='spline'),
            fill='tonexty',  # Fill to the line below (gusts line)
            fillcolor='rgba(128,0,128,0.3)',  # Adjust color and opacity as needed
            showlegend=False
        ),
        row=4, col=1
    )
            
    def calculate_conditions(row):
            
            score = 0

            # Sunny weather
            if row['direct_radiation'] > 50:
                score += 2
                
            # Cloud Cover
            if row['cloud_cover'] <90:
                score += 2

            # Feelslike temp 
            if row['feelslike_top_min'] > -10:
                score += 3

            # Low wind speed
            if row['wind_speed_top'] < 15:  # Adjust the threshold as needed
                score += 2

            # Significant fresh snow in the last 24 hours
            if row['top_cumulative_snowfall'] > 20:  # Adjust the threshold as needed
                score += 3

            return score
        
    # Add a new column 'sleety_score' to your DataFrame
    df['sleety_score'] = df.apply(calculate_conditions, axis=1)

    for i in range(len(df)):
        fig.add_trace(
            go.Bar(
                x=[df.time[i]],
                y=[elevation-90],
                marker=dict(
                    color='green',
                    line=dict(color='green', width=3),
                    opacity=df['sleety_score'][i] / max(df['sleety_score'])  # Normalize to [0,1]
                ),
                showlegend=False,
    #             hoverinfo='none'
            ),
            row=5,  # Change this to the row number where you want the bars
            col=1
        )

    # Add horizontal lines at 1500m, 2000m, and 2500m to the first subplot
    fig.add_shape(type="line", x0=smoothed_df.columns[1], y0=resort.base, x1=smoothed_df.columns[-1], y1=resort.base, line=dict(color="Black", width=2, dash="dash"), row=2, col=1)
    fig.add_shape(type="line", x0=smoothed_df.columns[1], y0=resort.mid, x1=smoothed_df.columns[-1], y1=resort.mid, line=dict(color="Black", width=2, dash="dash"), row=2, col=1)
    fig.add_shape(type="line", x0=smoothed_df.columns[1], y0=resort.top, x1=smoothed_df.columns[-1], y1=resort.top, line=dict(color="Black", width=2, dash="dash"), row=2, col=1)

    # Set labels and title
    fig.update_layout(
        title='Top Graphs',
        xaxis_title='Datetime',
        autosize=False,
        width=1200,
        height=900,
        yaxis=dict(),
        showlegend=False,
    )

    fig.update_coloraxes(showscale=False) 
    # fig.update_yaxes(showticklabels=False)

    # Show the plot
    plot_top_c = plot(fig, output_type='div', include_plotlyjs=False, link_text='', show_link=False)

    if selected_resort is not None:
        context = {
            'selected_resort':selected_resort,
            'df': df.to_html(),
            'plot_base_c': plot_base_c,
            'plot_mid_c': plot_mid_c,
            'plot_top_c': plot_top_c,
            # Add other context variables as needed
        }
        return render(request, 'graphs.html', context)
    else:
        # Handle the case where 'selected_resort_name' is not in the session
        return HttpResponse("Error: 'selected_resort_name' not found in session.")

def resort_list(request):
    country = request.GET.get('country')
    resort_list = Resort.objects.filter(country=country)
    context = {'resort_list': resort_list}
    return render(request, 'partials/modules.html', context)

def resorts(request):
    country = request.GET.get('country')
    resorts = Resort.objects.filter(country=country)
    context = {'resorts':resorts}
    return render(request, 'partials/resort_names.html', context)

def about(request):
    return render(request, 'about.html', {})



