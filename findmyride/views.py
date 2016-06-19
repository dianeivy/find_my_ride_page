from flask import render_template
from findmyride import app
import pandas as pd
from flask import request
from a_Model import ModelIt
import googlemaps
from datetime import datetime, timedelta
import numpy as np
#import forecastio


gmaps = googlemaps.Client(key='AIzaSyDHyED6bTDCiE5ixR3hzkeyONB132AO64s')


def find_address(address):
    geocode_result = gmaps.geocode(address)
    starting_lat = geocode_result[0]['geometry']['location']['lat']
    starting_lon = geocode_result[0]['geometry']['location']['lng']
    return starting_lat, starting_lon


def get_weather(station_lat, station_lon, start_date):
    return 20
    # forecast = forecastio.load_forecast('3609e893742373a7f2fe1ed9464cfd8d', station_lat, station_lon, time=start_date)
    # return forecast.hourly().data[0].temperature

import sys
def find_station_id(address_latitude, address_longitude):
    station_info = pd.DataFrame.from_csv('findmyride/station_info.csv')
    station_info['distance'] = ((station_info['latitude'] - address_latitude) * 111.03) ** 2 + \
                               ((station_info['longitude'] - address_longitude) * 85.39) ** 2

    counter = 0
    nearest_stations = []
    nearest_lats = []
    nearest_lons = []
    nearest_names = []
    for station_id in station_info.sort_values('distance')['station_id']:
        station_count = pd.DataFrame.from_csv('findmyride/station_count.csv')
        check_station_status = station_count[(station_count['station_id'] == station_id)]
        if check_station_status['event_count'].values[0] > 100:
            nearest_stations.append(station_id)
            nearest_names.append(station_info[(station_info['station_id'] == station_id)]['station_name'].values[0])
            nearest_lats.append(station_info[(station_info['station_id'] == station_id)]['latitude'].values[0])
            nearest_lons.append(station_info[(station_info['station_id'] == station_id)]['longitude'].values[0])
            counter += 1
        if counter == 20:
            break
    return nearest_stations, nearest_names, nearest_lats, nearest_lons


def fix_input_dates(input_date):
    if '-' in input_date:
        delim = '-'
    else:
        delim = '/'

    month = int(input_date.split(delim)[0])
    day = int(input_date.split(delim)[1])
    tmp_yr = input_date.split(delim)[2][:2]
    if tmp_yr[0] == '2':
        yr = int(input_date.split(delim)[2][:4])
    else:
        yr = int('20' + input_date.split(delim)[2][:2])

    afternoon = input_date.split(':')[1][-2:]
    hour = int(input_date.split(':')[0][-2:])
    minute = int(input_date.split(':')[1][:2])
    if afternoon == 'pm' and hour != 12:
        hour += 12
    return datetime(yr, month, day, hour, minute)


def find_distance_to_stations(address, nearby_station_lats, nearby_station_lons, leave_time):
    walking_times = []
    for nearby_lat, nearby_lon in zip(nearby_station_lats, nearby_station_lons):
        directions_result = gmaps.distance_matrix(address,
                                                  [(nearby_lat, nearby_lon)],
                                                  mode="walking",
                                                  departure_time=datetime.now())
        walking_times.append(directions_result['rows'][0]['elements'][0]['duration']['value']) ## time in seconds
    return walking_times

def calculate_bikes(start_address, start_add_lat, start_add_lon, start_date):
    nearest_stations, nearest_names, nearest_lats, nearest_lons = find_station_id(start_add_lat, start_add_lon)
    walking_times = find_distance_to_stations(start_address, nearest_lats, nearest_lons, start_date)

    station_temp = get_weather(start_add_lat, start_add_lon, start_date)

    bike_results = [[] for i in xrange(3)]
    bike_table = []
    better_times = []
    for i in range(0, len(nearest_stations)):
        model_bike_num, better_time, better_num = ModelIt('Default', station_id=nearest_stations[i], date=start_date, temp=station_temp)
        if model_bike_num == 0:
            bike_prob = 100
        elif model_bike_num == 1:
            bike_prob = 0.8
        elif model_bike_num == 2:
            bike_prob = 0.2

        bike_results[model_bike_num].append(dict(index=nearest_stations[i],
                                                 station_name=nearest_names[i],
                                                 station_lat=nearest_lats[i],
                                                 station_lon=nearest_lons[i],
                                                 num_bikes=model_bike_num,
                                                 walking_time=walking_times[i],
                                                 bike_prob=bike_prob * i,
                                                 better_time=[start_date + timedelta(minutes=better_time) if better_time != -999 else None][0]))

        bike_table.append(dict(index=nearest_stations[i],
                               station_name=nearest_names[i],
                               walking_time=int(walking_times[i] / 60.),
                               num_bikes=model_bike_num,
                               bike_prob=bike_prob * walking_times[i],
                               better_time=[start_date + timedelta(minutes=better_time) if better_time != -999 else None][0]))
    return bike_results, bike_table

def bike_list(bike_table_results):
    all_bike_probs = [bike_table_result['bike_prob'] for bike_table_result in bike_table_results]
    top_station_indices = np.argsort(all_bike_probs)
    better_time_string = None
    if top_station_indices[0] > 2:
        if bike_table_results[0]['better_time']:
            if bike_table_results[0]['better_time'].hour > 13:
                better_hour = bike_table_results[0]['better_time'].hour - 12
                better_ampm = 'pm'
            else:
                better_hour = bike_table_results[0]['better_time'].hour
                better_ampm = 'am'
            better_time_string = "Leave at %d:%d%s to get a bike at %s" %(better_hour,
                                                                          bike_table_results[0]['better_time'].minute,
                                                                          better_ampm,
                                                                          bike_table_results[0]['station_name'])
        elif bike_table_results[1]['better_time']:
            if bike_table_results[1]['better_time'].hour > 13:
                better_hour = bike_table_results[1]['better_time'].hour - 12
                better_ampm = 'pm'
            else:
                better_hour = bike_table_results[1]['better_time'].hour
                better_ampm = 'am'
            better_time_string = "Leave at %d:%d%s to get a bike at %s" %(better_hour, bike_table_results[1]['better_time'].minute,
                                                                          better_ampm,
                                                                          bike_table_results[1]['station_name'])

        print "bts"
        print better_time_string

    return np.array(bike_table_results)[top_station_indices[:5]], better_time_string

@app.route('/input')
def cesareans_input():
    return render_template("index2.html")

@app.route('/output')
def cesareans_output():
  start_address = request.args.get('starting_address')
  starting_string = request.args.get('starting_date')
  start_add_lat, start_add_lon = find_address(start_address)

  if starting_string.lower() == 'now':
    start_date = datetime.now()
  else:
    start_date = fix_input_dates(starting_string)
  print start_date

  bike_results, bike_table = calculate_bikes(start_address, start_add_lat, start_add_lon, start_date)
  bike_table_results, better_time_string = bike_list(bike_table)

  return render_template("output4.html", bike_0_results=bike_results[0], bike_1_results=bike_results[1],
                         bike_2_results=bike_results[2], bike_table_info=bike_table_results,
                         start_lat=start_add_lat, start_lon=start_add_lon, better_string=better_time_string)
