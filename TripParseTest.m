
clear
clc
close all

figure
trip_ax=gca;
hold

% rootDir='C:\Users\Erik Wilhelm\Documents\GitHub\TripInference';
% csvName='synthetic_sample_data.csv';

rootDir='C:\Users\Erik Wilhelm\Documents\Big Data (not backed up)\SUTD_data\SENSg\ServerModeData';
% csvName='10_bus_6sept15';
csvName='pilot3_formatted_server.csv';
csvName=[ csvName '.csv'];

GTcsvName=[ csvName '_gt.csv'];
[raw_num_gt,raw_txt_gt,~]=xlsread([rootDir,'\',GTcsvName]);
% from Raw File
school_lat=raw_num_gt(1,2);
school_lon=raw_num_gt(1,3);
home_lat=raw_num_gt(:,4);
home_lon=raw_num_gt(:,5);

plot(trip_ax,school_lon, school_lat,'xk' ,'MarkerSize',14,'LineWidth',2) %plot ground truth from sample set
plot(trip_ax,home_lon, home_lat,'rx','MarkerSize',14,'LineWidth',2) %plot ground truth from sample set

if ~exist('raw_num','var')
    [raw_num,raw_txt,~]=xlsread([rootDir,'\',csvName]);
end
time_offset=0; % 8 hours of offset may be required if sensor data is in GMT and not SGT

ID=raw_num(:,1); 
devices=unique(ID,'stable'); %find all ID's of devices in the dataset


for i=1:length(devices) %import and parse all files individually
    
    ind_dev=find(ID==devices(i));
    
    lat=raw_num(ind_dev,11);
    lon=raw_num(ind_dev,12);
    utime=raw_num(ind_dev,2)+time_offset*3600; %unix time - add and offset for SGT if necessary
    ind_lat=find(isnan(lat));
    lat(ind_lat)=[];
    lon(ind_lat)=[];
    time{i}=utime; 
    time{i}(ind_lat)=[];

    [POI{i},trip_store{i},vel{i},trip_dist{i},latlon_school{i},latlon_home{i},school_home_dist(i)]=TripParse(time{i},lat,lon);
    
    POIschool_ok(i,:)=POI{i}(2,:);
    POIhome_ok(i,:)=POI{i}(1,:);
    
    plot(trip_ax, [POIschool_ok(i,2),POIhome_ok(i,2)], [POIschool_ok(i,1),POIhome_ok(i,1)],'bx','MarkerSize',14,'LineStyle','--') %plot identified home/school points
    
    
end

