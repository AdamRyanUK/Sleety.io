from django.shortcuts import render
import json
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
from django.http import HttpResponseServerError
import pandas as pd
from .forms import ResortForm
from .Icons import weather_icons, weather_icons_night
from .sleety_score import calculate_conditions_base, calculate_conditions_mid, calculate_conditions_top

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

from datetime import datetime

def categorize_time(hour):
    if 0 <= hour < 6:
        return 'night'
    elif 6 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'afternoon'
    else:
        return 'evening'
    
def resorts(request):
    country = request.GET.get('country')
    resorts = Resort.objects.filter(country=country)
    context = {'resorts':resorts}
    return render(request, 'partials/resort_names.html', context)



def forecast(request):
    # Check if the forecast data is already cached
    cached_forecast = cache.get('forecast_data')

    # If not cached, make the API call and cache the data
    if not cached_forecast:
        resorts = Resort.objects.all()

        latitudes = [resort.lat for resort in resorts]
        longitudes = [resort.lon for resort in resorts]
        timezones = [resort.timezone for resort in resorts]
        base = [resort.base for resort in resorts]
        mid = [resort.mid for resort in resorts]
        top = [resort.top for resort in resorts]

        lat_str = ",".join(map(str, latitudes))
        lon_str = ",".join(map(str, longitudes))
        tz_str = ",".join(map(str, timezones))
        base_str = ",".join(map(str, base))

        api_request = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&forecast_days=10&hourly=temperature_2m,geopotential_height_1000hPa,geopotential_height_1000hPa,temperature_1000hPa,geopotential_height_850hPa,precipitation,weather_code,temperature_850hPa,windspeed_850hPa,wind_speed_10m,wind_gusts_10m,winddirection_850hPa,freezing_level_height&timezone={tz_str}&elevation={base_str}&models=gfs_seamless"                                      
        )
        api = json.loads(api_request.content)

        # Cache the API response for an hour (adjust as needed)
        cache.set('forecast_data', api, 3 * 60 * 60)

        # Use the cached forecast data
        cached_forecast = api

    if request.method == 'POST':
        selected_resort_name = request.POST.get('resort')

        # Check if the default option is selected
        if selected_resort_name == 'Select Resort':
            # Handle this case, e.g., redirect with an error message
            return render(request, 'forecast.html', {'error_message': 'Please select a valid resort'})

    elif request.method == 'GET':
        selected_resort_name = request.GET.get('resort')

    all_resorts= Resort.objects.all()

    # Filter the resorts list to include only the selected resort
    selected_resort = all_resorts.filter(name=selected_resort_name).first()

