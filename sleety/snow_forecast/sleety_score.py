#system to be improved to calculate snow conditions at the base, mid and top of resort. 

def calculate_conditions_base(row):
        
        score = 0

        # Sunny weather
        if row['weather_code_copy'] in [0, 1]:
            score += 2

        # Temperature below freezing
        if row['temperature_2m'] < 0:
            score += 3

        # Low wind speed
        if row['wind_speed_10m'] < 15:  # Adjust the threshold as needed
            score += 2

        # Significant fresh snow in the last 24 hours
        if row['base_cumulative_snowfall'] > 10:  # Adjust the threshold as needed
            score += 3

        return score

def calculate_conditions_mid(row):
        score = 0

        # Sunny weather
        if row['weather_code_copy'] in [0, 1]:
            score += 2

        # Temperature below freezing
        if row['temp_mid'] < 0:
            score += 3

        # Low wind speed
        if row['wind_speed_mid'] < 15:  # Adjust the threshold as needed
            score += 2

        # Significant fresh snow in the last 24 hours
        if row['mid_cumulative_snowfall'] > 10:  # Adjust the threshold as needed
            score += 3

        return score

def calculate_conditions_top(row):
        score = 0

        # Sunny weather
        if row['weather_code_copy'] in [0, 1]:
            score += 2

        # Temperature below freezing
        if row['temp_top'] < 0:
            score += 3

        # Low wind speed
        if row['wind_speed_top'] < 15:  # Adjust the threshold as needed
            score += 2

        # Significant fresh snow in the last 24 hours
        if row['top_cumulative_snowfall'] > 10:  # Adjust the threshold as needed
            score += 3

        return score