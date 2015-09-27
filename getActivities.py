import numpy as np
import requests
import json
import itertools
import operator
import math
import pandas as pd
from itertools import izip

#######################################################
# A few helper functions for geometry and determining #
# whether a point is in a park or sports              #
#######################################################

earth_radius = 6371.0

def great_circle_dist(a, b, unit="kilometers"):
    """
    compute great circle distance between two latitude/longitude coordinate pairs.
    Returns great cirlce distance in kilometers (default) or meters.
    https://en.wikipedia.org/wiki/Great-circle_distance
    """
    lat1, lon1 = a
    lat2, lon2 = b
    if (lat1==92) or (lat2==92):
        return -1 # invalid location gives invalid distance
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) * math.sin(dlat / 2.0) +
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
            math.sin(dlon / 2.0) * math.sin(dlon / 2.0))
    c = 2.0 * math.asin(math.sqrt(a))
    dist_km = earth_radius * c
    if unit == "kilometers":
        return dist_km
    elif unit == "meters":
        return dist_km * 1000
    else:
        raise ValueError("Unknown unit: %s" % unit)

def distance_on_earth(lat1, lon1, lat2, lon2):
    #print "starting distance comp ",lat1,lon1,lat2,lon2
    if lat1==lat2 and lon1==lon2:
        return 0.0
    
    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0
         
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
         
    # theta = longitude
    theta1 = lon1*degrees_to_radians
    theta2 = lon2*degrees_to_radians
    # Compute spherical distance from spherical coordinates.
         
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
     
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
           math.cos(phi1)*math.cos(phi2))
    #print type(cos)
    try:
        arc = math.acos( cos )
    except ValueError:
        arc = 1.0/6371/1000
    #print arc
    # Distance in meters
    return arc*6371*1000

def getBounds(coordinates):
    left = min([x for [x, y] in coordinates])
    bottom = min([y for [x, y] in coordinates])
    right = max([x for [x, y] in coordinates])
    top = max([y for [x, y] in coordinates])
    return [[bottom, left], [top, right]]
    
def pointInBounds(point, vs): # works with vs returned by getBounds
    if point[0] >= vs[0][0] and point[0] <= vs[1][0] and point[1] >= vs[0][1] and point[1] <= vs[1][1]:
        return True
    else:
        return False
        
def pointOutside(point, outside_bounds):
    b = False
    for i in range(0, len(outside_bounds)):
        current_bounds = outside_bounds[i]
        if pointInBounds(point, current_bounds) == True:
            b = True
    return b

def maxValueInDict(dict):
    return max(dict.iteritems(), key=operator.itemgetter(1))[0]
    
def separatePOI(POI, threshold=50):
    # Remove POI's that are close to one another (i.e distance between them under threshold), so we have less redundancy
    if len(POI[2]) > 0:
        b = True
        while b:
            b = False
            to_del = None
            for i in range(0, len(POI[2])):
                (lat1, lon1) = POI[2][i]
                for j in range(0, len(POI[2])):
                    if i != j:
                        (lat2, lon2) = POI[2][j]
                        dist = distance_on_earth(lat1, lon1, lat2, lon2)
                        if dist < threshold and b != True:
                            to_del = i
                            b = True
            if to_del != None:
                del(POI[2][to_del])
        if POI[0] != [None] and POI[1] != [None] and len(POI[0]) > 0 and len(POI[1]) > 0:
            b = True
            while b:
                b = False
                to_del = None
                for i in range(0, 2):
                    (lat1, lon1) = POI[i][0]
                    for j in range(0, len(POI[2])):
                        (lat2, lon2) = POI[2][j]
                        dist = distance_on_earth(lat1, lon1, lat2, lon2)
                        if dist < threshold and b != True:
                            to_del = j
                            b = True
                if to_del != None:
                    del(POI[2][to_del])
    
    return POI

def separatePOIFlat(POI, threshold=50):
    b = True
    while b:
        b = False
        to_del = None
        for i in range(0, len(POI)):
            (lat1, lon1) = POI[i]
            for j in range(0, len(POI)):
                if i != j:
                    (lat2, lon2) = POI[j]
                    dist = distance_on_earth(lat1, lon1, lat2, lon2)
                    if dist < threshold and b != True:
                        to_del = i
                        b = True
        if to_del != None:
            del(POI[to_del])
    return POI

#############################################
# Postprocess nodes data, get trips, assign #
# POI activities                            #
#############################################

