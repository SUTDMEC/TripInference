function [POI_final,trip_store,vel,trip_dist,latlon_school,latlon_home,school_home_dist,poi_ind,time_stop]=TripParse3(unix_time,lat,lon)

try
%revised trip parsing algorithm. Considers a trip end when dwell>Xmin in
%one location. Stores that location as a POI. Accepts arbitrary lengths of
%data. POI between 9:00-12:00 is considered school. POI from 22:00-5:00 is home.
%Returns a list of POI's, and frequency they are visited. home first, school second.
%Returns NAN for those first two columns if home/school isn't successfully found

%expected inputs:
%unix_time: time in unix (seconds)
%lat: latitude in degrees WGS85
%lon: longitude in degrees WGS85

%outputs
% POI_final: list of POI identified. 1st entry is identified home, 2nd entry is identified school
% trip_store: cell array of trips identified as vectors of lat/lon coordinates
% vel: vector of calculated velocity in m/s 
% trip_dist: vector of distances for all trips identified
% latlon_school: vector of lat/lon points identified during school hours (mostly useful for debugging)
% latlon_home: vector of lat/lon points identified during home hours (mostly useful for debugging)
% school_home_dist: vector of distances between home and school

POI_final=[];
trip_store=[];
vel=[];
trip_dist=[];
latlon_school=[];
latlon_home=[];
school_home_dist=0;

stopped_thresh=0.1; %velocity in m/s below which we are stopped (0.4 km/h)

stopped_dwell=900; %240 seconds in fast scan, or the time it takes the device to sleep

high_thresh=40; %velocities higher than 144m/s are rejected

max_school_thresh=100; %school/home distances <Ym away are rejected - to negate the possibility of creating home/school links for sensors left at school by mistake

%school assumption times
school_start=7;
school_last=12;

%home assumption times
home_start=22;
home_end=5;
 
lat_round=round(lat*100000)/100000; %round lat to the nearest 10m
lon_round=round(lon*100000)/100000; %round lat to the nearest 10m

hourtime=hour(unix_time./86400+719529); %convert UNIX timestamps matlab time and then to hours

%return lat/lon coordinates which are only during school time
latlon=[lat lon];

latlon_school=latlon(hourtime>=school_start&hourtime<school_last,:);
latlon_home=latlon(hourtime>=home_start|hourtime<home_end,:);

dist=zeros(length(unix_time),1);
vel=zeros(length(unix_time),1);
stopped_raw=zeros(length(unix_time),1);
stopped=zeros(length(unix_time),1);

for i=2:length(unix_time) %calculate the normalized travel distance between each point and the POI associated with it
    dist(i)=lldistkm_vec([lat(i) lon(i)],[lat(i-1) lon(i-1)]).*1000;  %distance between datapoints in m
    vel(i)=dist(i)/(unix_time(i)-unix_time(i-1));
end

%filter data - remove unrealistic points and outliers using heuristics
vel(vel>high_thresh)=nan;

%optional smoothing step
%vel=smooth(vel,3);

stop_count=0;
move_count=1;
poi_count=1;
trip_count=1;
trip_temp=[];
dist_temp=0;
time_stop=0;

for j=1:length(vel) %iterate through velocity vector
    

    if vel(j)<stopped_thresh %stopped points
        stopped_raw(j)=1;
        stop_count=stop_count+1;
        
        if j>1
            time_stop(j)=unix_time(j)-unix_time(j-1)+time_stop(j);
        end
        
        move_count=1;
        
    else
        move_count=move_count+1;

    end
    
    if time_stop(j)>stopped_dwell %if the number of stopped points crosses a threshold

        POI(poi_count,:)=[lat_round(j), lon_round(j)];
        poi_ind(j)=1.3;
        poi_count=poi_count+1;
        stop_count=0; %reset counters
        move_count=1; %reset counters
        time_stop(j)=0;
    else
        poi_ind(j)=1.2;
    end
        
        

    
    
end

% if there are fewer than 2 POI's identified, impossible to identify home/school - return
if poi_count<2
    POI_final=[NaN(2,2)];
    school_home_dist=NaN;
    return
end

% keyboard

% find unique POI's in the set
[~,ind,~] = unique(POI(:,1));

POI=POI(ind,:);

%find the POIs during school / home, and move them to top of list
szPOI=size(POI);
if szPOI(1)>1 %again check if there are > 2 unique POI's
    for k=1:szPOI(1)

        ind_POI{k}=find(lat_round==POI(k,1)&lon_round==POI(k,2)); %find indices of the POIs in the vector
        
        poi_school{k}=find(hourtime(ind_POI{k})>=school_start&hourtime(ind_POI{k})<school_last); %find POI within time range
        school_count(k)=length(poi_school{k});

        poi_home{k}=find(hourtime(ind_POI{k})>=home_start|hourtime(ind_POI{k})<home_end); %find POI within time range
        home_count(k)=length(poi_home{k});

    end
else
    keyboard
    POI_final=[NaN(2,2);POI];
    school_home_dist=NaN;
    return
end
    
%move POIs to top of list, assume that if no school/home time POI is
%identified, the value is NaN



%school
[sc_count,ind_sch]=max(school_count);
%home
[home_count,ind_home]=max(home_count);


%only if there are hits for home time, assign to home
if home_count>0 && ind_sch~=ind_home
    POI_final(1,:)=POI(ind_home,:);
else %this assumption applies if we wish to process an entire day
    keyboard
    POI_final=[NaN(2,2);POI];
    school_home_dist=NaN;
    return
end

%only if there are hits for school time, assign to school
if sc_count>0 && ind_sch~=ind_home
    POI_final(2,:)=POI(ind_sch,:);
else
    keyboard
    POI_final=[NaN(2,2);POI];
    school_home_dist=NaN;
    return
end

%sort out home/school pairings < YY km away - these are anomolies
sz_poi=size(POI_final);
if sz_poi(1)>1
    school_home_dist=lldistkm_vec(POI_final(1,:),POI_final(2,:));

    if school_home_dist*1000 < max_school_thresh
        POI_final=[NaN(2,2);POI];
        school_home_dist=NaN;
        return
    end
end
POI_rem=POI;
POI_rem([ind_sch ind_home],:)=[];

POI_final=[POI_final; POI_rem];

    
catch ME
   keyboard 
end




