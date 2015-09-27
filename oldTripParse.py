#!/usr/bin/env python
#Script to identify trips
#Erik's algorithm written in Python by Sandra, SUTD, 2015

import datetime
import numpy as np
import pandas as pd
import math
from itertools import izip_longest

def smooth(values, window):  #SS: to verfiy
    weights = np.repeat(1.0, window)/window
    sma = np.convolve(values, weights, 'same') # valid vs same - to compare..

    return sma

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
    arc = math.acos( cos )
    #print arc
    # Distance in meters
    return arc*6371*1000


def tripParse(t, lat, lon, mode):

	stopped_thresh=0.1 #velocity in m/s below which we are stopped (0.4 km/h)

	stopped_dwell=24 #240 seconds in fast scan, or the time it takes the device to sleep

	high_thresh=40 #velocities higher than 144m/s are rejected

	max_school_thresh=500 #school/home distances<500m away are rejected

	#school assumption times
	school_start=9
	school_last=12

	#home assumption times
	home_start=22
	home_end=5

	lat_round = [round(x,4) for x in lat] #round lat to the nearest 10m - rounding differences exist between python and MATLAB
	lon_round = [round(x,4) for x in lon] #round lat to the nearest 10m - rounding differences exist between python and MATLAB

	#lat_round = lat
	#lon_round = lon

	GMT_offset = 8 #correction factor - seems that the datetime function produces values which are 8 hours in the future

	hourtime = [datetime.datetime.fromtimestamp(x).hour - GMT_offset for x in t]  #Gets hour from unix timestamp - corrected by 8 hours

	#print hourtime

	latlon = zip(lat, lon)

	latlon_school = [x for x, y in zip(latlon, hourtime) if (y > school_start) and (y < school_last)]
	latlon_home = [x for x, y in zip(latlon, hourtime) if (y > home_start) or (y < home_end)]


	dist = [0] * len(t)
	delt = [0] * len(t)
	vel =[0] * len(t)
	stopped_raw = [0] * len(t)
	stopped = [0] * len(t)

	for i in range (1, len(t)):

		dist[i] = distance_on_earth(lat[i], lon[i], lat[i-1], lon[i-1])
		vel[i] = dist[i]/(t[i] - t[i-1])
		delt[i]=(t[i] - t[i-1])

	#Filter data

	vel = [x for x in vel if x <= high_thresh]

	#Smooth data

	#vel = list(smooth(vel, 3))

	stop_count=0
	move_count=0
	poi_count=0
	trip_count=0
	trip_temp=[]
	dist_temp=[]
	trip_dist=[]
	trip_store = []
	POI = []

	#print delt
	#print dist
	#print vel



	for j in range(0, len(vel)):


		if vel[j] < stopped_thresh:

			stopped_raw[j] = 1
			stop_count += 1

			'''print "I STOPPED"
			print "j", j
			print "stop_count", stop_count
			print "move_count", move_count
			print "trip_temp", trip_temp
			print "trip_dist", trip_dist
			print "dist_temp", dist_temp'''


		else:

			trip_temp.append((lat[j], lon[j]))
			
			if move_count >= 1:
				dist_temp.append(distance_on_earth(trip_temp[move_count][0], trip_temp[move_count][1], trip_temp[move_count-1][0], trip_temp[move_count-1][1]))
			else:
				dist_temp.append(0)
			
			move_count += 1
			#stop_count = 0

			'''print "I MOVED"
			print "j", j
			print "stop_count", stop_count
			print "move_count", move_count
			print "trip_temp", trip_temp
			print "trip_dist", trip_dist
			print "dist_temp", dist_temp'''


		if stop_count > stopped_dwell:


			stopped[j] = 1
			POI.append((lat_round[j], lon_round[j]))
			trip_store.append(trip_temp)
			trip_temp = []
			trip_dist.append(sum(dist_temp))
			dist_temp = []
			trip_count += 1
			poi_count += 1
			stop_count = 0
			move_count = 0



			'''print "I AM AT A POI"
			print "j", j
			print "stop_count", stop_count
			print "move_count", move_count
			print "trip_count", trip_count
			print "trip_temp", trip_temp
			print "trip_dist", trip_dist
			print "POI", POI'''

	if poi_count < 2:

		POI_final = []
		school_home_dist = []

	POI = list(set(POI))

	#find the POIs during school / home, and move them to top of list

	poi_school = []
	poi_home = []
	school_count = []
	home_count = []

	if len(POI) > 1:

		for k in range(0, len(POI)):
			
			ind_POI = [i for i, x in enumerate(zip(lat_round, lon_round)) if x[0] == POI[k][0] and x[1] == POI[k][1]] #SS: Don't like this, check alternative
			schooltimes = []

			for item in ind_POI:
				if (hourtime[item] > school_start) and (hourtime[item] < school_last):
					schooltimes.append(hourtime[item])
			poi_school.append(schooltimes)

			school_count.append(len(poi_school[k]))

			hometimes = []
			for item in ind_POI:
				if (hourtime[item] > home_start) or (hourtime[item] < home_end):
					hometimes.append(hourtime[item])
			poi_home.append(hometimes)
			home_count.append(len(poi_home[k]))

		#print school_count
		#print poi_school
		#print home_count
		#print poi_home

	else:

		POI_final = []
		school_home_dist = []

	ind_home = []
	ind_sch = []
	ind_rest = []
	homelist = []
	schoollist = []
	max_school_count = 0
	max_home_count = 0

	if len(school_count) > 0:

		max_school_count = max(school_count)
		ind_sch = [i for i, x in enumerate(school_count) if x == max_school_count]

	if len(home_count) > 0:

		max_home_count = max(home_count)
		ind_home = [i for i, x in enumerate(home_count) if x == max_home_count]


	POI_final = []
	school_home_dist = []


	if ind_home != ind_sch:

		homelist = [POI[x] for x in ind_home]
		POI_final.append(homelist)
		schoollist = [POI[x] for x in ind_sch]
		POI_final.append(schoollist)

	else:

		#Dealing with weird data where a point can be in school and home intervals (eg.devices left at school at night)
		#We assume the one with more counts is the correct POI and we set the other one to an empty list
		#Alternative is to set both to empty 

		if max_school_count > max_home_count:
			POI_final.append([])
			schoollist = [POI[x] for x in ind_sch]
			POI_final.append(schoollist)
		else:
			homelist = [POI[x] for x in ind_home]
			POI_final.append(homelist)
			POI_final.append([])



	#The rest of the POIs come after home and school

	ind_rest = list(set(range(0, len(POI))) - set(homelist) - set(schoollist))
	restlist = [POI[x] for x in ind_rest]
	POI_final.append(restlist)

	school_home_dist = [distance_on_earth(x[0], x[1], y[0], y[1]) for x, y in zip(POI_final[0], POI_final[1])]

	for i in range(0, len(school_home_dist)):
		if school_home_dist[i] < max_school_thresh:
			POI_final[0][i] = None
			POI_final[1][i] = None
			school_home_dist[i] = None


	# print POI_final

	return POI_final, trip_store, vel, trip_dist, latlon_school, latlon_home, school_home_dist