def process(data_frame, stopped_thresh=0.1, poi_dwell_time=900):
    def dwell_time(stop):
        """Return time spend in a stopped location in seconds"""
        start_time, end_time = stop[3], stop[4]
        return (end_time - start_time)
    trips, stops = trip_segments(data_frame, stopped_thresh)  
    pois = filter(lambda s: dwell_time(s) >= poi_dwell_time, stops)
    return (pois, trips, stops)

def clean_data(data_frame, valid_lat_low=1.0,
               valid_lat_up=2.0,valid_lon_low=103.0,valid_lon_up=105.0,
               location_accuracy_thresh=1000):
    """Clean data frame by replacing entries with impossible values with
    'null values'. The method does not remove rows to keep the
    original data intact. Each predictor that is using the fetures is
    responsible for checking that the features are valid. Changes are
    made in-place. There is no return value.
    valid_lat_low : float value to signal a possible minimum latitude. Default 1.0
    valid_lat_up : float value to signal a possible maximum latitude. Default 2.0
    valid_lon_low : float value to signal a possible minimum longitude. Default 103.0
    valid_lon_up : float value to signal a possible maximum longitude. Default 105.0
    location_accuracy_thresh : upper threshold on the location
                               accuracy in meters beyond which we
                               treat the location as
                               missing. Default 1000
    """
    def invalid_location(acc):
        """Select rows with invalid accuracy. acc is a data frame column,
        returns a data frame of boolean values."""
        return (acc < 0) | (acc > location_accuracy_thresh)


    # replace invalid lat/lon values with NaN
    data_frame.loc[(data_frame['WLATITUDE'] < valid_lat_low) | (data_frame['WLATITUDE'] > valid_lat_up),
                   ['WLATITUDE', 'WLONGITUDE']] = np.nan
    data_frame.loc[(data_frame['WLONGITUDE'] < valid_lon_low) | (data_frame['WLONGITUDE'] > valid_lon_up),
                   ['WLATITUDE', 'WLONGITUDE']] = np.nan

    # replace locations with poor accuracy or negative accuracy values
    # (signal for invalid point) with NaN and set velocity as invalid
    if 'ACCURACY' in data_frame.columns:
        data_frame.loc[invalid_location(data_frame['ACCURACY']) ,
                       ['WLATITUDE', 'WLONGITUDE']] = np.nan
   
# def calculate_features(data_frame):
#     """Calculate additional features and attributes from the raw hardware
#     data. New attributes are added as new columns in the data frame in
#     place."""
#     # calculate distance covered since the last measurement, in meters
#     consec_points = izip(data_frame[['WLATITUDE', 'WLONGITUDE']].values, data_frame[['WLATITUDE', 'WLONGITUDE']].values[1:])
#     delta_dist = map(lambda x: great_circle_dist(x[1], x[0]) * 1000, consec_points)
#     # calculate time delta since the last measurement, in seconds
#     consec_timestamps = izip(data_frame[['TIMESTAMP']].values, data_frame[['TIMESTAMP']].values[1:])
#     delta_timestamps = map(lambda x: x[1][0]-x[0][0], consec_timestamps)
#     # calculate velocity in meter per second
#     velocity = map(lambda x: x[0]/x[1], izip(delta_dist, delta_timestamps))
#     # add a zero value for the first measurement where no delta is available
#     data_frame['VELOCITY'] = pd.Series([0] + velocity)

