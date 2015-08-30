
clear
clc
close all


rootDir='C:\Users\Erik Wilhelm\Documents\GitHub\TripInference';

csvName='synthetic_sample_data.csv';

%ground truth school coordinates
school_lat=1.3298017;
school_lon=103.8062975;


%ground truth home coordinates
home_lat=[1.32992944080094;1.33121574909076;1.33186166686553;1.32820555386601;1.32781414132580;1.32970308306266;1.32796373269814;1.33034760557324;1.32922872819711;1.33028341254650];
home_lon=[103.808772171192;103.801598269294;103.803274790548;103.805980957317;103.804362143691;103.803138620502;103.809896471073;103.799143470792;103.812615791834;103.803991817046];


[raw_num,raw_txt,~]=xlsread([rootDir,'\',csvName]);

time_offset=0; % 8 hours of offset may be required if sensor data is in GMT and not SGT

ID=raw_num(:,1); 
devices=unique(ID,'stable'); %find all ID's of devices in the dataset

figure
trip_ax=gca;
hold

plot(trip_ax,school_lon, school_lat,'xk' ,'MarkerSize',14,'LineWidth',2) %plot ground truth from sample set
plot(trip_ax,home_lon, home_lat,'rx','MarkerSize',14,'LineWidth',2) %plot ground truth from sample set

for i=1:length(devices) %import and parse all files individually
    
    ind_dev=find(ID==devices(i));
    
    lat=raw_num(ind_dev,11);
    lon=raw_num(ind_dev,12);
    utime=raw_num(ind_dev,2)+time_offset*3600; %unix time - add and offset for SGT if necessary
    ind_lat=find(isnan(lat));
    lat(ind_lat)=[];
    lon(ind_lat)=[];
    time=utime; 
    time(ind_lat)=[];

    [POI{i},trip_store{i},vel{i},trip_dist{i},latlon_school{i},latlon_home{i},school_home_dist(i)]=TripParse(time,lat,lon);
    
    POIschool_ok(i,:)=POI{i}(2,:);
    POIhome_ok(i,:)=POI{i}(1,:);
    
    plot(trip_ax, [POIschool_ok(i,2),POIhome_ok(i,2)], [POIschool_ok(i,1),POIhome_ok(i,1)],'bx','MarkerSize',14,'LineStyle','--') %plot identified home/school points
    
    
end

