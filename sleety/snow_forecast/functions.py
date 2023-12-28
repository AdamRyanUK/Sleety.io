from .models import Resort
from django.shortcuts import render
import pandas as pd
import numpy as np

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
    # Replace negative wind speeds with 0.1
    wind_speed = np.where(wind_speed < 0, 0.1, wind_speed)
    
    wind_chill_celsius = 13.12 + 0.6215 * temperature - 11.37 * wind_speed**0.16 + 0.3965 * temperature * wind_speed**0.16
    return wind_chill_celsius

def classify_wind_direction(angle):
    if 345 <= angle < 22:
        result = 0
    elif 22 <= angle < 67:
        result = 45
    elif 67 <= angle < 112:
        result = 90
    elif 112 <= angle < 165:
        result = 120
    elif 165 <= angle < 202:
        result = 180
    elif 202 <= angle < 247:
        result = 225
    elif 247 <= angle < 315:
        result = 270 
    elif 315 <= angle < 345:
        result = 315
    else:
        result = None  # Handle the case where angle is not in any specified range
    
    return result

def convert_to_fahrenheit(temperature_celcius):
    temperature_fahrenheit = temperature_celcius * (9/5) + 32
    return temperature_fahrenheit

def calculate_temperature_at_height(target_height, freezing_level_height):
    # Lapse rate in degrees Celsius per meter
    
    # Calculate temperature at the given height
    if freezing_level_height >= target_height:
        temperature_at_given_height = (target_height - freezing_level_height) * -0.0065
    elif freezing_level_height <= target_height:
        temperature_at_given_height = (target_height - freezing_level_height) * +0.0065
        
    return temperature_at_given_height

def calculate_temperature_for_array(temp_1500m, height):
    if height <= 1500:
        return temp_1500m + ((1500 - height) * 0.006)
    else:
        return temp_1500m + -0.008 * (height - 1500)

def only_rain(precipitation, temperature):
    """
    Filter precipitation data for rain (temperature > 0).

    Parameters:
    - precipitation: Precipitation value
    - temperature: Temperature value

    Returns:
    - If temperature is greater than 0, return precipitation value
    - If temperature is 0 or less, return None
    """
    if temperature > 0:
        return precipitation
    else:
        return 0
    
def estimate_snowmelt(temp, rainfall, temp_scaling_factor=0.5):
    """
    Estimate snowmelt in centimeters for the next hour based on temperature and rainfall.

    Parameters:
    - temp (float): Temperature in degrees Celsius.
    - rainfall (float): Rainfall in millimeters.
    - temp_scaling_factor (float): Scaling factor to adjust temperature sensitivity.

    Returns:
    - float: Estimated snowmelt in centimeters.
    """
    # Temperature factor with scaling
    temp_factor = max(temp - 1, 0) * temp_scaling_factor

    # Rainfall factor
    rainfall_factor = rainfall / 10

    # Total snowmelt estimation
    snowmelt_estimate = temp_factor + rainfall_factor

    return snowmelt_estimate

def calculate_melt_adjusted_base_snowpack(df):
    base_cumulative_snowfall = df['base_cumulative_snowfall']
    snowmelt = df['snowmelt']

    melt_adjusted_base_snowpack = [base_cumulative_snowfall[0]]
    last_snowfall = base_cumulative_snowfall[0]
    last_snowfall_index = 0

    for i in range(1, len(base_cumulative_snowfall)):
        if snowmelt[i] > 0:  # if there is snowmelt
            last_snowfall = max(0, melt_adjusted_base_snowpack[-1] - snowmelt[i])  # decrease from the last point, but not below zero
        else:  # if there is no snowmelt
            if base_cumulative_snowfall[i] > last_snowfall:  # if there is new snowfall
                last_snowfall = melt_adjusted_base_snowpack[-1] + (base_cumulative_snowfall[i] - base_cumulative_snowfall[last_snowfall_index])  # update the last point
            last_snowfall_index = i
        melt_adjusted_base_snowpack.append(last_snowfall)
    
    return melt_adjusted_base_snowpack

def calculate_melt_adjusted_mid_snowpack(df):
    mid_cumulative_snowfall = df['mid_cumulative_snowfall']
    snowmelt = df['snowmelt']

    melt_adjusted_mid_snowpack = [mid_cumulative_snowfall[0]]
    last_snowfall = mid_cumulative_snowfall[0]
    last_snowfall_index = 0

    for i in range(1, len(mid_cumulative_snowfall)):
        if snowmelt[i] > 0:  # if there is snowmelt
            last_snowfall = max(0, melt_adjusted_mid_snowpack[-1] - snowmelt[i])  # decrease from the last point, but not below zero
        else:  # if there is no snowmelt
            if mid_cumulative_snowfall[i] > last_snowfall:  # if there is new snowfall
                last_snowfall = melt_adjusted_mid_snowpack[-1] + (mid_cumulative_snowfall[i] - mid_cumulative_snowfall[last_snowfall_index])  # update the last point
            last_snowfall_index = i
        melt_adjusted_mid_snowpack.append(last_snowfall)
    
    return melt_adjusted_mid_snowpack

def calculate_melt_adjusted_top_snowpack(df):
    top_cumulative_snowfall = df['top_cumulative_snowfall']
    snowmelt = df['snowmelt']

    melt_adjusted_top_snowpack = [top_cumulative_snowfall[0]]
    last_snowfall = top_cumulative_snowfall[0]
    last_snowfall_index = 0

    for i in range(1, len(top_cumulative_snowfall)):
        if snowmelt[i] > 0:  # if there is snowmelt
            last_snowfall = max(0, melt_adjusted_top_snowpack[-1] - snowmelt[i])  # decrease from the last point, but not below zero
        else:  # if there is no snowmelt
            if top_cumulative_snowfall[i] > last_snowfall:  # if there is new snowfall
                last_snowfall = melt_adjusted_top_snowpack[-1] + (top_cumulative_snowfall[i] - top_cumulative_snowfall[last_snowfall_index])  # update the last point
            last_snowfall_index = i
        melt_adjusted_top_snowpack.append(last_snowfall)
    
    return melt_adjusted_top_snowpack

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

