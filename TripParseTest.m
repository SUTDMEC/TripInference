
clear
clc
close all


rootDir='C:\Users\Erik Wilhelm\Documents\GitHub\TripInference';

csvName='synthetic_sample_data.csv';

%ground truth school coordinates
school_lat=1.3298017;
school_lon=103.8062975;


%ground truth home coordinates
home_lat=[1.32964711060518;1.33103593858323;1.33012261316030;1.33010679489890;1.32998043477296;1.33052940776422;1.32993249020606;1.32846234153159;1.32933395574647;1.32879817012855];
home_lon=[103.810373011023;103.806122351826;103.805762490554;103.809959125139;103.802053347846;103.801335436115;103.799206603694;103.806434594117;103.808676130270;103.799320244711];


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