# Check if the selected resort exists
    if selected_resort is None:
        # Handle the case when the selected resort is not found
        return render(request, 'forecast.html', {'error_message': 'Selected resort not found'})

    # Define resorts here as well
    resorts= Resort.objects.all()
    base = selected_resort.base
    mid = selected_resort.mid
    top = selected_resort.top

    # Find the index of the selected resort in the list of resorts
    selected_resort_index = [resort.name for resort in resorts].index(selected_resort_name)

    temperature_icons = {}
    for temperature in range(-45, 45):
        temperature_icons[temperature] = f'/static/images/temperatures_celcius/{temperature}.png'

    # Add "_night" to the end of each file name for night time
    weather_icons_night = {code: path.replace('.png', '_night.png') for code, path in weather_icons.items()}
    
    # Retrieve the forecast data for the selected resort
    resort_forecast_data = cached_forecast[selected_resort_index]

    df = pd.DataFrame(resort_forecast_data['hourly'])
    df['datetime'] = pd.to_datetime(df['time'])
    df['date'] = pd.to_datetime(df['datetime']).dt.date
    df['hour'] = pd.to_datetime(df['datetime']).dt.hour
    df['height_diff'] = df['geopotential_height_850hPa'] - df['geopotential_height_1000hPa']
    df['temp_diff'] = df['temperature_850hPa'] - df['temperature_1000hPa']
    df['lapse_rate'] = (df['temp_diff']/df['height_diff'])*100
    df['temp_mid'] = df['temperature_850hPa'] + (df['lapse_rate']*((mid - df['geopotential_height_850hPa'])/100))
    df['temp_top'] = df['temperature_850hPa'] + (df['lapse_rate']*((top - df['geopotential_height_850hPa'])/100))
    df['temperature_2m'] = df['temperature_2m'].round().astype(int)

    # Apply the snowfall_amount function to create new columns for snowfall totals
    df['base_snowfall_total'] = df.apply(lambda row: round(snowfall_amount(row['temperature_2m'], row['precipitation']) * 0.0393701, 1), axis=1)
    df['mid_snowfall_total'] = df.apply(lambda row: round(snowfall_amount(row['temp_mid'], row['precipitation']) *0.0393701,1), axis=1)
    df['top_snowfall_total'] = df.apply(lambda row: round(snowfall_amount(row['temp_top'], row['precipitation']) *0.0393701,1), axis=1)
    # convert snowfall to inches and sum for period. 
    df['base_cumulative_snowfall'] = df['base_snowfall_total'].cumsum()*0.0393701
    df['mid_cumulative_snowfall'] = df['mid_snowfall_total'].cumsum()*0.0393701
    df['top_cumulative_snowfall'] = df['top_snowfall_total'].cumsum()*0.0393701
    #leave the precipitation as mm.
    df['base_rainfall_total'] = df.apply(lambda row: round(rainfall_amount(row['temperature_2m'], row['precipitation']) * 0.0393701, 1), axis=1)
    df['mid_rainfall_total'] = df.apply(lambda row: round(rainfall_amount(row['temp_mid'], row['precipitation']) * 0.0393701, 1), axis=1)
    df['top_rainfall_total'] = df.apply(lambda row: round(rainfall_amount(row['temp_top'], row['precipitation']) * 0.0393701, 1), axis=1)
    df['cumulative_precipitation'] = df['precipitation'].cumsum()/10
    #calculate how much wind is increasing with height
    df['wind_speed_gradient']= (df['windspeed_850hPa'] - df['wind_speed_10m'])/(df['geopotential_height_850hPa'] - 10)
    #work out the wind speed and gusts for mid and top, we already have base as the 10m wind speed + gusts. 
    df['wind_speed_base'] = df['wind_speed_10m'].round(1)
    df['wind_gusts_base'] = df['wind_gusts_10m'].round(1)
    df['wind_speed_mid'] = df['wind_speed_10m'] + ((mid - (base + 10)) * df['wind_speed_gradient'])
    df['wind_gusts_mid'] = df['wind_gusts_10m'] + ((mid - (base + 10)) * df['wind_speed_gradient'])
    df['wind_speed_top'] = df['wind_speed_10m'] + ((top - (base + 10)) * df['wind_speed_gradient'])
    df['wind_gusts_top'] = df['wind_gusts_10m'] + ((top - (base + 10)) * df['wind_speed_gradient'])

    # Apply the function to create a new column 'wind_chill'
    df['feelslike_base_max'] = calculate_wind_chill(df['temperature_2m'], df['wind_speed_10m']).round().astype(int)
    df['feelslike_base_min'] = calculate_wind_chill(df['temperature_2m'], df['wind_gusts_10m']).round().astype(int)

    df['feelslike_mid_max'] = calculate_wind_chill(df['temp_mid'], df['wind_speed_mid'])
    df['feelslike_mid_min'] = calculate_wind_chill(df['temp_mid'], df['wind_gusts_mid'])

    df['feelslike_top_max'] = calculate_wind_chill(df['temp_top'], df['wind_speed_top'])
    df['feelslike_top_min'] = calculate_wind_chill(df['temp_top'], df['wind_gusts_top'])

    #make copy of weather code for later use in the Sleety Index (C)
    df['weather_code_copy'] = df['weather_code']

    #add weather icon column, map the images to it. 
    df['weather_icon'] = np.where(get_time_of_day(df['hour']) == 'day',
                              df['weather_code'].map(weather_icons),
                              df['weather_code'].map(weather_icons_night).fillna('/static/images/default.png'))

    #save the generic hourly dataframe with columns of intrest. 
    df_all = df[['datetime', 'date','hour','temperature_2m', 'geopotential_height_1000hPa',
       'temperature_1000hPa', 'geopotential_height_850hPa',
       'temperature_850hPa', 'precipitation', 'weather_code',
       'windspeed_850hPa', 'wind_speed_10m', 'wind_gusts_10m', 'wind_speed_base', 'wind_gusts_base',
       'winddirection_850hPa', 'freezing_level_height', 'temp_mid',
       'temp_top', 
        'base_cumulative_snowfall',
       'mid_cumulative_snowfall', 'top_cumulative_snowfall','base_snowfall_total','mid_snowfall_total','top_snowfall_total',
       'cumulative_precipitation', 'base_rainfall_total','mid_rainfall_total','top_rainfall_total',
       'wind_speed_gradient', 'wind_speed_mid',
       'wind_gusts_mid', 'wind_speed_top', 'wind_gusts_top',
       'feelslike_base_max', 'feelslike_base_min', 'feelslike_mid_max',
       'feelslike_mid_min', 'feelslike_top_max', 'feelslike_top_min', 'weather_icon', 'weather_code_copy']]

