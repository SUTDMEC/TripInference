import getActivities as ga
import tripParse as tp
import numpy as np
import pandas as pd
import pprint
import process
import json

def reconstructTrips(trips, stops, poi_dwell_time=900):
    def dwell_time(stop):
        """Return time spend in a stopped location in seconds"""
        start_time, end_time = stop[3], stop[4]
        return (end_time - start_time)
        
    t = []
    cur_trip = []
    if stops[0][1] == 0: # we start with a trip
        del stops[0]
    for i in range(0, len(trips)):
        cur_trip += [trips[i]]
        if i < len(stops):
            stop = stops[i]
            if dwell_time(stop) < poi_dwell_time:
                cur_trip += [stop]
            else:
                t += [cur_trip]
                cur_trip = []
        else:
            t += [cur_trip]
            cur_trip = []
    return t

pp = pprint.PrettyPrinter(indent=4)
data = np.genfromtxt("latlontime.csv", delimiter=",")
data = data[1:-1,:] # Remove header
nodes = np.unique(data[:,0]) # Get list of nodes
total_trips_logged = 0
for i in range(0, len(nodes)): # Iterate over nodes
    print "--------------------------------------"
    nid = nodes[i]
    print "Node %d, index %d" % (nid, i)
    cur_data = data[data[:,0]==nid,:] # Get data associated to nid
    t = cur_data[:, 1]
    lat = cur_data[:, 2]
    lon = cur_data[:, 3]
    df = pd.DataFrame({ "TIMESTAMP": pd.Series(t), "WLONGITUDE": pd.Series(lon), "WLATITUDE": pd.Series(lat) })
    #ga.clean_data(df)
    ga.calculate_features(df)
    (pois, trips, stops) = ga.process(df, stopped_thresh=0.2)
    pois_coord = [((poi[5]+poi[7])/2, (poi[6]+poi[8])/2) for poi in pois]
    pois_coord = ga.separatePOIFlat(pois_coord)
    t = reconstructTrips(trips, stops)
    trips_coord = [[[trip[0][5], trip[0][6]], [trip[-1][7], trip[-1][8]]] for trip in t]
    trips = ga.processTripsMoreInfo(t, pois_coord, cur_data)
    np.savetxt("trips2/"+str(int(nid))+".csv", trips)
    mode = "walking"
    for j in range(0, len(trips)):
        trip = trips[j]
        directions = ga.getDirections(trip[5], trip[6], trip[7], trip[8], mode)
        if directions != None:
            with open("directions2/"+str(int(nid))+"-"+str(int(j))+"-"+mode+".json", 'w') as outfile:
                json.dump(directions, outfile)

            total_trips_logged += 1
            google_dist = ga.totalTripDistance(directions)
            google_total_total_dist = ga.totalTotalTripDistance(directions)
            print "-------------------------------------------"
            print "Google distance %f" % float(google_dist)
            print "Google total total trip distance %f" % float(google_total_total_dist)
            dist_precise = float(trip[9])
            dist_coarse = float(trip[10])
            print "Student distance precise %f" % dist_precise
            print "Student distance coarse %f" % dist_coarse
            print "Google duration %f" % ga.totalDuration(directions)
            print "Our duration %f" % float(trip[11])
print "Logged %d trips" % total_trips_logged