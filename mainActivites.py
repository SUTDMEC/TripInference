import numpy as np
import oldTripParse as tp
import getActivities as ga
import itertools

#########################
# Read pilot nodes data #
#########################

#         0     1    2      3     4
# Data is nid / ts / mode / lat / lon
data = np.genfromtxt("pilot2_trimmed.csv", delimiter=",")
data = data[1:-1,:] # Remove header
nodes = np.unique(data[:,0]) # Get list of nodes
length_POI_before = np.zeros(len(nodes)) # For statistical purposes, compute how many POIs we removed
length_POI_after = np.zeros(len(nodes))
activity_types = ['home', 'school', 'food', 'commercial', 'sports', 'others']
num_activities = len(activity_types)

#############################################
# Construct outside bounds from GIS data    #
# By outside we mean sports and parks       #
#############################################
with open('sports.json') as data_file:
    sports = json.load(data_file)

with open('parks.json') as data_file:
    parks = json.load(data_file)

outside_activities = sports["features"]+parks["features"]
outside_bounds = []
for i in range(0, len(outside_activities)):
    coordinates = outside_activities[i]["geometry"]["coordinates"]
    chain = itertools.chain(*coordinates) # coordinates is an array with depth 4, for some reason, so we flatten it
    chain = itertools.chain(*list(chain))
    coordinates = list(chain)
    bounds = ga.getBounds(coordinates)
    if max(abs(bounds[0][0]-bounds[1][0]), abs(bounds[0][1]-bounds[1][1])) < 0.1: # remove absurd bounding boxes
        outside_bounds += [bounds]

###################
# Node processing #
###################      

for i in range(50, 118): # Iterate over nodes
    nid = nodes[i]
    cur_data = data[data[:,0]==nid,:] # Get data associated to nid
    t = cur_data[:, 1]
    lat = cur_data[:, 3]
    lon = cur_data[:, 4]
    mode = cur_data[:, 2]

    # tripParse takes args t, lat, lon, mode
    (POI_final, trip_store, vel, trip_dist, latlon_school, latlon_home, school_home_dist) = tp.tripParse(t, lat, lon, mode)
    if POI_final[0] == [None] or len(POI_final[0]) != 1:
        POI_final[0] = []
    if POI_final[1] == [None] or len(POI_final[1]) != 1:
        POI_final[1] = []
    print "-------------------------"
    print i
    length_POI_before[i] = len(POI_final[0])+len(POI_final[1])+len(POI_final[2])
    POI = ga.separatePOI(POI_final, 75) # Reduce POIs to avoid redundancies
    length_POI_after[i] = len(POI[0])+len(POI[1])+len(POI[2])
    list_POI = POI[0]+POI[1]+POI[2] # Flatten POI_final array (easier)...
    index_POI = range(0, len(POI[0])) + range(1, len(POI[1])+1) + range(2, len(POI[2])+2) # ... but keep track of indices with index_POI
    activities = []
    print list_POI
    if len(list_POI) > 0:
        for j in range(0, len(list_POI)):
            # Build coefficients dictionary that weighs different activity options
            if index_POI[j] == 0:
                activities += ["home"]
            elif index_POI[j] == 1:
                activities += ["school"]
            else:
                (lat, lon) = list_POI[j]
                coefs = { "food": 0, "commercial": 0, "sports": 0 }

                # If we can assert that a point is inside a park or a sports installation, then we weigh the sports item a lot
                if ga.pointOutside([lat, lon], outside_bounds) == True:
                    coefs["sports"] += 10

                # Google Places request
                types = ['store', 'park', 'restaurant', 'gym', 'food']
                radius = 50
                results = ga.getPlaces(lat, lon, radius, types)
                for k in range(0, len(results)):
                    result = results[k]
                    distance_from_point = tp.distance_on_earth(lat, lon, result["geometry"]["location"]["lat"], result["geometry"]["location"]["lng"])
                    distance_from_point = min(radius, distance_from_point)
                    for t in result["types"]:
                        # Weight decreases as distance from point increases
                        if t == "store":
                            coefs["commercial"] += 2*(1-distance_from_point/radius)
                        if t == "food" or t == "restaurant":
                            coefs["food"] += 1*(1-distance_from_point/radius)
                        if t == "park" or t == "gym":
                            coefs["sports"] += 2*(1-distance_from_point/radius)

                # If Google Places returned good results, we select the one with the highest weight
                if max(coefs.values()) > 0:
                    max_coef = ga.maxValueInDict(coefs)
                    activities += [max_coef]
                else: # Otherwise, we file it under "others"
                    activities += ["others"]

        # Build trip matrix for chord diagram
        (trips, ft) = ga.processTrips(trip_store, list_POI)
        trip_matrix = np.zeros((num_activities, num_activities)) # we have 6 different activities home/school/food/commercial/sports/others
        for j in range(0, len(trips)):
            trip_matrix[activity_types.index(activities[trips[j][0]]), activity_types.index(activities[trips[j][1]])] += 1.0

        # Save trip matrices and POI lat/lon + assigned activity
        np.savetxt("trip_matrices/"+str(int(nid))+".csv", trip_matrix)
        act_index = [activity_types.index(activities[j]) for j in range(0, len(activities))] # index in act_types array
        np_act = np.array(act_index)
        np_act = np.reshape(np_act, (len(np_act),1))
        POI = np.hstack([np.array(list_POI), np_act]) # POI associated with their activities
        np.savetxt("POI/"+str(int(nid))+".csv", POI)

# How many POIs we are throwing away with our separatePOI function (at least half it turns out, for threshold of 50 meters!)
ratios_length = np.divide(length_POI_after, length_POI_before)
ratios_length = ratios_length[~np.isnan(ratios_length)]
percentage_remaining = sum(ratios_length)/len(ratios_length)*100