# Apply the function to calculate base sleety index
    df_all['condition_score'] = df_all.apply(calculate_conditions_base, axis=1)
    min_score = df_all['condition_score'].min()
    max_score = df_all['condition_score'].max()

    df_all['condition_index'] = (10 * (df_all['condition_score'] - min_score) / (max_score - min_score))
    df_all['condition_index'] = df_all['condition_index'].round(1)

# Apply the function to calculate mid sleety index
    df_all['condition_score_mid'] = df_all.apply(calculate_conditions_mid, axis=1)
    min_score = df_all['condition_score_mid'].min()
    max_score = df_all['condition_score_mid'].max()

    df_all['condition_index_mid'] = (10 * (df_all['condition_score_mid'] - min_score) / (max_score - min_score))
    df_all['condition_index_mid'] = df_all['condition_index_mid'].round(1)

# Apply the function to calculate top sleety index
    df_all['condition_score_top'] = df_all.apply(calculate_conditions_top, axis=1)
    min_score = df_all['condition_score_top'].min()
    max_score = df_all['condition_score_top'].max()

    df_all['condition_index_top'] = (10 * (df_all['condition_score_top'] - min_score) / (max_score - min_score))
    df_all['condition_index_top'] = df_all['condition_index_top'].round(1)

#         def forecast(request):
#     # ... (your existing code)

#     if request.method == 'POST':
#         selected_altitude = request.POST.get('altitude', 'base')

# make sure the post is using the onclick. 

