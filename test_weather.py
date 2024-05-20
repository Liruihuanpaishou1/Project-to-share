from app import app
import subprocess
from datetime import datetime, timedelta
import os, time, requests, base64, dotenv, pytest, sys

@pytest.fixture(autouse=True, scope='session')
def pytest_sessionstart():
  dotenv.load_dotenv()

@pytest.fixture(scope='module')
def start_microservice():
  host, port = os.getenv('COURSES_MICROSERVICE_URL').split("/")[2].split(":")

  microservice = subprocess.Popen([sys.executable, "-m", "flask", "run", "--host", host, "--port", port], cwd="courses_microservice")
  time.sleep(2) #wait a bit for the microservice to start
  yield
  microservice.terminate()

@pytest.fixture(scope='module')
def test_client():
  flask_app = app
  with flask_app.test_client() as testing_client:
    # Establish an application context
    with flask_app.app_context():
      yield testing_client

def check_course(client, course, code=200, limit=None):
  assert cache_used, "cache must work before other tests will run"

  r = client.post('/weather', data={"course": course}, content_type='multipart/form-data')

  assert r.status_code == code
  
  check = requests.post('http://sp24-cs340-adm.cs.illinois.edu:3407/check/'+course, json=r.json).json()
  if 'error' in check:
    assert check['error'], 'Expected an error message'
    return
  
  for k in check:
    if k == 'unexpected keys':
      assert len(check['unexpected keys']) == 0, f'did not expect JSON key {" and ".join(check["unexpected keys"])} for course {course}'
    else:
      if not limit or k in limit:
        assert check[k], f'Incorrect or missing {k} entry ({r.json.get(k)}) for course {course}'
  



def get_cached_data(client):
  r = client.get('/weatherCache')
  assert(r.status_code == 200), f"Cache is not initialized"
  return r.json

def check_cached_weather(client, isEmpty = False): 
  data = get_cached_data(client)
  if isEmpty:
    assert(len(data) == 0), f"Cache is not empty"
  else:
    assert(len(data) > 0), f"Cache is empty"

def test_at_start_cache_is_empty(start_microservice, test_client):
  check_cached_weather(test_client, isEmpty = True)

cache_used = True
def test_cache_used(start_microservice, test_client):
  global cache_used
  cache_used = False
  
  r1 = test_client.post('/weather', data={"course": 'CS 340'}, content_type='multipart/form-data')

  oldg,oldp = requests.get, requests.post
  def newg(*args, **kargs):
    if any('weather.gov' in str(_).lower() for _ in args):
      assert False, "Should have served request from cache"
    if any('weather.gov' in str(_).lower() for _ in kargs.values()):
      assert False, "Should have served request from cache"
    return oldg(*args, **kargs)
  def newp(*args, **kargs):
    if any('weather.gov' in str(_).lower() for _ in args):
      assert False, "Should have served request from cache"
    if any('weather.gov' in str(_).lower() for _ in kargs.values()):
      assert False, "Should have served request from cache"
    return oldp(*args, **kargs)
  requests.get = newg
  requests.post = newp

  r2 = test_client.post('/weather', data={"course": 'CS 340'}, content_type='multipart/form-data')
  requests.get, requests.post = oldg, oldp
  assert r1.text == r2.text, "Cached and uncached replies should be indistinguishable"
  cache_used = True
  

def test_valid_cache_implementation(start_microservice, test_client):
  for i in range(10):
    check_course(test_client, "CS 107")
  check_cached_weather(test_client)

def test_our_course(start_microservice, test_client):
  check_course(test_client, "CS 340")
  
  
# def test_valid_course_with_space_upper(start_microservice,test_client):
  # check_course(test_client, "CS 107")
  # check_course(test_client, "CS 101")

# def test_valid_course_with_space_lower(start_microservice,test_client):
  # check_course(test_client, "cs 340")
  # check_course(test_client, "cs 101")

# def test_valid_course_without_space_lower(start_microservice,test_client):
  # check_course(test_client, "cs374")
  # check_course(test_client, "cs101")

# def test_valid_course_without_space_upper(start_microservice,test_client):
  # check_course(test_client, "CS450")
  # check_course(test_client, "CS101")

def test_invalid_course_correct_format(start_microservice,test_client):
  check_course(test_client, "CSS 12345", 400)

def test_invalid_course_incorrect_format_1(start_microservice,test_client):
  check_course(test_client, "CSS", 400)
def test_invalid_course_incorrect_format_2(start_microservice,test_client):
  check_course(test_client, "12345", 400)
def test_invalid_course_incorrect_format_3(start_microservice,test_client):
  check_course(test_client, "this is not a course and should fail", 400)
def test_invalid_course_incorrect_format_4(start_microservice,test_client):
  check_course(test_client, "this should also fail", 400)

# def test_once_a_week_course_1(start_microservice,test_client):
  # check_course(test_client, "CS 105")

# def test_once_a_week_course_2(start_microservice,test_client):
  # check_course(test_client, "CS 124")

# def test_multiple_times_a_week_course_1(start_microservice,test_client):
  # check_course(test_client, "CS 446")

# def test_multiple_times_a_week_course_2(start_microservice,test_client):
  # check_course(test_client, "CS 225")

# def test_unavailable(start_microservice,test_client):
  # check_course(test_client, "TEST 999")

# def test_valid_course_case_insensitive(start_microservice,test_client):
  # check_course(test_client, "cS374")
  # check_course(test_client, "Cs101")

def test_blank_course_1(start_microservice,test_client):
  check_course(test_client, " ", 400)
def test_blank_course_2(start_microservice,test_client):
  check_course(test_client, "   ", 400)
def test_blank_course_3(start_microservice,test_client):
  check_course(test_client, "", 400)


checked_courses = {}
def make_several_tests(course):
  global checked_courses
  def fmaker(k):
    def f(start_microservice,test_client):
      if course not in checked_courses:
        assert cache_used, "cache must work before other tests will run"
        r = test_client.post('/weather', data={"course": course}, content_type='multipart/form-data')
        assert r.status_code == 200
        checked_courses[course] = requests.post('http://sp24-cs340-adm.cs.illinois.edu:3407/check/'+course, json=r.json).json()
      check = checked_courses[course]
      assert check[k], f'Incorrect or missing {k} entry for course {course}'
    return f
  for k in 'course','nextCourseMeeting','forecastTime','temperature','shortForecast':
    globals()['test_course_'+course.replace(' ','_')+'_'+k] = fmaker(k)



make_several_tests('CS 101')
make_several_tests('CS 105')
make_several_tests('CS 107')
make_several_tests('CS 124')
make_several_tests('Cs 225')
make_several_tests('cS 233')
make_several_tests('Cs374')
make_several_tests('cS173')
make_several_tests('cs128')
make_several_tests('CS340')
make_several_tests('TEST 999')