def calculate_features(data_frame, high_velocity_thresh=40):
    """Calculate additional features and attributes from the raw hardware
    data. New attributes are added as new columns in the data frame in
    place.
    high_velocity_thresh : maximum threshold for velocities in m/s,
                           higher values are rejected. Default 40m/s
                           (= 144 km/h)
    """
    # select rows in data frame that have valid locations
    df_validloc = data_frame.loc[~np.isnan(data_frame['WLATITUDE']) & ~np.isnan(data_frame['WLONGITUDE'])]
    # calculate distance delta from pairs of valid lat/lon locations that follow each other
    valid_latlon = df_validloc[['WLATITUDE', 'WLONGITUDE']].values
    dist_delta = map(lambda loc_pair: great_circle_dist(loc_pair[0], loc_pair[1], unit="meters"), izip(valid_latlon[:-1], valid_latlon[1:]))
    # calculate time delta from pairs of valid timestamps
    valid_times = df_validloc['TIMESTAMP'].values
    time_delta = valid_times[1:] - valid_times[:-1]
    # calculate velocity, m/s
    velocity = dist_delta / time_delta

    # create new columns for delta distance, time delta and velocity, initialzied with NaN
    data_frame['DISTANCE_DELTA'] = pd.Series(dist_delta, df_validloc.index[1:])
    data_frame['TIME_DELTA'] = pd.Series(time_delta, df_validloc.index[1:])
    data_frame['VELOCITY'] = pd.Series(velocity, df_validloc.index[1:]) # velocity in m/s
    
    # replace very high velocity values which are due to wifi
    # localizations errors with NaN in VELOCITY column
    label_too_high_vel = data_frame['VELOCITY'] > high_velocity_thresh
    idx_too_high = label_too_high_vel[label_too_high_vel==True].index.tolist()
    idx_bef_too_high = (np.array(idx_too_high)-1).tolist()
    data_frame.loc[idx_too_high,['WLATITUDE', 'WLONGITUDE','DISTANCE_DELTA','VELOCITY']] = np.nan
    data_frame.loc[idx_bef_too_high,['WLATITUDE', 'WLONGITUDE','DISTANCE_DELTA','VELOCITY']] = np.nan
    
def trip_segments(data_frame, stopped_thresh=0.1):
    """Segement the data into consecutive chunks of low velocity states
    (dwelling) and high velcoity (travelling). Return a list of trip
    segments and stopped segments. Each segment has the number of
    measurements, start and end index in the original data frame
    (starting from zero), start and end timestamp, start and end
    latitude and longitude.
    """
    def save_trip(trip_buffer, trips):
        trip_length = len(trip_buffer)
        trip_start_index, trip_end_index = trip_buffer[0], trip_buffer[-1]

        trip_start_time, trip_start_lat, trip_start_lon = data_frame.loc[trip_start_index][['TIMESTAMP', 'WLATITUDE', 'WLONGITUDE']]
        trip_end_time, trip_end_lat, trip_end_lon = data_frame.loc[trip_end_index][['TIMESTAMP', 'WLATITUDE', 'WLONGITUDE']]
        trips.append((trip_length, trip_start_index, trip_end_index, trip_start_time, trip_end_time, trip_start_lat, trip_start_lon, trip_end_lat, trip_end_lon))

    def save_stop(stopped_buffer, stops):
        stopped_length = len(stopped_buffer)
        stopped_start_index, stopped_end_index = stopped_buffer[0], stopped_buffer[-1]
        stopped_start_time, stopped_start_lat, stopped_start_lon = data_frame.loc[stopped_start_index][['TIMESTAMP', 'WLATITUDE', 'WLONGITUDE']]
        stopped_end_time, stopped_end_lat, stopped_end_lon = data_frame.loc[stopped_end_index][['TIMESTAMP', 'WLATITUDE', 'WLONGITUDE']]
        stops.append((stopped_length, stopped_start_index, stopped_end_index, stopped_start_time, stopped_end_time, stopped_start_lat, stopped_start_lon, stopped_end_lat, stopped_end_lon))

    trips = []
    stops = []
    stopped_buffer = []
    trip_buffer = []
    for index, row in data_frame.iterrows():
        # identify chunks of low and high velocity
        if row['VELOCITY'] < stopped_thresh:
            # device is not moving
            # save trip buffer and reset if not empty
            if trip_buffer:
                save_trip(trip_buffer, trips)
                trip_buffer = []
            stopped_buffer.append(index)
        else:
            # device is moving
            # save stopped buffer and reset if not empty
            if stopped_buffer:
                save_stop(stopped_buffer, stops)
                stopped_buffer = []
            trip_buffer.append(index)
    # store any remaining stop or trip that is still in the buffers
    if trip_buffer:
        save_trip(trip_buffer, trips)
    if stopped_buffer:
        save_stop(stopped_buffer, stops)
    return trips, stops

def processTrips(trip_store, list_POI, trip_dist=None):
    # Associates trips filed under trip_store to POI's. If we can't, we dismiss the trip
    threshold = 100 # in meters
    trips = []
    full_trips = []
    dist = []
    for j in range(0, len(trip_store)):
        if len(trip_store[j]) > 1:
            start_poi = None
            end_poi = None
            (start_lat, start_lon) = trip_store[j][0]
            (end_lat, end_lon) = trip_store[j][-1]
            for k in range(0, len(list_POI)):
                if list_POI[k] != None:
                    (poi_lat, poi_lon) = list_POI[k]
                    if distance_on_earth(poi_lat, poi_lon, start_lat, start_lon) < threshold:
                        start_poi = k
                    if distance_on_earth(poi_lat, poi_lon, end_lat, end_lon) < threshold:
                        end_poi = k
            if start_poi != end_poi and start_poi != None and end_poi != None:
                print "Found a trip!"
                trips += [[start_poi, end_poi]]
                full_trips += [trip_store[j]]
                if trip_dist != None:
                    dist += [trip_dist[j]]
    return (trips, full_trips, dist)

