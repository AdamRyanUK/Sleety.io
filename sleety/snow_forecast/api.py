from django.shortcuts import render
import json
import requests
import plotly.graph_objs as go
from .models import Resort

def home(request):
    resorts = Resort.objects.all()

    # Extract latitude and longitude values into separate lists
    names = [resort.name for resort in resorts]
    latitudes = [resort.lat for resort in resorts]
    longitudes = [resort.lon for resort in resorts]

    # Convert the lists to strings for the API request
    lat_str = ",".join(map(str, latitudes))
    lon_str = ",".join(map(str, longitudes))

    # Make the API request using the constructed URL
    api_request = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&hourly=temperature_2m")

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

    # Iterate through each item in the JSON data
    for resort, item in zip(resorts, api):
        # Extract time and temperature_2m data
        times = item['hourly']['time']
        temperatures_2m = item['hourly']['temperature_2m']

        # Add data to the dictionary
        resort_data[resort.name] = {'Time': times, 'Temperature_2m': temperatures_2m}

        # Create traces for each resort
    traces = []
    for resort_name, data in resort_data.items():
        trace = go.Scatter(x=data['Time'], y=data['Temperature_2m'], mode='lines', name=resort_name)
        traces.append(trace)

    layout = go.Layout(title='Temperature Variation for Resorts', xaxis=dict(title='Time'), yaxis=dict(title='Temperature_2m'))

    # Create a figure and plot it
    fig = go.Figure(data=traces, layout=layout)