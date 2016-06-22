import pickle
from datetime import datetime, timedelta
import numpy as np
from convertdate import holidays


def check_holiday(date):
  holiday_check = 0
  if date.month == 1 and date.day == 1: holiday_check = 1
  if date.month == 1 and date.day == 20: holiday_check = 1
  if date.month == 7 and date.day == 4: holiday_check = 1
  if date.month == 11 and date.day == 11: holiday_check = 1
  if date.month == 12 and date.day == 24: holiday_check = 1
  if date.month == 12 and date.day == 25: holiday_check = 1
  if date.month == 13 and date.day == 31: holiday_check = 1

  for holiday in [holidays.martin_luther_king_day(date.year),
                  holidays.presidents_day(date.year),
                  holidays.memorial_day(date.year),
                  holidays.labor_day(date.year),
                  holidays.columbus_day(date.year),
                  holidays.thanksgiving(date.year)]:
    holiday_check = 1
  return holiday_check

def ModelIt(fromUser='Default', station_id=[], date='', temp='', rain=0):
  with open('findmyride/fmr_models/rfc2_%d.pkl' %station_id, 'rb') as f:
    regr = pickle.load(f)

  holiday = check_holiday(date)
  minute_of_day = date.hour * 60 + date.minute
  num_extra_hours = 2
  all_minutes = np.arange(- num_extra_hours * 60, num_extra_hours * 60 + 1) + minute_of_day
  hour_features = np.array([all_minutes, np.zeros((len(all_minutes))) + date.month,
                           np.zeros((len(all_minutes))) + date.weekday(), np.zeros((len(all_minutes))) + holiday,
                           np.zeros((len(all_minutes))) + temp, np.zeros((len(all_minutes))) + rain])
  hour_predict = regr.predict(hour_features.T)
  better_time = -999

  print('checking correct minute ', all_minutes[num_extra_hours * 60 + 1], minute_of_day)

  if hour_predict[num_extra_hours * 60] < 2:
    # hour_1bike = np.array([index for index in np.arange(len(all_minutes)) if hour_predict[index] == 1]) - num_extra_hours * 60 + 1
    hour_2bike = np.array([index for index in np.arange(len(all_minutes)) if hour_predict[index] == 2]) - num_extra_hours * 60
    blah = [(index, hour_predict[index]) for index in np.arange(len(all_minutes))]
    print('h2b', hour_2bike)
    print('blah', blah)
    if len(hour_2bike) > 0:
      better_time_index = np.argmin(np.abs(hour_2bike))
      better_time = hour_2bike[better_time_index]
    # elif len(hour_1bike) > 0:
    #   better_time = hour_1bike[np.argmin(np.abs(hour_1bike))]

  if better_time != -999:
    better_time_bikes = hour_predict[better_time_index]
  else:
    better_time_bikes = -999
  print(better_time, better_time_bikes)

  return hour_predict[num_extra_hours * 60], better_time, better_time_bikes
