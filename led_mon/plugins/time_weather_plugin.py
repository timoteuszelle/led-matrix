# Built In Dependencies
from collections import namedtuple
import requests
import os
import time
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import numpy as np
from functools import cache
from threading import Timer
import logging
from enum import Enum

# Internal dependencies
from led_mon.patterns import icons, letters_5_x_6
from led_mon import drawing

Weather = namedtuple('Weather', ['Weather', 'temp', 'wind_chill', 'wind_speed', 'wind_speed_symbol', 'wind_dir', 'temp_symbol', 'condition'])

OPENWEATHER_HOST = 'https://api.openweathermap.org'
OPEN_METEO_HOST = 'https://api.open-meteo.com'
OPEN_METEO_GEOCODE_HOST = 'https://geocoding-api.open-meteo.com'
IPIFY_HOST = 'https://api.ipify.org'
IPWHO_HOST = 'https://ipwho.is'
IPAPI_HOST = 'https://ipapi.co/json'
IPINFO_HOST = 'https://ipinfo.io/json'

log = logging.getLogger(__name__)
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

log_level = LOG_LEVELS[os.environ.get("LOG_LEVEL", "warning").lower()]
log.setLevel(log_level)

class Measures(Enum):
    TEMP_COND = 'temp_condition'
    WIND_CHILL = 'wind_chill'
    WIND = 'wind'
    



### Helper functions ###

@cache
# Cache results so we avoid exceeding the API rate limit
# No need to invalidate cache since location per given zip is fixed
def get_location_by_zip(zip_info, weather_api_key):
    zip_code, country = zip_info
    result = requests.get(
        f"{OPENWEATHER_HOST}/geo/1.0/zip?zip={zip_code},{country}&appid={weather_api_key}",
        timeout=10
    ).json()
    if not isinstance(result, dict) or "lat" not in result or "lon" not in result:
        details = result.get("message", result) if isinstance(result, dict) else result
        raise Exception(f"OpenWeather zip lookup failed: {details}")
    lat = result['lat']
    lon = result['lon']
    loc = lat, lon
    return loc

