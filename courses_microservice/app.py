import os
import requests
import csv
from datetime import datetime

def fetchIfNotExists(url, fileName):
  """Given a URL and a file name,
  1. Checks if the file exists; if so, does nothing
  2. If the file does not exist, downloads the URL to that file
  """
  if not os.path.exists(fileName):
    print("Fetching course catalog from @wadefagen/course-catalog...")
    r = requests.get(url, stream=True)
    with open(fileName, 'wb') as fd:
      for chunk in r.iter_content(chunk_size=4096):
        fd.write(chunk)

# Ensure we have a courses dataset
fetchIfNotExists("https://raw.githubusercontent.com/wadefagen/datasets/master/course-catalog/data/2024-sp.csv", "courses.csv")

def csv2dict(fname, *columns):
  """Convert a CSV to a dict, using give set of header items as keys
  The value at each key is a list of dicts; the dicts of form {header entry:cell value}
  The dict keys are a tuple of the values in the columns with the provided header entries
  """
  result = {}
  with open(fname, "r") as fh:
    r = csv.reader(fh)
    header = r.__next__()
    for row in r:
      kv = {k:v for k,v in zip(header, row)}
      key = tuple(kv[k] for k in columns)
      result.setdefault(key,[]).append(kv)
  return result

all_courses = csv2dict("courses.csv", 'Subject', 'Number')

def build_reply(subject, number):
  result = {}

  # Cast `number` as an int and ensure `subject` is all caps:
  try:
    number = str(int(number))
  except:
    result["error"] = f"Course number `{number}` is not a number"
    status_code = 404
    return result
  subject = subject.upper()

  # A test course for the forecast unavailable states:
  if subject == "TEST" and number == '999':
    return TEST_999(result)

  # Fetch data:
  courses = [sec for sec in all_courses.get((subject,number), []) if sec['Start Time'] not in ('', 'ARRANGED')]

  if len(courses) == 0:
    # Provide an error:
    result["error"] = f"No course data available for {subject} {number}"
  else:
    # Prefer LEC sections (for courses with discussions/labs)
    course_lec = [sec for sec in courses if sec['Type Code'] == 'LEC']
    if len(course_lec) > 0:
      courses = course_lec

    # Get the first result's data:
    c = courses[0]
    result["Start Time"] = c["Start Time"]
    result["Days of Week"] = c["Days of Week"]

  return result

from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/<subject>/<number>/')
def GET_subject_number(subject, number):
  # Prep result:
  result = { "course": f"{subject} {number}" }

  # Cast `number` as an int and ensure `subject` is all caps:
  try:
    number = str(int(number))
  except:
    result["error"] = f"Course number `{number}` is not a number"
    return jsonify(result), 404
  subject = subject.upper()
  
  result.update(build_reply(subject, number))
  if 'error' in result: return jsonify(result), 404
  else: return jsonify(result), 200

# Special case for "TEST 999" course to always return a date/time
# that is 6 days and 23 hours in the future for testing:
def TEST_999(result):
  hour = datetime.now().hour
  minute = 0
  day = 0
  hour -= 1
  if hour < 0:
    hour += 24 
    day = -1
  mark = "AM"
  if hour > 12:
    hour = hour - 12
    mark = "PM"
  elif hour == 12:
    mark = "PM"
  result["Start Time"] = f"{hour}".zfill(2) + ":" + f"{minute}".zfill(2) + " " + mark
  today_of_week = datetime.today().weekday()
  six_days_later = (today_of_week + 7 + day) % 7
  if six_days_later == 0:
    result["Days of Week"] = "M"
  elif six_days_later == 1:
    result["Days of Week"] = "T"
  elif six_days_later == 2:
    result["Days of Week"] = "W"
  elif six_days_later == 3:
    result["Days of Week"] = "R"
  elif six_days_later == 4:
    result["Days of Week"] = "F"
  elif six_days_later == 5:
    result["Days of Week"] = "S"
  elif six_days_later == 6:
    result["Days of Week"] = "U"
  return result



if __name__ == '__main__':
  # run as a program; start up using the recommended port from the .env file
  import dotenv
  dotenv.load_dotenv()
  host, port = os.getenv('COURSES_MICROSERVICE_URL').split("/")[2].split(":")
  app.run(host=host, port=port)