#         # Filter the DataFrame based on the selected altitude
#         if selected_altitude == 'base':
#nother line here about and if Temp = C, if F then convert to preferred units. 
#             df_selected = df[['datetime', 'date', 'hour', 'temperature_2m', 'geopotential_height_1000hPa',
#                               'temperature_1000hPa', 'geopotential_height_850hPa', 'temperature_850hPa',
#                               'precipitation', 'weather_code', 'windspeed_850hPa', 'wind_speed_10m',
#                               'wind_gusts_10m', 'winddirection_850hPa', 'freezing_level_height', 'temp_mid',
#                               'temp_top', 'base_snowfall_total', 'mid_snowfall_total', 'top_snowfall_total',
#                               'base_cumulative_snowfall', 'mid_cumulative_snowfall', 'top_cumulative_snowfall',
#                               'cumulative_precipitation', 'wind_speed_gradient', 'wind_speed_mid',
#                               'wind_gusts_mid', 'wind_speed_top', 'wind_gusts_top', 'feelslike_base_max',
#                               'feelslike_base_min', 'feelslike_mid_max', 'feelslike_mid_min', 'feelslike_top_max',
#                               'feelslike_top_min', 'weather_icon']]
#         elif selected_altitude == 'mid':
#             df_selected = df[['datetime', 'date', 'hour', 'temperature_2m', 'geopotential_height_1000hPa',
#                               'temperature_1000hPa', 'geopotential_height_850hPa', 'temperature_850hPa',
#                               'precipitation', 'weather_code', 'windspeed_850hPa', 'wind_speed_10m',
#                               'wind_gusts_10m', 'winddirection_850hPa', 'freezing_level_height', 'temp_mid',
#                               'temp_top', 'base_snowfall_total', 'mid_snowfall_total', 'top_snowfall_total',
#                               'base_cumulative_snowfall', 'mid_cumulative_snowfall', 'top_cumulative_snowfall',
#                               'cumulative_precipitation', 'wind_speed_gradient', 'wind_speed_mid',
#                               'wind_gusts_mid', 'wind_speed_top', 'wind_gusts_top', 'feelslike_base_max',
#                               'feelslike_base_min', 'feelslike_mid_max', 'feelslike_mid_min', 'feelslike_top_max',
#                               'feelslike_top_min', 'weather_icon']]
#         elif selected_altitude == 'top':
#             df_selected = df[['datetime', 'date', 'hour', 'temperature_2m', 'geopotential_height_1000hPa',
#                               'temperature_1000hPa', 'geopotential_height_850hPa', 'temperature_850hPa',
#                               'precipitation', 'weather_code', 'windspeed_850hPa', 'wind_speed_10m',
#                               'wind_gusts_10m', 'winddirection_850hPa', 'freezing_level_height', 'temp_mid',
#                               'temp_top', 'base_snowfall_total', 'mid_snowfall_total', 'top_snowfall_total',
#                               'base_cumulative_snowfall', 'mid_cumulative_snowfall', 'top_cumulative_snowfall',
#                               'cumulative_precipitation', 'wind_speed_gradient', 'wind_speed_mid',
#                               'wind_gusts_mid', 'wind_speed_top', 'wind_gusts_top', 'feelslike_base_max',
#                               'feelslike_base_min', 'feelslike_mid_max', 'feelslike_mid_min', 'feelslike_top_max',
#                               'feelslike_top_min', 'weather_icon']]
#         else:
#             # Handle invalid selections
    
    df_daily = df_all.copy()
    # cut hours into chunks and label appropriatley
    #set the date and time of day as indexes
    df_daily.set_index(['date'], inplace=True)
    #aggregate the data to a dict and specify how to do so for each one, 
    # most are mean, some median, snow is summed. 
    agg_dict_daily = {
        'temperature_2m': ['max', 'min'], 'temp_mid': ['min', 'max'], 'temp_top': ['min', 'max'],
        'wind_speed_10m': 'mean', 'wind_gusts_10m': 'max',
        'wind_speed_base':'mean','wind_gusts_base': 'max',
        'wind_speed_mid': 'mean', 'wind_gusts_mid': 'max',
        'wind_speed_top': 'mean', 'wind_gusts_top': 'max',
        'winddirection_850hPa': 'median',
        'base_snowfall_total': 'sum', 'mid_snowfall_total': 'sum', 'top_snowfall_total': 'sum',
        'base_rainfall_total': 'sum', 'mid_rainfall_total': 'sum', 'top_rainfall_total':'sum',
        'cumulative_precipitation': 'sum',  
        'feelslike_base_max': 'max', 'feelslike_base_min': 'min',
        'feelslike_mid_max': 'max', 'feelslike_mid_min': 'min',
        'feelslike_top_max': 'max', 'feelslike_top_min': 'min', 
        'condition_index': 'mean', 'condition_index_mid':'mean', 'condition_index_top': 'mean'}

    #group by first and second level of multi-index, i.e. date and time of day. 
    df_grouped_daily = df_daily.groupby(df_daily.index).agg(agg_dict_daily)
    
    #***************DAILY TEMP********************#
    #map the weather paths onto the 2m temp for base. 
    df_grouped_daily['temperature_2m_max_icons'] = df_grouped_daily[('temperature_2m', 'max')].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['temperature_2m_min_icons'] = df_grouped_daily[('temperature_2m', 'min')].map(temperature_icons).map(path_to_image_html)
    
    # Create 'base_temp_icons' column by combining the max and min icons
    df_grouped_daily['Max/Min'] = df_grouped_daily['temperature_2m_max_icons'] + " " + df_grouped_daily['temperature_2m_min_icons']
    
    # Map feels like temp icons to the right columns and then combine into a single column. 
    df_grouped_daily['feelslike_base_min_icons'] = df_grouped_daily['feelslike_base_min', 'min'].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_base_max_icons'] = df_grouped_daily['feelslike_base_max', 'max'].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['Feels Like Max/Min'] = df_grouped_daily['feelslike_base_max_icons'] + " " + df_grouped_daily['feelslike_base_min_icons']

    #Create a Base Rain/Snow Joint Precip column. 
    df_grouped_daily['Base Precipitation'] = df_grouped_daily['base_rainfall_total'].round(1).astype(str)  + "mm / " + df_grouped_daily['base_snowfall_total'].astype(str) +"'"
    
    df_grouped_daily['wind_speed_base_str'] = df_grouped_daily['wind_speed_base'].round(1).astype(str)
    df_grouped_daily['wind_gusts_base_str'] = df_grouped_daily['wind_gusts_base'].round(1).astype(str)
    df_grouped_daily['Base Winds'] = (df_grouped_daily['wind_speed_base_str'] + "kph / " + df_grouped_daily['wind_gusts_base_str']+ "kph")
    df_grouped_daily['condition_index'] = df_grouped_daily['condition_index'].round(1)
    #create a selection of columns to merge with the second data frame. 
    df_grouped_daily = df_grouped_daily[['Max/Min', 'Feels Like Max/Min', 'Base Precipitation', 'Base Winds', 'condition_index']]


    df_selected = df[['datetime', 'date','hour','temperature_2m', 'geopotential_height_1000hPa',
       'temperature_1000hPa', 'geopotential_height_850hPa',
       'temperature_850hPa', 'precipitation', 'weather_code',
       'windspeed_850hPa', 'wind_speed_10m', 'wind_gusts_10m',
       'winddirection_850hPa', 'freezing_level_height', 'temp_mid',
       'temp_top', 'base_snowfall_total', 'mid_snowfall_total',
       'top_snowfall_total', 'base_cumulative_snowfall',
       'mid_cumulative_snowfall', 'top_cumulative_snowfall',
       'cumulative_precipitation', 'wind_speed_gradient', 'wind_speed_mid',
       'wind_gusts_mid', 'wind_speed_top', 'wind_gusts_top',
       'feelslike_base_max', 'feelslike_base_min', 'feelslike_mid_max',
       'feelslike_mid_min', 'feelslike_top_max', 'feelslike_top_min', 'weather_icon', 'weather_code_copy']]
    #save a copy but for categorized time data. 
    df_hourly = df_selected.copy()

        # Convert 'hour' column to numeric
    df_hourly['hour'] = pd.to_numeric(df_hourly['hour'], errors='coerce')

    # Cut hours into chunks and label appropriately
    df_hourly['time_of_day'] = pd.cut(df_hourly['hour'], bins=[0, 6, 12, 18, 24], labels=['night', 'morning', 'afternoon', 'evening'], right=False)

    # Set the date and time of day as indexes
    df_hourly.set_index(['date', 'time_of_day'], inplace=True)