@cache
def get_location_by_zip_open_meteo(zip_info):
    zip_code, country = zip_info
    country_code = country.upper() if country else None
    params = {
        "name": str(zip_code),
        "count": 1,
        "language": "en",
        "format": "json",
    }
    if country_code:
        params["countryCode"] = country_code

    result = requests.get(
        f"{OPEN_METEO_GEOCODE_HOST}/v1/search",
        params=params,
        timeout=10
    ).json()
    results = result.get("results") if isinstance(result, dict) else None

    if not results and country_code:
        fallback_result = requests.get(
            f"{OPEN_METEO_GEOCODE_HOST}/v1/search",
            params={
                "name": f"{zip_code} {country_code}",
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=10
        ).json()
        if isinstance(fallback_result, dict):
            result = fallback_result
            results = fallback_result.get("results")

    if not isinstance(results, list) or len(results) == 0:
        details = result.get("reason", result) if isinstance(result, dict) else result
        raise Exception(f"Open-Meteo geocoding lookup failed: {details}")

    lat = results[0].get("latitude")
    lon = results[0].get("longitude")
    if lat is None or lon is None:
        raise Exception("Open-Meteo geocoding response did not include coordinates.")
    return lat, lon

@cache
# Cache results so we avoid exceeding the API rate limit
# No need to invalidate cache since location per given IP address is generally fixed
def get_location_by_ip(ip_api_key, ip):
    try:
        from iplocate import IPLocateClient
    except ImportError as e:
        raise Exception("IP-based weather lookup requires the optional `iplocate` dependency.") from e
    client = IPLocateClient(api_key=ip_api_key)
    result = client.lookup(ip)
    if result.latitude is None or result.longitude is None:
        raise Exception("IP-based location lookup returned no coordinates.")
    loc = result.latitude, result.longitude
    try:
        log.debug(f"Getting weather for {result.city}, {result.subdivision}, {result.country_code}, geo coordinates: {loc}")
    except:
        pass
    return loc

@cache
def get_location_by_ip_keyless():
    errors = []
    try:
        result = requests.get(IPWHO_HOST, timeout=10).json()
        if isinstance(result, dict) and result.get("success") is True:
            lat = result.get("latitude")
            lon = result.get("longitude")
            if lat is not None and lon is not None:
                return lat, lon
        errors.append(f"ipwho.is: {result}")
    except Exception as e:
        errors.append(f"ipwho.is: {e}")

    try:
        result = requests.get(IPAPI_HOST, timeout=10).json()
        if isinstance(result, dict):
            lat = result.get("latitude")
            lon = result.get("longitude")
            if lat is not None and lon is not None:
                return lat, lon
        errors.append(f"ipapi.co: {result}")
    except Exception as e:
        errors.append(f"ipapi.co: {e}")

    try:
        result = requests.get(IPINFO_HOST, timeout=10).json()
        if isinstance(result, dict):
            loc = result.get("loc")
            if isinstance(loc, str) and "," in loc:
                lat, lon = loc.split(",", 1)
                return float(lat), float(lon)
        errors.append(f"ipinfo.io: {result}")
    except Exception as e:
        errors.append(f"ipinfo.io: {e}")

    raise Exception(f"No location method configured and keyless IP geolocation failed ({'; '.join(errors)})")


def get_temp_symbol(units):
    return 'degC' if units == 'metric' else 'degF' if units == 'imperial' else 'degK'


def get_open_meteo_condition(weather_code):
    try:
        code = int(weather_code)
    except (TypeError, ValueError):
        return 'clouds'

    if code == 0:
        return 'clear'
    if code in [1, 2, 3]:
        return 'clouds'
    if code in [45, 48]:
        return 'mist-like'
    if code in [51, 53, 55, 56, 57]:
        return 'drizzle'
    if code in [61, 63, 65, 66, 67, 80, 81, 82]:
        return 'rain'
    if code in [71, 73, 75, 77, 85, 86]:
        return 'snow'
    if code in [95, 96, 99]:
        return 'thunderstorm'
    return 'clouds'


def apply_standard_temperature_conversion(value, units):
    if units == 'standard' and value is not None:
        return value + 273.15
    return value


def get_location(zip_info, lat_lon, ip_api_key, weather_api_key):
    if lat_lon:
        if len(lat_lon) != 2:
            raise Exception("Invalid lat_lon value. Expected [lat, lon].")
        return float(lat_lon[0]), float(lat_lon[1])

    if zip_info:
        if weather_api_key:
            try:
                return get_location_by_zip(zip_info, weather_api_key)
            except Exception as e:
                log.warning(f"OpenWeather zip geocoding failed; falling back to Open-Meteo geocoding: {e}")
        return get_location_by_zip_open_meteo(zip_info)

    if ip_api_key:
        ip = requests.get(IPIFY_HOST, timeout=10).text
        return get_location_by_ip(ip_api_key, ip)

    return get_location_by_ip_keyless()


def get_weather_fields(source, units, temp_symbol, mist_like):
    if not isinstance(source, dict):
        raise Exception(f"OpenWeather response item has unexpected type: {type(source)}")

    main = source.get("main")
    wind = source.get("wind")
    weather_data = source.get("weather")

    if not isinstance(main, dict) or not isinstance(wind, dict) or not isinstance(weather_data, list) or len(weather_data) == 0:
        raise Exception("OpenWeather response is missing one or more required fields: main, wind, weather")

    weather_head = weather_data[0]
    if not isinstance(weather_head, dict):
        raise Exception("OpenWeather response weather entry is malformed")

    temp = main.get("temp")
    feels_like = main.get("feels_like")
    wind_speed = wind.get("speed")
    wind_dir = wind.get("deg")
    condition = weather_head.get("main")

    missing_fields = []
    if temp is None: missing_fields.append("main.temp")
    if feels_like is None: missing_fields.append("main.feels_like")
    if wind_speed is None: missing_fields.append("wind.speed")
    if wind_dir is None: missing_fields.append("wind.deg")
    if condition is None: missing_fields.append("weather[0].main")
    if missing_fields:
        raise Exception(f"OpenWeather response is missing required values: {', '.join(missing_fields)}")

    wind_speed_symbol = 'mi' if units == 'imperial' else 'km'
    if condition in mist_like:
        condition = 'mist-like'

    return temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition


def get_weather_by_openweather(loc, weather_api_key, units, forecast, forecast_day, forecast_hour, mist_like):
    temp_symbol = get_temp_symbol(units)
    if forecast:
        forecast_data = requests.get(
            f"{OPENWEATHER_HOST}/data/2.5/forecast?lat={loc[0]}&lon={loc[1]}&appid={weather_api_key}&units={units}",
            timeout=10
        ).json()
        if not isinstance(forecast_data, dict) or "list" not in forecast_data or not isinstance(forecast_data["list"], list) or len(forecast_data["list"]) == 0:
            details = forecast_data.get("message", forecast_data) if isinstance(forecast_data, dict) else forecast_data
            raise Exception(f"OpenWeather forecast lookup failed: {details}")

        target_date = (datetime.now(ZoneInfo('GMT')).date() + timedelta(days=forecast_day))
        for fc in forecast_data['list']:
            dt = datetime.strptime(fc['dt_txt'], '%Y-%m-%d %H:%M:%S')
            if dt.date() == target_date and dt.hour >= forecast_hour:
                temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition = get_weather_fields(fc, units, temp_symbol, mist_like)
                # Convert m/sec to km/hr (* 3,600 / 1,000)
                if units != 'imperial':
                    wind_speed *= 3.6
                forecast_weather = Weather('Forecast', temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition)
                log.debug(f"OpenWeather forecast selected ({fc['dt_txt']}): {forecast_weather}")
                return forecast_weather

        fc = forecast_data['list'][-1]
        temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition = get_weather_fields(fc, units, temp_symbol, mist_like)
        # Convert m/sec to km/hr (* 3,600 / 1,000)
        if units != 'imperial':
            wind_speed *= 3.6
        forecast_weather = Weather('Forecast', temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition)
        log.debug(f"OpenWeather forecast fallback (latest): {forecast_weather}")
        return forecast_weather

    current = requests.get(
        f"{OPENWEATHER_HOST}/data/2.5/weather?lat={loc[0]}&lon={loc[1]}&appid={weather_api_key}&units={units}",
        timeout=10
    ).json()
    if not isinstance(current, dict) or "main" not in current:
        details = current.get("message", current) if isinstance(current, dict) else current
        raise Exception(f"OpenWeather current-weather lookup failed: {details}")

    temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition = get_weather_fields(current, units, temp_symbol, mist_like)
    # Convert m/sec to km/hr (* 3,600 / 1,000)
    if units != 'imperial':
        wind_speed *= 3.6
    weather = Weather('Current', temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition)
    log.debug(f"OpenWeather current weather: {weather}")
    return weather


def get_weather_by_open_meteo(loc, units, forecast, forecast_day, forecast_hour):
    temp_symbol = get_temp_symbol(units)
    temperature_unit = 'fahrenheit' if units == 'imperial' else 'celsius'
    wind_speed_unit = 'mph' if units == 'imperial' else 'kmh'
    wind_speed_symbol = 'mi' if units == 'imperial' else 'km'

    params = {
        "latitude": loc[0],
        "longitude": loc[1],
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
        "timezone": "GMT",
    }
    if forecast:
        params["hourly"] = "temperature_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,weather_code"
    else:
        params["current"] = "temperature_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,weather_code"

    result = requests.get(
        f"{OPEN_METEO_HOST}/v1/forecast",
        params=params,
        timeout=10
    ).json()
    if not isinstance(result, dict):
        raise Exception("Open-Meteo returned an unexpected response payload.")
    if result.get("error", False):
        raise Exception(f"Open-Meteo lookup failed: {result.get('reason', result)}")

    if forecast:
        hourly = result.get("hourly", {})
        times = hourly.get("time", [])
        if not isinstance(times, list) or len(times) == 0:
            raise Exception("Open-Meteo forecast response did not include hourly time data.")

        target_date = (datetime.now(ZoneInfo('GMT')).date() + timedelta(days=forecast_day))
        selected_idx = None
        for idx, dt_raw in enumerate(times):
            dt = datetime.fromisoformat(dt_raw)
            if dt.date() == target_date and dt.hour >= forecast_hour:
                selected_idx = idx
                break
        if selected_idx is None:
            selected_idx = len(times) - 1

        def hourly_at(key):
            values = hourly.get(key, [])
            if not isinstance(values, list) or selected_idx >= len(values):
                raise Exception(f"Open-Meteo forecast response missing hourly field: {key}")
            return values[selected_idx]

        temp = hourly_at("temperature_2m")
        feels_like = hourly_at("apparent_temperature")
        wind_speed = hourly_at("wind_speed_10m")
        wind_dir = hourly_at("wind_direction_10m")
        condition = get_open_meteo_condition(hourly_at("weather_code"))

        temp = apply_standard_temperature_conversion(temp, units)
        feels_like = apply_standard_temperature_conversion(feels_like, units)
        forecast_weather = Weather('Forecast', temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition)
        log.debug(f"Open-Meteo forecast weather: {forecast_weather}")
        return forecast_weather

    current = result.get("current", {})
    if not isinstance(current, dict):
        raise Exception("Open-Meteo current-weather response is malformed.")

    temp = current.get("temperature_2m")
    feels_like = current.get("apparent_temperature")
    wind_speed = current.get("wind_speed_10m")
    wind_dir = current.get("wind_direction_10m")
    weather_code = current.get("weather_code")
    if any(value is None for value in [temp, feels_like, wind_speed, wind_dir, weather_code]):
        raise Exception("Open-Meteo current-weather response is missing one or more required fields.")

    temp = apply_standard_temperature_conversion(temp, units)
    feels_like = apply_standard_temperature_conversion(feels_like, units)
    condition = get_open_meteo_condition(weather_code)
    weather = Weather('Current', temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition)
    log.debug(f"Open-Meteo current weather: {weather}")
    return weather

####  Monitor functions ####

class TimeMonitor:

    @staticmethod
    def get(**kwargs):
        """
        Return the current time as a tuple (HHMM, is_pm). is_pm is False if 24-hour format is used.
        Represent in local time or specified timezone, and in 24-hour or 12-hour format, based on configuration.
        """
        timezone = kwargs.get('timezone', None)
        format_24_hour = 'fmt_24_hour' in kwargs and kwargs['fmt_24_hour']
        now = datetime.now(ZoneInfo(timezone)) if timezone else datetime.now().astimezone()
        if format_24_hour:
            return (now.strftime("%H%M"), False)
        else:
            return (now.strftime("%I%M"), now.strftime("%p") == 'PM')

        
class WeatherMonitor:

    @staticmethod
    @cache
    # Cache results so we avoid exceeding the API rate limit
    def get(fs_dict):
        ip_api_key = os.environ.get("IP_LOCATE_API_KEY", None)
        weather_api_key = os.environ.get("OPENWEATHER_API_KEY", None)

        # https://ipapi.co/ip/ is a simpler location API (no api key needed for free version),
        # but it applies rate limits arbitrarily and is not be reliable for production use.
        args_dict = dict(fs_dict)
        zip_info = args_dict.get('zip_info', None)
        lat_lon = args_dict.get('lat_lon', None)
        units = args_dict.get('units', 'metric')
        forecast = args_dict.get('forecast', False)
        forecast_day = int(args_dict.get('forecast_day', 1))
        forecast_hour = int(args_dict.get('forecast_hour', 12))
        mist_like = ['Mist', 'Fog', 'Dust', 'Haze', 'Smoke', 'Squall', 'Ash', 'Sand', 'Tornado']

        try:
            if units not in ['metric', 'imperial', 'standard']:
                log.warning(f"Unrecognized weather units '{units}', defaulting to metric")
                units = 'metric'

            loc = get_location(zip_info, lat_lon, ip_api_key, weather_api_key)
            provider_errors = []

            if weather_api_key:
                try:
                    weather = get_weather_by_openweather(loc, weather_api_key, units, forecast, forecast_day, forecast_hour, mist_like)
                    log.debug("Weather provider: OpenWeather")
                    return weather
                except Exception as e:
                    provider_errors.append(f"OpenWeather: {e}")
                    log.warning(f"OpenWeather weather lookup failed; falling back to Open-Meteo: {e}")
            else:
                log.info("OPENWEATHER_API_KEY is not set; using Open-Meteo fallback provider.")

            try:
                weather = get_weather_by_open_meteo(loc, units, forecast, forecast_day, forecast_hour)
                log.debug("Weather provider: Open-Meteo")
                return weather
            except Exception as e:
                provider_errors.append(f"Open-Meteo: {e}")
                raise Exception(" | ".join(provider_errors))
        except Exception as e:
            log.error(f"Error getting weather: {e}")
            return None
        
    
time_monitor = TimeMonitor()
weather_monitor = WeatherMonitor()

#### Implement high-level drawing functions to be called by app functions below ####

draw_app = getattr(drawing, 'draw_app')

VALID_MEASURES = ['temp_condition', 'wind_chill', 'wind']

def get_next_measure(measures, duration):
    measures = list(filter(lambda m: m in VALID_MEASURES, measures))
    if len(measures) == 0:
        log.warning("No valid weather measures configured; defaulting to temp_condition")
        measures = [Measures.TEMP_COND.value]
    base_time = time.monotonic()
    measure_idx = 0
    while True:
        if time.monotonic() - base_time > duration:
            measure_idx = (measure_idx + 1) % len(measures)
            base_time = time.monotonic()
        yield measures[measure_idx]
        
def get_weather_values(weather: Weather, measure):
    if measure == Measures.TEMP_COND.value:
        return  list(str(round(weather.temp))) + [weather.temp_symbol] + [weather.condition.lower()]
    elif measure == Measures.WIND_CHILL.value:
        return ['wc', ' '] + list(str(round(weather.wind_chill))) + [weather.temp_symbol]
    elif measure == Measures.WIND.value:
        # Convert wind direction in degrees to compass direction
        dirs = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw']
        ix = round(weather.wind_dir / (360. / len(dirs)))
        wind_dir = dirs[ix % len(dirs)]
        return ['wd'] + list(str(round(weather.wind_speed))) + [weather.wind_speed_symbol] + [f"wind-{wind_dir}"]
    else:
        return "?", "?"
    
def draw_fc_period_indicator(grid, foreground_value, day, hour):
    """Draw vertical bars at the bottom left and right mafrix edges, to indicate
        the Forecast Day (left edge) and Forecast Hours (right edge) settings"""
    day = max(1, min(day, 5))
    hours = [0, 3, 6, 9, 12, 15, 18, 21]
    hours_idx = 8
    for idx, _hour in enumerate(hours):
        if hour >= _hour: hours_idx = idx
    # We count from the bottom pixel with a 1-based index
    hours_idx += 1
    day_y_vals = range(33 -day +1, 34)
    hour_y_vals = range(33 -hours_idx + 1, 34)
    grid[0, day_y_vals[0]: day_y_vals[-1]+1] = foreground_value
    grid[8, hour_y_vals[0]: hour_y_vals[-1]+1] = foreground_value
    # Draw a hash mark next to the fourht pixel from bottom if needed, for ease of reading
    grid[7, 30] = grid[8, 30]
    
@cache
def get_generator(**kwargs):
    return get_next_measure( kwargs.get('measures', [Measures.TEMP_COND.value]), kwargs.get('measures-duration', 10))
        
def draw_weather(arg, grid, foreground_value, idx, **kwargs):
    # Make kwargs hashable for caching
    fs_dict = frozenset(kwargs.items())
    weather = weather_monitor.get(fs_dict)
    if weather:
        gen = get_generator(**kwargs)
        weather_values = get_weather_values(weather, next(gen))
        draw_app(arg, grid, weather_values, foreground_value, idx)
        if kwargs.get("forecast", None):
            draw_fc_period_indicator(grid, foreground_value, kwargs.get("forecast_day", 1), kwargs.get("forecast_hour", 12))
    else:
        draw_app(arg, grid, ["?", "?"], foreground_value, idx)
        log.debug(f"Weather: No data available")

    
def draw_time(arg, grid, foreground_value, idx, **kwargs):
    hhmm, is_pm = time_monitor.get(**kwargs)
    hhmm = list(hhmm)
    time_values = hhmm[:2] + ["horiz_colon"] + hhmm[2:]
    draw_app(arg, grid, time_values, foreground_value, idx)
    if is_pm:
        grid.T[32:34, 7:9] = icons['pm_indicator'] * foreground_value


def repeat_function(interval, func, *args, **kwargs):
    def wrapper():
        func(*args, **kwargs)
        Timer(interval, wrapper).start()

    Timer(interval, wrapper).start()


# Get fresh weather data every 30 secs.
# Requests are cached between refreshes regardless of provider.
repeat_function(30, weather_monitor.get.cache_clear)

draw_chars = getattr(drawing, 'draw_chars_list')

#### Implement low-level drawing functions ####
# These functions will be dynamically imported by drawing.py and called by their corresponding app function
direct_draw_funcs = {
    "time": {
        "fn": draw_chars,
        "border": lambda *x: None  # no border
    },
    "weather": {
        "fn": draw_chars,
        "border": lambda *x: None  # no border
    }
}

# Implement app functions that call your direct_draw functions
# These functions will be dynamically imported by led_system_monitor.py. They call the direct_draw_funcs
# defined above, providing additional capabilities that can be targeted to panel quadrants

app_funcs = [
    {
        "name": "time",
        "fn": draw_time
    },
    {
        "name": "weather",
        "fn": draw_weather
    }
]

# Provide id patterns that identify your apps
# These items will be dynamically imported by drawing.py

id_patterns = {
    "time": np.concatenate((np.zeros((2,9)), letters_5_x_6["T"], np.zeros((2,9)), letters_5_x_6["I"], np.zeros((2,9)),letters_5_x_6["M"], np.zeros((2,9)), letters_5_x_6["E"], np.zeros((2,9)))).T,
    "weather_current": np.concatenate((np.zeros((2,9)), letters_5_x_6["W"], np.zeros((2,9)), letters_5_x_6["T"], np.zeros((2,9)),letters_5_x_6["R"], np.zeros((2,9)), letters_5_x_6["C"], np.zeros((2,9)))).T,
    "weather_forecast": np.concatenate((np.zeros((2,9)), letters_5_x_6["W"], np.zeros((2,9)), letters_5_x_6["T"], np.zeros((2,9)),letters_5_x_6["R"], np.zeros((2,9)), letters_5_x_6["F"], np.zeros((2,9)))).T
}
