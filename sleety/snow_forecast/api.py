from django.shortcuts import render
import json
import requests
from .models import Resort
from plotly.offline import plot
import numpy as np
from django.views.generic import ListView
from blog.models import Post
from datetime import datetime, date, time 
from django.core.cache import cache
from django.http import HttpResponseServerError
import pandas as pd
from django.shortcuts import redirect
from .forms import ResortForm
from .icons import weather_icons, weather_icons_night, temperature_icons, fahrenheit_icons, wind_direction_icons
from .sleety_score import calculate_conditions_base, calculate_conditions_mid, calculate_conditions_top
from .functions import snowfall_amount, rainfall_amount, calculate_wind_chill, resort_list, get_time_of_day, categorize_time, path_to_image_html, resorts, convert_to_fahrenheit, classify_wind_direction

def get_openweather_data(request):
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
            f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&forecast_days=10&hourly=temperature_2m,geopotential_height_1000hPa,geopotential_height_1000hPa,temperature_1000hPa,geopotential_height_850hPa,precipitation,weather_code,temperature_850hPa,windspeed_850hPa,wind_speed_10m,wind_gusts_10m,winddirection_850hPa,freezing_level_height,direct_radiation,cloud_cover&timezone={tz_str}&elevation={base_str}&models=gfs_seamless"                                      
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
    
    # Retrieve the forecast data for the selected resort
    resort_forecast_data = cached_forecast[selected_resort_index]

    #HOURLY DATAFRAME CREATION. 
    df = pd.DataFrame(resort_forecast_data['hourly'])
    df['datetime'] = pd.to_datetime(df['time'])
    df['date'] = pd.to_datetime(df['datetime']).dt.date
    df['hour'] = pd.to_datetime(df['datetime']).dt.hour
    df['height_diff'] = df['geopotential_height_850hPa'] - df['geopotential_height_1000hPa']
    df['temp_diff'] = df['temperature_850hPa'] - df['temperature_1000hPa']
    df['lapse_rate'] = (df['temp_diff']/df['height_diff'])*100
    df['temp_mid'] = (df['temperature_850hPa'] + (df['lapse_rate']*((mid - df['geopotential_height_850hPa'])/100))).round().astype(int)
    df['temp_top'] = (df['temperature_850hPa'] + (df['lapse_rate']*((top - df['geopotential_height_850hPa'])/100))).round().astype(int)
    df['temperature_2m'] = df['temperature_2m'].round().astype(int)

    #convert the hourly temps at different levels to fahrenheit
    df['temperature_2m_f'] = convert_to_fahrenheit(df['temperature_2m'])
    df['temp_mid_f'] = convert_to_fahrenheit(df['temp_mid'])
    df['temp_top_f'] = convert_to_fahrenheit(df['temp_top'])

    # Apply the snowfall_amount function to create new columns for snowfall totals
    df['base_snowfall_total'] = df.apply(lambda row: round(snowfall_amount(row['temperature_2m'], row['precipitation']) *0.0393701, 1), axis=1)
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

    # Convert the snowfall/rainfall to the bars for inclusion in the df. 
    epsilon = 1e-7 # small constant to avoid errors. 
    max_sum_base_hr = df[['base_rainfall_total', 'base_snowfall_total']].sum(axis=1).max()
    max_sum_mid_hr = df[['mid_rainfall_total', 'mid_snowfall_total']].sum(axis=1).max()
    max_sum_top_hr = df[['top_rainfall_total', 'top_snowfall_total']].sum(axis=1).max()

    df['base_precip'] = df.apply(
    lambda row: f"<div style='display: flex; flex-direction: column;'>"
                f"<div style='display: flex;'>"
                f"<div style='color: #204875; margin-right: 5px; font-weight: bold;'>{row['base_snowfall_total']}'</div>"
                f"<div style='width: {int(row['base_snowfall_total'] / (max_sum_base_hr + epsilon) * 100)}px; height: 30px; background-color: #204875; border-radius: 5px;'></div>"
                f"</div>"
                f"<div style='display: flex;'>"
                f"<div style='color: #872020; margin-right: 5px; font-weight: bold;'>{row['base_rainfall_total']}'</div>"
                f"<div style='width: {int(row['base_rainfall_total'] / (max_sum_base_hr + epsilon) * 100)}px; height: 30px; background-color: #872020; border-radius: 5px;'></div>"
                f"</div>"
                f"</div>",
    axis=1
)
    df['mid_precip'] = df.apply(
        lambda row: f"<div style='display: flex; flex-direction: column;'>"
                    f"<div style='display: flex;'>"
                    f"<div style='color: #204875; margin-right: 5px; font-weight: bold;'>{row['mid_snowfall_total']}'</div>"
                    f"<div style='width: {int(row['mid_snowfall_total'] / (max_sum_mid_hr + epsilon) * 100)}px; height: 30px; background-color: #204875; border-radius: 5px;'></div>"
                    f"</div>"
                    f"<div style='display: flex;'>"
                    f"<div style='color: #872020; margin-right: 5px; font-weight: bold;'>{row['mid_rainfall_total']}'</div>"
                    f"<div style='width: {int(row['mid_rainfall_total'] / (max_sum_mid_hr + epsilon) * 100)}px; height: 30px; background-color: #872020; border-radius: 5px;'></div>"
                    f"</div>"
                    f"</div>",
        axis=1
    )
    df['top_precip'] = df.apply(
        lambda row: f"<div style='display: flex; flex-direction: column;'>"
                    f"<div style='display: flex;'>"
                    f"<div style='color: #204875; margin-right: 5px; font-weight: bold;'>{row['top_snowfall_total']}'</div>"
                    f"<div style='width: {int(row['top_snowfall_total'] / (max_sum_top_hr + epsilon) * 100)}px; height: 30px; background-color: #204875; border-radius: 5px;'></div>"
                    f"</div>"
                    f"<div style='display: flex;'>"
                    f"<div style='color: #872020; margin-right: 5px; font-weight: bold;'>{row['top_rainfall_total']}'</div>"
                    f"<div style='width: {int(row['top_rainfall_total'] / (max_sum_top_hr + epsilon) * 100)}px; height: 30px; background-color: #872020; border-radius: 5px;'></div>"
                    f"</div>"
                    f"</div>",
        axis=1
    )
    
    #calculate how much wind is increasing with height
    df['wind_speed_gradient']= (df['windspeed_850hPa'] - df['wind_speed_10m'])/(df['geopotential_height_850hPa'] - 10)
    #work out the wind speed and gusts for mid and top, we already have base as the 10m wind speed + gusts. 
    df['wind_speed_base'] = df['wind_speed_10m'].round(1)
    df['wind_gusts_base'] = df['wind_gusts_10m'].round(1)
    df['wind_speed_mid'] = (df['wind_speed_10m'] + ((mid - (base + 10)) * df['wind_speed_gradient'])).round(1)
    df['wind_gusts_mid'] = (df['wind_gusts_10m'] + ((mid - (base + 10)) * df['wind_speed_gradient'])).round(1)
    df['wind_speed_top'] = df['wind_speed_10m'] + ((top - (base + 10)) * df['wind_speed_gradient']).round(1)
    df['wind_gusts_top'] = df['wind_gusts_10m'] + ((top - (base + 10)) * df['wind_speed_gradient']).round(1)

    #transform the hourly winds into strings to insert into hourly table. 
    df['wind_speed_base_hourly_str'] = df['wind_speed_base'].astype(str)
    df['wind_gusts_base_hourly_str'] = df['wind_gusts_base'].astype(str)
    df['wind_speed_mid_hourly_str'] = df['wind_speed_mid'].astype(str)
    df['wind_gusts_mid_hourly_str'] = df['wind_gusts_mid'].astype(str)
    df['wind_speed_top_hourly_str'] = df['wind_speed_top'].astype(str)
    df['wind_gusts_top_hourly_str'] = df['wind_gusts_top'].astype(str)

    #convert 850hPa wind directions to binned amounts for selection of image. 
    df['wind_dir_classified'] = df['winddirection_850hPa'].apply(classify_wind_direction)
    # Apply wind speed icons to the wind speeds using a function. 
    df['wind_dir_icons'] = df['wind_dir_classified'].map(wind_direction_icons).map(path_to_image_html)
    # add the icons to the wind strings. 
    df['base_winds_hourly'] = (df['wind_speed_base_hourly_str'] + "kph / " + df['wind_gusts_base_hourly_str']+ "kph " + df['wind_dir_icons'] )
    df['mid_winds_hourly'] = (df['wind_speed_mid_hourly_str'] + "kph / " + df['wind_gusts_mid_hourly_str']+ "kph " + df['wind_dir_icons'])
    df['top_winds_hourly'] = (df['wind_speed_top_hourly_str'] + "kph / " + df['wind_gusts_top_hourly_str']+ "kph " + df['wind_dir_icons'])

    # # Apply the function to create a new column 'feelslike' for celcius and fahrenheit
    df['feelslike_base_max'] = calculate_wind_chill(df['temperature_2m'], df['wind_speed_10m']).round().astype(int)
    df['feelslike_base_min'] = calculate_wind_chill(df['temperature_2m'], df['wind_gusts_10m']).round().astype(int)
    df['feelslike_base_max_f'] = convert_to_fahrenheit(df['feelslike_base_max']).round().astype(int)
    df['feelslike_base_min_f'] = convert_to_fahrenheit(df['feelslike_base_min']).round().astype(int)

    df['feelslike_mid_max'] = calculate_wind_chill(df['temp_mid'], df['wind_speed_mid']).round().astype(int)
    df['feelslike_mid_min'] = calculate_wind_chill(df['temp_mid'], df['wind_gusts_mid']).round().astype(int)
    df['feelslike_mid_max_f'] = convert_to_fahrenheit(df['feelslike_mid_max']).round().astype(int)
    df['feelslike_mid_min_f'] = convert_to_fahrenheit(df['feelslike_mid_min']).round().astype(int)

    df['feelslike_top_max'] = calculate_wind_chill(df['temp_top'], df['wind_speed_top']).round().astype(int)
    df['feelslike_top_min'] = calculate_wind_chill(df['temp_top'], df['wind_gusts_top']).round().astype(int)
    df['feelslike_top_max_f'] = convert_to_fahrenheit(df['feelslike_top_max']).round().astype(int)
    df['feelslike_top_min_f'] = convert_to_fahrenheit(df['feelslike_top_min']).round().astype(int)

    #make copy of weather code for later use in the Sleety Index (C)
    df['weather_code_copy'] = df['weather_code']

    #import weather and temp icons. 
    temperature_icons
    weather_icons_night
    fahrenheit_icons

    #add weather icon column, map the images to it. 
    df['weather_icon'] = np.where(get_time_of_day(df['hour']) == 'day',
                              df['weather_code'].map(weather_icons),
                              df['weather_code'].map(weather_icons_night).fillna('/static/images/default.png'))

    df['base_temp_hourly_icons'] = df['temperature_2m'].map(temperature_icons).map(path_to_image_html)
    df['mid_temp_hourly_icons'] = df['temp_mid'].map(temperature_icons).map(path_to_image_html)
    df['top_temp_hourly_icons'] = df['temp_top'].map(temperature_icons).map(path_to_image_html)
    df['base_temp_hourly_icons_f'] = df['temperature_2m'].map(fahrenheit_icons).map(path_to_image_html)
    df['mid_temp_hourly_icons_f'] = df['temp_mid'].map(fahrenheit_icons).map(path_to_image_html)
    df['top_temp_hourly_icons_f'] = df['temp_top'].map(fahrenheit_icons).map(path_to_image_html)

    df['base_feelslike_hourly_icons'] = df['feelslike_base_min'].map(temperature_icons).map(path_to_image_html)
    df['mid_feelslike_hourly_icons'] = df['feelslike_mid_min'].map(temperature_icons).map(path_to_image_html)
    df['top_feelslike_hourly_icons'] = df['feelslike_top_min'].map(temperature_icons).map(path_to_image_html)
    df['base_feelslike_hourly_icons_f'] = df['feelslike_base_min'].map(fahrenheit_icons).map(path_to_image_html)
    df['mid_feelslike_hourly_icons_f'] = df['feelslike_mid_min'].map(fahrenheit_icons).map(path_to_image_html)
    df['top_feelslike_hourly_icons_f'] = df['feelslike_top_min'].map(fahrenheit_icons).map(path_to_image_html)