# Rest of your code...


    #aggregate the data to a dict and specify how to do so for each one, 
    # most are mean, some median, snow is summed. 
    agg_dict = {'hour': 'first','temperature_2m': 'mean', 'geopotential_height_1000hPa': 'mean', 'temperature_1000hPa': 'mean',
                'geopotential_height_850hPa': 'mean', 'temperature_850hPa': 'mean', 'precipitation': 'sum',
                'weather_code': lambda x: x.value_counts().idxmax(), 'weather_icon': lambda x: x.value_counts().idxmax(), 'windspeed_850hPa': 'mean', 'wind_speed_10m': 'mean', 'wind_gusts_10m': 'max',
                'winddirection_850hPa': 'median', 'freezing_level_height': 'mean', 'temp_mid': 'mean', 'temp_top': 'mean',
                'base_cumulative_snowfall': 'sum', 'mid_cumulative_snowfall': 'sum', 'top_cumulative_snowfall': 'sum',
                'cumulative_precipitation': 'sum', 'wind_speed_gradient': 'mean', 'wind_speed_mid': 'mean',
                'wind_gusts_mid': 'mean', 'wind_speed_top': 'mean', 'wind_gusts_top': 'mean', 'feelslike_base_max': 'mean',
                'feelslike_base_min': 'mean', 'feelslike_mid_max': 'mean', 'feelslike_mid_min': 'mean',
                'feelslike_top_max': 'mean', 'feelslike_top_min': 'mean'}

    #group by first and second level of multi-index, i.e. date and time of day. 
    df_grouped = df_hourly.groupby(level=[0, 1]).agg(agg_dict)

    # Unstack the 'time_of_day' values into separate columns
    df_unstacked = df_grouped.unstack(level=-1)

    df_unstacked = df_unstacked['weather_icon']
    # Reset the index to move 'date' and 'time_of_day' back to columns
    df_unstacked = df_unstacked.reset_index()

    df_grouped_daily.columns = df_grouped_daily.columns.droplevel(-1)
    df_grouped_daily = df_grouped_daily.reset_index()


    daily_final = df_unstacked.merge(df_grouped_daily, on = 'date', how = 'left') 
    daily_final = daily_final.set_index('date')
    daily_final.columns.name = daily_final.index.name
    daily_final.index.name = None
    
    # daily_final = pd.merge(df_unstacked, df_grouped_daily, left_index=True, right_index=True)

    hourly_html_table = df.to_html()
    daily_html_table = df_grouped_daily.to_html(escape=False)
    categorized_html_table = df_unstacked.to_html(escape=False, formatters={('morning'): path_to_image_html,
                                                                        ('afternoon'): path_to_image_html,
                                                                        ('evening'): path_to_image_html,
                                                                        ( 'night'): path_to_image_html})
    daily_final = daily_final.to_html(classes='table table-striped table-bordered table-hover table-sm', escape=False, formatters={('morning'): path_to_image_html,
                                                                        ('afternoon'): path_to_image_html,
                                                                        ('evening'): path_to_image_html,
                                                                        ( 'night'): path_to_image_html})

    context = {
        'daily_final': daily_final,
        'daily_df': daily_html_table,
        'selected_resort_name': selected_resort_name,
        'resort_forecast_data':resort_forecast_data,
        'hourly_df':hourly_html_table,
        'categorized_df':categorized_html_table,
    }

    return render(request, 'forecast.html', context)