def processTripsMoreInfo(trips, pois, db):
    # Associates trips filed under trip_store to POI's. If we can't, we dismiss the trip
    # Also returns distance, duration of the trip
    threshold = 100 # in meters
    t = []
    for j in range(0, len(trips)):
        if len(trips[j]) > 1:
            start_poi = None
            end_poi = None
            (start_lat, start_lon) = (trips[j][0][5], trips[j][0][6])
            (end_lat, end_lon) = (trips[j][-1][7], trips[j][-1][8])
            for k in range(0, len(pois)):
                if pois[k] != None:
                    (poi_lat, poi_lon) = pois[k]
                    if distance_on_earth(poi_lat, poi_lon, start_lat, start_lon) < threshold:
                        start_poi = k
                    if distance_on_earth(poi_lat, poi_lon, end_lat, end_lon) < threshold:
                        end_poi = k
            if start_poi != end_poi and start_poi != None and end_poi != None and distance_on_earth(start_lat, start_lon, end_lat, end_lon) > 750 and (trips[j][-1][2]-trips[j][0][1]) > 10 and sum([distance_on_earth(db[k+1][2], db[k+1][3], db[k][2], db[k][3]) for k in range(trips[j][0][1], trips[j][-1][2])])/(trips[j][-1][2]-trips[j][0][1]) < 500 and (trips[j][-1][4] - trips[j][0][3] < 3600):
                measurements = sum([trip[0] for trip in trips[j]])
                start = trips[j][0][1] # index
                end = trips[j][-1][2] # index
                start_time = trips[j][0][3] # timestamp
                end_time = trips[j][-1][4] # timestamp
                total_time = end_time-start_time # time in seconds
                start_coord_lat = trips[j][0][5]
                start_coord_lon = trips[j][0][6]
                end_coord_lat = trips[j][-1][7]
                end_coord_lon = trips[j][-1][8]
                dist_precise = 0
                dist_coarse = 0
                for i in range(0, len(trips[j])):
                    if i % 2 == 0: # we don't count the stops
                        dist_precise += sum([distance_on_earth(db[k+1][2], db[k+1][3], db[k][2], db[k][3]) for k in range(trips[j][i][1], trips[j][i][2])])
                        dist_coarse += distance_on_earth(trips[j][i][5], trips[j][i][6], trips[j][i][7], trips[j][i][8])
                t += [[measurements, start, end, start_time, end_time, start_coord_lat, start_coord_lon, end_coord_lat, end_coord_lon, dist_precise, dist_coarse, total_time]]
    return t

########################
# Google Places search #
########################
# https://developers.google.com/places/web-service/intro

def getPlaces(lat, lon, radius, types):
    key = "" # Google API key
    types_string = "|".join(types)
    req_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=%f,%f&radius=%d&key=%s&types=%s" % \
        (lat, lon, radius, key, types_string)
    r = requests.get(req_url)
    results = r.json()["results"]
    return results
    
############################
# Google Directions search #
############################
# https://developers.google.com/maps/documentation/directions/intro

def getDirections(lat_start, lon_start, lat_end, lon_end, mode):
    key = "" # Google API key
    req_url = "https://maps.googleapis.com/maps/api/directions/json?origin=%f,%f&destination=%f,%f&mode=%s&key=%s" % \
        (lat_start, lon_start, lat_end, lon_end, mode, key)
    r = requests.get(req_url)
    results = r.json()
    if results["status"] == "OK":
        results = results["routes"][0] # picking the first best route
        return results
    else:
        return None
    
def totalTotalTripDistance(directions):
    return sum([distance_on_earth(step['start_location']['lat'], step['start_location']['lng'], step['end_location']['lat'], step['start_location']['lng']) for step in directions['legs'][0]['steps']])

def totalTripDistance(directions):
    return directions['legs'][0]['distance']['value']

def totalDuration(directions):
    return directions['legs'][0]['duration']['value']
    