# Apply the function to calculate base sleety index
    df['condition_score'] = df.apply(calculate_conditions_base, axis=1)
    min_score = df['condition_score'].min()
    max_score = df['condition_score'].max()

    df['condition_index_base'] = (10 * (df['condition_score'] - min_score) / (max_score - min_score))
    df['condition_index_base'] = df['condition_index_base'].round(1)

# Apply the function to calculate mid sleety index
    df['condition_score_mid'] = df.apply(calculate_conditions_mid, axis=1)
    min_score = df['condition_score_mid'].min()
    max_score = df['condition_score_mid'].max()

    df['condition_index_mid'] = (10 * (df['condition_score_mid'] - min_score) / (max_score - min_score))
    df['condition_index_mid'] = df['condition_index_mid'].round(1)

# Apply the function to calculate top sleety index
    df['condition_score_top'] = df.apply(calculate_conditions_top, axis=1)
    min_score = df['condition_score_top'].min()
    max_score = df['condition_score_top'].max()

    df['condition_index_top'] = (10 * (df['condition_score_top'] - min_score) / (max_score - min_score))
    df['condition_index_top'] = df['condition_index_top'].round(1)

    #save the generic hourly dataframe with columns of intrest. 
    df = df[[
    'datetime', 'date','hour',
    'temperature_2m', 'freezing_level_height','temperature_850hPa', 'temp_mid','temp_top',
    'base_temp_hourly_icons', 'mid_temp_hourly_icons', 'top_temp_hourly_icons',
    'temperature_2m_f', 'temp_mid_f', 'temp_top_f',
    'base_temp_hourly_icons_f', 'mid_temp_hourly_icons_f', 'top_temp_hourly_icons_f',
    'weather_code',
    'wind_speed_base', 'wind_gusts_base','wind_speed_mid','wind_gusts_mid', 'wind_speed_top', 'wind_gusts_top',
    'base_winds_hourly', 'mid_winds_hourly', 'top_winds_hourly',
    'winddirection_850hPa', 'wind_dir_icons', 'wind_speed_10m', 'wind_gusts_10m',
    'base_cumulative_snowfall', 'mid_cumulative_snowfall', 'top_cumulative_snowfall',
    'base_snowfall_total','mid_snowfall_total','top_snowfall_total',
    'precipitation','cumulative_precipitation', 
    'base_rainfall_total','mid_rainfall_total','top_rainfall_total',
    'base_precip', 'mid_precip', 'top_precip',
    'feelslike_base_max', 'feelslike_base_min', 'feelslike_mid_max', 'feelslike_mid_min', 'feelslike_top_max', 'feelslike_top_min',
    'feelslike_base_max_f', 'feelslike_base_min_f', 'feelslike_mid_max_f', 'feelslike_mid_min_f', 'feelslike_top_max_f', 'feelslike_top_min_f',
    'base_feelslike_hourly_icons', 'mid_feelslike_hourly_icons', 'top_feelslike_hourly_icons',
    'base_feelslike_hourly_icons_f', 'mid_feelslike_hourly_icons_f', 'top_feelslike_hourly_icons_f',
    'weather_icon', 'weather_code_copy',
    'condition_index_base', 'condition_index_mid', 'condition_index_top',
    'cloud_cover', 'direct_radiation'
    ]]

    #####END OF HOURLY DF###########
    #####START OF DAILY DF##########

    df_daily = df.copy()
    # cut hours into chunks and label appropriatley
    #set the date and time of day as indexes
    df_daily.set_index(['date'], inplace=True)
    #aggregate the data to a dict and specify how to do so for each one, 
    # most are mean, some median, snow is summed. 
    agg_dict_daily = {
        'temperature_2m': ['max', 'min'], 'temp_mid': ['max', 'min'], 'temp_top': ['max', 'min'],
        'temperature_2m_f': ['max', 'min'], 'temp_mid_f': ['max', 'min'], 'temp_top_f':['max','min'],
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
        'feelslike_base_max_f': 'max', 'feelslike_base_min_f':'min', 
        'feelslike_mid_max_f':'max', 'feelslike_mid_min_f':'min', 
        'feelslike_top_max_f':'max', 'feelslike_top_min_f':'min',
        'condition_index_base': 'mean', 'condition_index_mid':'mean', 'condition_index_top': 'mean'}

    #group by first and second level of multi-index, i.e. date and time of day. 
    df_grouped_daily = df_daily.groupby(df_daily.index).agg(agg_dict_daily)
    
    #***************DAILY TEMP********************#

    #map the weather paths onto the 2m temp for celcius
    df_grouped_daily['temperature_2m_max_icons'] = df_grouped_daily[('temperature_2m', 'max')].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['temperature_2m_min_icons'] = df_grouped_daily[('temperature_2m', 'min')].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['temperature_mid_max_icons'] = df_grouped_daily[('temp_mid', 'max')].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['temperature_mid_min_icons'] = df_grouped_daily[('temp_mid', 'min')].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['temperature_top_max_icons'] = df_grouped_daily[('temp_top', 'max')].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['temperature_top_min_icons'] = df_grouped_daily[('temp_top', 'min')].map(temperature_icons).map(path_to_image_html)

    # map weather icons onto fahrenheit data. 
    df_grouped_daily['temperature_2m_max_f_icons'] = df_grouped_daily[('temperature_2m', 'max')].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['temperature_2m_min_f_icons'] = df_grouped_daily[('temperature_2m', 'min')].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['temperature_mid_max_f_icons'] = df_grouped_daily[('temp_mid', 'max')].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['temperature_mid_min_f_icons'] = df_grouped_daily[('temp_mid', 'min')].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['temperature_top_max_f_icons'] = df_grouped_daily[('temp_top', 'max')].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['temperature_top_min_f_icons'] = df_grouped_daily[('temp_top', 'min')].map(fahrenheit_icons).map(path_to_image_html)

    # Combining the max and min icons into a single column for each height.
    df_grouped_daily['base_temp'] = df_grouped_daily['temperature_2m_max_icons'] + " " + df_grouped_daily['temperature_2m_min_icons']
    df_grouped_daily['mid_temp'] = df_grouped_daily['temperature_mid_max_icons'] + " " + df_grouped_daily['temperature_mid_min_icons']
    df_grouped_daily['top_temp'] = df_grouped_daily['temperature_top_max_icons'] + " " + df_grouped_daily['temperature_top_min_icons']

    #do the same for the fahrenheit column for each height. 
    df_grouped_daily['base_temp_f'] = df_grouped_daily['temperature_2m_max_f_icons'] + " " + df_grouped_daily['temperature_2m_min_f_icons']
    df_grouped_daily['mid_temp_f'] = df_grouped_daily['temperature_mid_max_f_icons'] + " " + df_grouped_daily['temperature_mid_min_f_icons']
    df_grouped_daily['top_temp_f'] = df_grouped_daily['temperature_top_max_f_icons'] + " " + df_grouped_daily['temperature_top_min_f_icons']

    # Map feels like temp icons to the right columns and then combine into a single column. 
    df_grouped_daily['feelslike_base_min_icons'] = df_grouped_daily['feelslike_base_min', 'min'].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_base_max_icons'] = df_grouped_daily['feelslike_base_max', 'max'].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_mid_min_icons'] = df_grouped_daily['feelslike_mid_min', 'min'].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_mid_max_icons'] = df_grouped_daily['feelslike_mid_max', 'max'].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_top_min_icons'] = df_grouped_daily['feelslike_top_min', 'min'].map(temperature_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_top_max_icons'] = df_grouped_daily['feelslike_top_max', 'max'].map(temperature_icons).map(path_to_image_html)

    df_grouped_daily['base_feels'] = df_grouped_daily['feelslike_base_max_icons'] + " " + df_grouped_daily['feelslike_base_min_icons']
    df_grouped_daily['mid_feels'] = df_grouped_daily['feelslike_mid_max_icons'] + " " + df_grouped_daily['feelslike_mid_min_icons']
    df_grouped_daily['top_feels'] = df_grouped_daily['feelslike_top_max_icons'] + " " + df_grouped_daily['feelslike_top_min_icons']

    # Map feels like fahrenheit temp icons to the right columns and then combine into a single column. 
    df_grouped_daily['feelslike_base_min_icons_f'] = df_grouped_daily['feelslike_base_min', 'min'].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_base_max_icons_f'] = df_grouped_daily['feelslike_base_max', 'max'].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_mid_min_icons_f'] = df_grouped_daily['feelslike_mid_min', 'min'].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_mid_max_icons_f'] = df_grouped_daily['feelslike_mid_max', 'max'].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_top_min_icons_f'] = df_grouped_daily['feelslike_top_min', 'min'].map(fahrenheit_icons).map(path_to_image_html)
    df_grouped_daily['feelslike_top_max_icons_f'] = df_grouped_daily['feelslike_top_max', 'max'].map(fahrenheit_icons).map(path_to_image_html)

    df_grouped_daily['base_feels_f'] = df_grouped_daily['feelslike_base_max_icons_f'] + " " + df_grouped_daily['feelslike_base_min_icons_f']
    df_grouped_daily['mid_feels_f'] = df_grouped_daily['feelslike_mid_max_icons_f'] + " " + df_grouped_daily['feelslike_mid_min_icons_f']
    df_grouped_daily['top_feels_f'] = df_grouped_daily['feelslike_top_max_icons_f'] + " " + df_grouped_daily['feelslike_top_min_icons_f']
    
    #---------WINDSPEED FOR DAILY FINAL TABLE---------
    df_grouped_daily['wind_speed_base_str'] = df_grouped_daily['wind_speed_base'].round(1).astype(str)
    df_grouped_daily['wind_gusts_base_str'] = df_grouped_daily['wind_gusts_base'].round(1).astype(str)
    df_grouped_daily['wind_speed_mid_str'] = df_grouped_daily['wind_speed_mid'].round(1).astype(str)
    df_grouped_daily['wind_gusts_mid_str'] = df_grouped_daily['wind_gusts_mid'].round(1).astype(str)
    df_grouped_daily['wind_speed_top_str'] = df_grouped_daily['wind_speed_top'].round(1).astype(str)
    df_grouped_daily['wind_gusts_top_str'] = df_grouped_daily['wind_gusts_top'].round(1).astype(str)

    df_grouped_daily['base_winds'] = (df_grouped_daily['wind_speed_base_str'] + "kph / " + df_grouped_daily['wind_gusts_base_str']+ "kph")
    df_grouped_daily['mid_winds'] = (df_grouped_daily['wind_speed_mid_str'] + "kph / " + df_grouped_daily['wind_gusts_mid_str']+ "kph")
    df_grouped_daily['top_winds'] = (df_grouped_daily['wind_speed_top_str'] + "kph / " + df_grouped_daily['wind_gusts_top_str']+ "kph")

    #round off snowfall  totals again. 
    df_grouped_daily['base_snowfall_total'] = df_grouped_daily['base_snowfall_total'].round(1)
    df_grouped_daily['mid_snowfall_total'] = df_grouped_daily['mid_snowfall_total'].round(1)
    df_grouped_daily['top_snowfall_total'] = df_grouped_daily['top_snowfall_total'].round(1) 
    
    #round off precip totals again.
    df_grouped_daily['base_rainfall_total'] = df_grouped_daily['base_rainfall_total'].round(1)
    df_grouped_daily['mid_rainfall_total'] = df_grouped_daily['mid_rainfall_total'].round(1)
    df_grouped_daily['top_rainfall_total'] = df_grouped_daily['top_rainfall_total'].round(1)

    df_grouped_daily['base_sleety_index'] = df_grouped_daily['condition_index_base'].round(1)
    df_grouped_daily['mid_sleety_index'] = df_grouped_daily['condition_index_mid'].round(1)
    df_grouped_daily['top_sleety_index'] = df_grouped_daily['condition_index_top'].round(1)

    #export all variables to merge with second time of day df. 
    df_grouped_daily = df_grouped_daily[[
        'base_temp', 'mid_temp', 'top_temp',
        'base_temp_f', 'mid_temp_f', 'top_temp_f',
        'base_feels', 'mid_feels', 'top_feels', 
        'base_feels_f', 'mid_feels_f', 'top_feels_f', 
        'base_snowfall_total', 'mid_snowfall_total', 'top_snowfall_total',
        'base_rainfall_total', 'mid_rainfall_total', 'top_rainfall_total',
        'base_winds', 'mid_winds', 'top_winds',
        'base_sleety_index', 'mid_sleety_index', 'top_sleety_index'
        ]]