def snowfall_amount(temperature, precipitation_amt):
    if temperature > 0:
        result = 0
    elif -2.78 <= temperature < 0:
        result = precipitation_amt * 10
    elif temperature > -6.66667:
        result = precipitation_amt * 15
    elif temperature > -9.44:
        result = precipitation_amt * 20
    elif temperature > -12.2222:
        result = precipitation_amt * 30
    elif temperature > -17.7778:
        result = precipitation_amt * 50
    else:
        result = precipitation_amt * 100

    return result

def rainfall_amount(temperature, precipitation_amt):
    if temperature > 0:
        result = precipitation_amt
    else:
        result = 0

    return result

def calculate_wind_chill(temperature, wind_speed):
    wind_chill_celsius = 13.12 + 0.6215 * temperature - 11.37 * wind_speed**0.16 + 0.3965 * temperature * wind_speed**0.16
    return wind_chill_celsius

def resort_list(request):
    country = request.GET.get('country')
    resort_list = Resort.objects.filter(country=country)
    context = {'resort_list': resort_list}
    return render(request, 'partials/modules.html', context)

def get_time_of_day(hour):
    if isinstance(hour, pd.Series):
        # If 'hour' is a Series, apply the function element-wise
        return hour.apply(get_time_of_day)
    else:
        # If 'hour' is a single value, determine the time of day
        if 6 <= hour < 18:
            return 'day'
        else:
            return 'night'

def categorize_time(hour):
    if 0 <= hour < 6:
        return 'night'
    elif 6 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'afternoon'
    else:
        return 'evening'
    
def path_to_image_html(path):
    return f'<img src="{path}" width="60" >'

def resorts(request):
    country = request.GET.get('country')
    resorts = Resort.objects.filter(country=country)
    context = {'resorts':resorts}
    return render(request, 'partials/resort_names.html', context)

def about(request):
    return render(request, 'about.html', {})