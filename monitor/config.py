from decouple import config


FRED_API_KEY = config('FRED_API_KEY')
CHECK_INTERVAL = 10800  # 3시간 체크 