#######END OF DAILY DF#############
#######START OF CAT TIME DF#########

    df_selected = df[['datetime', 'date','hour', 'weather_code',
        'weather_icon', 'weather_code_copy']]
    #save a copy but for categorized time data. 
    df_hourly = df_selected.copy()

    # Convert 'hour' column to numeric
    df_hourly['hour'] = pd.to_numeric(df_hourly['hour'], errors='coerce')

    # Cut hours into chunks and label appropriately
    df_hourly['time_of_day'] = pd.cut(df_hourly['hour'], bins=[0, 6, 12, 18, 24], labels=['night', 'morning', 'afternoon', 'evening'], right=False)

    # Set the date and time of day as indexes
    df_hourly.set_index(['date', 'time_of_day'], inplace=True)

    #aggregate the data to a dict and specify how to do so for each one, 
    # most are mean, some median, snow is summed. 
    agg_dict = {
                'hour': 'first',
                'weather_code': lambda x: x.value_counts().idxmax(), 
                'weather_icon': lambda x: x.value_counts().idxmax()
                }

    #group by first and second level of multi-index, i.e. date and time of day. 
    df_grouped = df_hourly.groupby(level=[0, 1]).agg(agg_dict)

    # Unstack the 'time_of_day' values into separate columns
    df_unstacked = df_grouped.unstack(level=-1)

    df_unstacked = df_unstacked['weather_icon']
    # Reset the index to move 'date' and 'time_of_day' back to columns
    df_unstacked = df_unstacked.reset_index()

    df_grouped_daily.columns = df_grouped_daily.columns.droplevel(-1)
    
    cat_time_df = df_grouped_daily.reset_index()
    
    ##########END OF CAT_TIME DF#########
    ##########START OF MERGING DAILY & CAT TIME######

    daily_final = df_unstacked.merge(cat_time_df, on = 'date', how = 'left') 
    daily_final = daily_final.set_index('date')
    daily_final.columns.name = daily_final.index.name
    daily_final.index.name = None

    #######FORMATTING THE SNOW AND PRECIP AMOUNTS ##################
    max_sum_base = daily_final[['base_rainfall_total', 'base_snowfall_total']].sum(axis=1).max()
    max_sum_mid = daily_final[['mid_rainfall_total', 'mid_snowfall_total']].sum(axis=1).max()
    max_sum_top = daily_final[['top_rainfall_total', 'top_snowfall_total']].sum(axis=1).max()

    epsilon = 1e-7  # small constant

    daily_final['base_precip'] = daily_final.apply(
        lambda row: f"<div style='display: flex; flex-direction: column;'>"
                    f"<div style='display: flex;'>"
                    f"<div style='color: #204875; margin-right: 5px; font-weight: bold;'>{row['base_snowfall_total']}'</div>"
                    f"<div style='width: {int(row['base_snowfall_total'] / (max_sum_base + epsilon) * 100)}px; height: 30px; background-color: #204875; border-radius: 5px;'></div>"
                    f"</div>"
                    f"<div style='display: flex;'>"
                    f"<div style='color: #872020; margin-right: 5px; font-weight: bold;'>{row['base_rainfall_total']}'</div>"
                    f"<div style='width: {int(row['base_rainfall_total'] / (max_sum_base + epsilon) * 100)}px; height: 30px; background-color: #872020; border-radius: 5px;'></div>"
                    f"</div>"
                    f"</div>",
        axis=1
    )
    # Do the same for 'mid_precip' and 'top_precip'

    daily_final['mid_precip'] = daily_final.apply(
    lambda row: f"<div style='display: flex; flex-direction: column;'>"
                f"<div style='display: flex;'>"
                f"<div style='color: #204875; margin-right: 5px; font-weight: bold;'>{row['mid_snowfall_total']}'</div>"
                f"<div style='width: {int(row['mid_snowfall_total'] / (max_sum_mid + epsilon) * 100)}px; height: 30px; background-color: #204875; border-radius: 5px;'></div>"
                f"</div>"
                f"<div style='display: flex;'>"
                f"<div style='color: #872020; margin-right: 5px; font-weight: bold;'>{row['mid_rainfall_total']}'</div>"
                f"<div style='width: {int(row['mid_rainfall_total'] / (max_sum_mid + epsilon) * 100)}px; height: 30px; background-color: #872020; border-radius: 5px;'></div>"
                f"</div>"
                f"</div>",
    axis=1
)
    daily_final['top_precip'] = daily_final.apply(
    lambda row: f"<div style='display: flex; flex-direction: column;'>"
                f"<div style='display: flex;'>"
                f"<div style='color: #204875; margin-right: 5px; font-weight: bold;'>{row['top_snowfall_total']}'</div>"
                f"<div style='width: {int(row['top_snowfall_total'] / (max_sum_top + epsilon) * 100)}px; height: 30px; background-color: #204875; border-radius: 5px;'></div>"
                f"</div>"
                f"<div style='display: flex;'>"
                f"<div style='color: #872020; margin-right: 5px; font-weight: bold;'>{row['top_rainfall_total']}'</div>"
                f"<div style='width: {int(row['top_rainfall_total'] / (max_sum_top + epsilon)* 100)}px; height: 30px; background-color: #872020; border-radius: 5px;'></div>"
                f"</div>"
                f"</div>",
    axis=1
)
        
    return df, daily_final, selected_resort

#so finally there are two pandas dataframes which we will import into our view and 
# df which is HOURLY and daily_final which is daily. 






   
