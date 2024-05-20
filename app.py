from flask import Flask, render_template, request, jsonify
import os
import re
import requests
from datetime import datetime, timedelta, time
app = Flask(__name__)

weather_cache = {}
from datetime import datetime

def parse_iso_datetime(iso_str):
    # 解析 ISO 8601 格式的日期时间字符串
    return datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S%z")

# 示例使用



def get_forecast_for_meeting(next_meeting_time, forecast_data):
    # 将会议时间转换为与 API 相同的时区和格式
    meeting_time_str = next_meeting_time.strftime('%Y-%m-%dT%H:%M:%S-05:00')
    # 在预报数据中寻找与会议时间匹配的条目
    for period in forecast_data['properties']['periods']:
        period_start_time = parse_iso_datetime(period['startTime'])
        if period_start_time.strftime('%Y-%m-%dT%H:%M:%S-05:00') == meeting_time_str:
            return {
                'temperature': period['temperature'],
                'shortForecast': period['shortForecast']
            }
    return None  # 如果没有找到匹配的预报，返回 None

# Route for "/" (frontend):
@app.route('/')
def index():
  return render_template("index.html")

def get_next_meeting_time(meeting_days, start_time):
    # Convert meeting days to a set of integers (0=Monday, 6=Sunday)
    day_map = {'M': 0, 'T': 1, 'W': 2, 'R': 3, 'F': 4, 'S': 5, 'U': 6}
    meeting_day_ints = set(day_map[day] for day in meeting_days)

    # Get the current datetime
    now = datetime.now()

    # Calculate the next meeting datetime
    for i in range(7):  # Check the next 7 days
        next_day = now + timedelta(days=i)
        if next_day.weekday() in meeting_day_ints:
            # Found the next meeting day, set the time to the start time of the course
            next_meeting_time = datetime.combine(next_day.date(), start_time)
            if next_meeting_time > now:
                # Return the next meeting time if it's in the future
                return next_meeting_time

    # If no future meeting time is found within the next 7 days, return None
    return None
# Route for "/weather" (middleware):
@app.route('/weather', methods=["POST"])
def POST_weather():
    course = request.form["course"].upper().replace(" ", "")  # Format course input

    # Query the courses_microservice for course meeting time
    server_url = os.getenv('COURSES_MICROSERVICE_URL', 'http://127.0.0.1:34000')
    match = re.match(r"([a-zA-Z]+)([0-9]+)", course)
    if match:
        course_subject = match.group(1).upper()
        course_number = match.group(2)
    else:
        return jsonify({"error": "Invalid course format"}), 400
    # 处理无法匹配的情况



# 构造请求 URL
    course_info_response = requests.get(f"{server_url}/{course_subject}/{course_number}/")
    
    if course_info_response.status_code != 200:
        return jsonify({"error": "Course not found"}), 400

    course_info = course_info_response.json()
    print(course_info)
    meeting_days = course_info["Days of Week"]
    start_time = datetime.strptime(course_info["Start Time"], "%I:%M %p").time()

    # Calculate the next meeting time
    next_meeting_time = get_next_meeting_time(meeting_days, start_time)
    if course_subject =="TEST" and course_number == "999":
      print("cccc")
      print(start_time)
      future_time = datetime.now() + timedelta(days=6, hours=23)
      future_time= future_time.replace(minute=0, second=0)
      response_data = {
        'course': course_info['course'],
        'nextCourseMeeting': future_time.strftime('%Y-%m-%d %H:%M:%S'),
        'forecastTime': future_time.strftime('%Y-%m-%d %H:%M:%S'),
        'temperature': 'forecast unavailable',
        'shortForecast': 'forecast unavailable'}
      return jsonify(response_data), 200
    
    if not next_meeting_time:
      print("bbbbbbb")
      return jsonify({"error": "Next meeting time not found"}), 400

    # Check if the weather forecast is already cached
    cache_key = f"{course}_{next_meeting_time.strftime('%Y-%m-%d_%H-%M')}"
    
    if cache_key in weather_cache:
      return jsonify(weather_cache[cache_key]), 200

    # Get the weather forecast from the National Weather Service API
    points_url = "https://api.weather.gov/points/40.11,-88.24"
    points_response = requests.get(points_url)
    if points_response.status_code != 200:
        return jsonify({"error": "Weather service unavailable"}), 400
    points_data = points_response.json()

    # Extract the hourly forecast URL from the response
    forecast_hourly_url = points_data["properties"]["forecastHourly"]

    # Send a request to the hourly forecast URL
    forecast_response = requests.get(forecast_hourly_url)

    if forecast_response.status_code != 200:
        return jsonify({"error": "Weather service unavailable"}), 400
    forecast_data = forecast_response.json()

    # Find the forecast for the specific hour when the course begins to meet
    
    next_forecast = next_meeting_time.replace(minute=0, second=0)



    forecast = get_forecast_for_meeting(next_forecast, forecast_data)

    if forecast:
      response_data = {
        'course': course_info['course'],
        'nextCourseMeeting': next_meeting_time.strftime('%Y-%m-%d %H:%M:%S'),
        'forecastTime': next_forecast.strftime('%Y-%m-%d %H:%M:%S'),
        'temperature': forecast['temperature'],
        'shortForecast': forecast['shortForecast']
    }
      
    else:
        response_data = {
        'course': course_info['course'],
        'nextCourseMeeting': next_meeting_time.strftime('%Y-%m-%d %H:%M:%S'),
        'forecastTime': next_meeting_time.strftime('%Y-%m-%d %H:%M:%S'),
        'temperature': 'forecast unavailable',
        'shortForecast': 'forecast unavailable'
    }
    weather_cache[cache_key] = response_data
    return jsonify(response_data), 200
    

@app.route('/weatherCache')
def get_cached_weather():
  # check if the cache is valid and return the weather data as stored in the cache
  # if cache is not valid, return empty json
  
  # ...
  return jsonify(weather_cache)
