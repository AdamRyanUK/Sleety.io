#series of dictionaries for icons used in the site. 

weather_icons = {
    0: '/static/images/clear_sky.png',
    1: '/static/images/partly_cloudy.png',
    2: '/static/images/moderately_cloudy.png',
    3: '/static/images/overcast.png',
    45: '/static/images/fog.png',
    48: '/static/images/freezing_fog.png',
    51: '/static/images/drizzle_light.png',
    53: '/static/images/drizzle_moderate.png',
    55: '/static/images/drizzle_heavy.png',
    56: '/static/images/light_freezing_drizzle.png',
    57: '/static/images/heavy_freezing_drizzle.png',
    61: '/static/images/light_rain.png',
    63: '/static/images/moderate_rain.png',
    65: '/static/images/heavy_rain.png',
    66: '/static/images/light_freezing_rain.png',
    67: '/static/images/heavy_freezing_rain.png',
    71: '/static/images/light_snow.png',
    73: '/static/images/moderate_snow.png',
    75: '/static/images/heavy_snow.png',
    77: '/static/images/snow_pellets.png',
    80: '/static/images/light_rain_shower.png',
    81: '/static/images/moderate_rain_shower.png',
    82: '/static/images/heavy_rain_shower.png',
    85: '/static/images/light_snow_shower.png',
    86: '/static/images/heavy_snow_shower.png',
    95: '/static/images/thunderstorm.png'
}

# Add "_night" to the end of each file name for night time
weather_icons_night = {code: path.replace('.png', '_night.png') for code, path in weather_icons.items()}

wind_direction_icons = {
    0: '/static/images/wind_degrees/0.png',
    45: '/static/images/wind_degrees/45.png',
    90:'/static/images/wind_degrees/90.png',
    120:'/static/images/wind_degrees/120.png',
    180:'/static/images/wind_degrees/180.png',
    225:'/static/images/wind_degrees/225.png',
    270:'/static/images/wind_degrees/270.png',
    315:'/static/images/wind_degrees/315.png',
}
temperature_icons = {}
for temperature in range(-60, 45):
    temperature_icons[temperature] = f'/static/images/temperatures_celcius/{temperature}.png'

fahrenheit_icons = {}
for temperature in range(-60, 45):
    fahrenheit_icons[temperature] = f'/static/images/temperatures_fahrenheit/{temperature}.png'

