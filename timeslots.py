import os
import subprocess
import argparse

from astropy.coordinates import EarthLocation, SkyCoord, AltAz
from astropy.time import Time
from astropy import units as u

import datetime
import numpy as np
import pandas as pd

ATA_LAT = 40.8178
ATA_LON = 121.473

time_string = "%Y-%m-%d %H:%M:%S"

#ATA = EarthLocation.of_site("Allen Telescope Array")
#ATA = EarthLocation(-2524157.30002672, -4123357.36615597, 4147750.83995041)

ATA = EarthLocation(lat = 40.8175, lon = -121.47333)

'''
ATA_PULSARS = PULSARS = 
       ['J1939+2134', 
        'J1713+0747', 
        'J2145-0750', 
        'J1857+0943', 
        'J1022+1001', 
        'J1643-1224', 
        'J1744-1134', 
        'J0613-0200', 
        'J0837+0610', 
        'J0332+5434', 
        'J0953+0755', 
        'J1935+1616', 
        'J2022+2854', 
        'J2018+2839', 
        'J1932+1059', 
        'J2022+5154', 
        'J1645-0317', 
        'J1239+2453', 
        'J0358+5413']
'''

ATA_PULSAR_DATA = pd.read_csv("PULSARS.csv")#[el.split(",") for el in f.read().split("\n") if el[0] != '' and if el[0] != "PULSAR"]

ATA_PULSARS = PULSARS = ATA_PULSAR_DATA["PULSAR"]

PRIORITIES = {}

for priority in range(1, max([int(el) for el in ATA_PULSAR_DATA["PRIORITY"]]) + 1):
    if priority not in PRIORITIES:
        PRIORITIES[priority] = ATA_PULSAR_DATA["PULSAR"][ATA_PULSAR_DATA["PRIORITY"] == priority].tolist()

MAX_OBS_TIME = 30
MIN_OBS_TIME = 10
OBS_TIME_RANGE = MAX_OBS_TIME - MIN_OBS_TIME 

FLUX_DENS_HIGH_PLAT = 30
FLUX_DENS_LOW_PLAT = 5
FLUX_DENS_RANGE = FLUX_DENS_HIGH_PLAT - FLUX_DENS_LOW_PLAT

OBS_BUFFER_TIME = 5

PSRCAT_PARAMS = [
    'PSRJ',
    'RAJ',
    'DECJ',
    'S1400'
    ]

def fetch_pulsar_data(pulsar, key = None):
    options = ['-nohead',
            '-o', 'short',
            '-nonumber'
            ]
    

    command = ['psrcat', pulsar] + ['-c', " ".join(PSRCAT_PARAMS)] + options


    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    result = out.decode("utf-8")
    while "  " in result:
        result = result.replace("  ", " ")

    if key is None:
        return result.split(" ")
    else:
        return result.split(" ")[PSRCAT_PARAMS.index(key)]

def get_ATA_LST(time = None):
    if time is None:
        time = datetime.datetime.now()

    observing_location = ATA 

    obs_time = Time(time, scale = 'utc', location = observing_location)
    lst = obs_time.sidereal_time('mean')

    return lst

#takes ra and dec in 'xxhxxmxx.xs' format
def radec_to_azel(ra, dec, time):
    observing_location = ATA
    observing_time = Time(time)
    aa = AltAz(location = observing_location, obstime = observing_time)

    coord = SkyCoord(ra = ra, dec = dec)
    newcoord = coord.transform_to(aa)

    return [newcoord.altaz.az.deg, newcoord.altaz.alt.deg]

def check_pulsar_availability(pulsar, timewindows = None):
    if timewindows is None:
        now = datetime.datetime.now()
        delta = datetime.timedelta(minutes = 180)

        timewindows = [[now, now + delta]]
    
    data = fetch_pulsar_data(pulsar)

    RAJ_str = data[PSRCAT_PARAMS.index("RAJ")]

    RAJ_spl = RAJ_str.split(":")
    RAJ_fmt = RAJ_spl[0] + "h" + RAJ_spl[1] + "m" + RAJ_spl[2] + "s"

    DECJ_str = data[PSRCAT_PARAMS.index("DECJ")]

    DECJ_spl = DECJ_str.split(":")
    DECJ_fmt = DECJ_spl[0] + "d" + DECJ_spl[1] + "m" + DECJ_spl[2] + "s"

    availability = []

    for window in timewindows:
        altaz_start = radec_to_azel(RAJ_fmt, DECJ_fmt, window[0])
        altaz_end = radec_to_azel(RAJ_fmt, DECJ_fmt, window[1])

        az_beg = altaz_start[0]
        el_beg = altaz_start[1]

        az_end = altaz_end[0]
        el_end = altaz_end[1]

        available = []

        #the idea here is that we set the rise and set times to be
        #the edges of the window of availability, and then check
        #if the object rises later or sets earlier. if it doesn't,
        #then functionally the object does "rise" and "set" at the edges
        #of the window of availability, at least with regards to our
        #observation
        rise_time = window[0]
        set_time = window[1]

        search_delta = datetime.timedelta(minutes = 60)

        if el_beg < 20:
            while rise_time < window[1]:
                rise_time = rise_time + search_delta
                el_beg_new = radec_to_azel(RAJ_fmt, DECJ_fmt, rise_time)[1]
                if el_beg_new >= 20:
                    if abs(search_delta.total_seconds()) < 5:
                        break
                    rise_time = rise_time - search_delta
                    search_delta = search_delta * 0.5

        search_delta = datetime.timedelta(minutes = 60)

        if el_end < 20:
            while set_time > window[0]:
                set_time = set_time - search_delta
                el_end_new = radec_to_azel(RAJ_fmt, DECJ_fmt, set_time)[1]
                if el_end_new >= 20:
                    if abs(search_delta.total_seconds()) < 5:
                        break
                    set_time = set_time + search_delta
                    search_delta = search_delta * 0.5

        if rise_time >= window[1]:
            available = [False, False]
        else:
            available.append(rise_time)
            available.append(set_time)


        '''
        #check if the object is available at the start of the window
        #else find when it rises
        if el_beg >= 20:
            available.append(window[0])
        else:
            object_rises = window[0]
            az = az_beg
            el = el_beg
            while el < 20:
                object_rises = object_rises + search_delta
                
                if object_rises >= window[1]:
                    break
                
                az, el = radec_to_azel(RAJ_fmt, DECJ_fmt, object_rises)

            #if the rise time is >= to the end of the window, the object can't be seen
            if object_rises >= window[1]:
                available.append(False)
            else:
                available.append(object_rises)
    
        '''

        '''
        #and now check for the end
        if el_end >= 20:
            available.append(window[1])
        else:
            #if the object was available earlier on in the window,
            #then we can check for when it sets
            if available[0]:
                object_sets = window[1]
                az = az_end
                el = el_end
                while el < 20:
                    object_sets = object_sets - search_delta

                    #since the object was available at the beginning, we don't have to check
                    #for the object_sets time being less than the start

                    az, el = radec_to_azel(RAJ_fmt, DECJ_fmt, object_sets)
                    
                available.append(object_sets)
            #otherwise we know the object is not visible during the window
            else:
                available.append(False)
        '''

        availability.append(available)

    return availability


def create_obs_schedule(l, timewindows = None):
    if timewindows is None:
        timewindows = [[0, 1]]

    now = datetime.datetime.now()

    for window_ind in range(len(timewindows)):
        start = timewindows[window_ind][0]
        end = timewindows[window_ind][1]
        w = [now + datetime.timedelta(minutes = start), now + datetime.timedelta(minutes = end)]
        timewindows[window_ind] = w

    print("Checking pulsar visibilities...")
    all_availabilities = [check_pulsar_availability(pulsar, timewindows) for pulsar in l] 

    availabilities_dict = {}
    for item, pulsar in zip(all_availabilities, l):
        availabilities_dict[pulsar] = item

    print("Computing observation times using BUFFERTIME = " + str(OBS_BUFFER_TIME) + "...")
    all_obstimes = []#[float(fetch_pulsar_data(pulsar, "S1400")) for pulsar in l]
    #all_obstimes = [OBS_BUFFER_TIME + min(MIN_OBS_TIME + OBS_TIME_RANGE * (max(FLUX_DENS_HIGH_PLAT - fluxdens, 0) / FLUX_DENS_RANGE), MAX_OBS_TIME) for fluxdens in all_obstimes]

    for pulsar_ind in range(len(l)):
        pulsar = l[pulsar_ind]
        fluxdens = float(fetch_pulsar_data(pulsar, "S1400"))
        basetime = MIN_OBS_TIME + OBS_TIME_RANGE * ((max(FLUX_DENS_HIGH_PLAT - fluxdens, 0) / FLUX_DENS_HIGH_PLAT) ** (1 / 2))
        maxtime = MAX_OBS_TIME
        obstime = OBS_BUFFER_TIME + min(basetime, MAX_OBS_TIME)

        obstime = min( max( MIN_OBS_TIME, MIN_OBS_TIME / ((fluxdens / FLUX_DENS_HIGH_PLAT) ** 2)), MAX_OBS_TIME) + OBS_BUFFER_TIME

        all_obstimes.append(obstime)

    obstimedict = {}

    for ind in range(len(PULSARS)):
        obstimedict[PULSARS[ind]] = all_obstimes[ind]

    remaining_pulsars = obstimedict

    visible_matches = {}

    schedule = {}

    print("Matching observation windows to visible pulsars...")

    observed = []

    QUEUE = []

    for twind_ind in range(len(timewindows)):
        timewindow = timewindows[twind_ind]
        print("\tChecking visible pulsars for window", timewindow[0].strftime(time_string), "->", timewindow[1].strftime(time_string))
        available = []
        for pulsar in l:
            pulsar_window = availabilities_dict[pulsar][twind_ind]
            if not pulsar_window[0]:
                continue
            else:
                available.append(pulsar)

        schedule[timewindow[0]] = []
        marker = timewindow[0]

        for priority in range(max(PRIORITIES), 0, -1):

            print("\t\tWorking on priority " + str(priority) + "...")
            if priority not in PRIORITIES:
                print("\t\t\tNo pulsars with this priority, skipping...")
                continue

            this_priority_avail = [el for el in available if el in PRIORITIES[priority]]
            this_priority_avail.sort(key = lambda x : availabilities_dict[x][twind_ind][0])

            print("\t\t\tPrioritizing unobserved pulsars...")
            #for every pulsar we observe, we want to put those at the back of the list 
            #so we will keep track of which pulsars we have observed, and whenever we
            #construct a list of available pulsars, and sort by earliest visibility
            #time, we will remove every observed pulsar and then add the list of observed pulsars
            #back to the end (after sorting that itself for earliest visibility time)

            #we only want to add back observed pulsars that are still available
            observed_add_back = []

            for pulsar in observed:
                try:
                    this_priority_avail.remove(pulsar)
                    observed_add_back.append(pulsar)
                except ValueError:
                    pass

            observed_add_back.sort(key = lambda x : availabilities_dict[x][twind_ind][0])

            this_priority_avail = this_priority_avail + observed_add_back

            visible_matches[timewindow[0]] = this_priority_avail

            print("\t\t\tConstructing schedule for window...")
            print("\t\t\tAvailable pulsars: " + " ".join(this_priority_avail))
            for pulsar in this_priority_avail:
                marker = timewindow[0]

                obs_len = obstimedict[pulsar]

                pulsar_window = availabilities_dict[pulsar][twind_ind]

                if marker < pulsar_window[0]:
                    marker = pulsar_window[0]

                #if the pulsar isn't visible for long enough
                if pulsar_window[1] - pulsar_window[0] < datetime.timedelta(minutes = obs_len):
                    print("\t\t\t\t" + pulsar, " not visible:", pulsar_window[0].strftime(time_string), "->", pulsar_window[1].strftime(time_string))
                    continue

                '''
                #if we don't have enough time to observe the pulsar
                if marker + datetime.timedelta(minutes = obs_len) > timewindow[1]:
                    print("\t\t\t\t" + pulsar, " takes too long:", marker.strftime(time_string), "->|", timewindow[1].strftime(time_string), "but need", obs_len)
                    continue
                '''
                #we're going to iterate through the current schedule, and search for spaces between observations
                #if that space is greater than our required observation time, then we will schedule the observation
                schedule_item = None
                this_window_schedule = schedule[timewindow[0]]
                for window_end_index in range(len(this_window_schedule) + 1):
                    if window_end_index == 0:
                        empty_window_start = timewindow[0]
                        #if there are no currently scheduled observations
                        if len(this_window_schedule) == 0:
                            empty_window_end = timewindow[1]
                        else:    
                            empty_window_end = this_window_schedule[window_end_index][2]
                    elif window_end_index == len(this_window_schedule):
                        empty_window_start = this_window_schedule[-1][2] + datetime.timedelta(minutes = this_window_schedule[-1][1])
                        empty_window_end = timewindow[1]
                    else:
                        #the start of the window is the end of the previous observation
                        #which we obtain by adding the obs time to the start time
                        empty_window_start = this_window_schedule[window_end_index - 1][2] + datetime.timedelta(minutes = this_window_schedule[window_end_index - 1][1])
                        #the end of the window is the start of the next observation
                        empty_window_end = this_window_schedule[window_end_index][2]
                    

                    #check if there's enough time in the empty window
                    if empty_window_end - empty_window_start > datetime.timedelta(minutes = obs_len):
                        #check if the pulsar sets after the needed observation time
                        if pulsar_window[1] >= empty_window_start + datetime.timedelta(minutes = obs_len):
                            #check if the pulsar rises before the needed observation time
                            if pulsar_window[0] <= empty_window_end - datetime.timedelta(minutes = obs_len):
                                schedule_item = [pulsar, obs_len, max(empty_window_start, pulsar_window[0]), priority]
                                break

                if schedule_item is not None:
                    schedule[timewindow[0]].append(schedule_item)
                    schedule[timewindow[0]].sort(key = lambda x : x[2])
                else:
                    continue

                if pulsar not in observed:
                    observed.append(pulsar)

                print("\t\t\t\tObserve P(" + str(priority) + ")", pulsar, "@", schedule_item[2].strftime(time_string), "for {:.2f}".format(obs_len - OBS_BUFFER_TIME), "+", OBS_BUFFER_TIME, "\tmin")

                marker = marker + datetime.timedelta(minutes = obs_len)

    print("-" * 50)
    print("FINAL OBSERVING SCHEDULE:")
    for window in schedule:
        print("Starting @ " + window.strftime(time_string) + ":")
        for pulsar_ind in range(len(schedule[window])):
            pulsar = schedule[window][pulsar_ind]
            
            print("\tObserve P" + str(pulsar[3]) + " " + pulsar[0] + " for {:.2f}".format(pulsar[1] - OBS_BUFFER_TIME, 2), "+", OBS_BUFFER_TIME, "minutes, starting @", pulsar[2].strftime(time_string))

            if pulsar_ind != len(schedule[window]) - 1:
                wait_time = schedule[window][pulsar_ind + 1][2] - (pulsar[2] + datetime.timedelta(minutes = pulsar[1]))
                if wait_time.seconds != 0:
                    print("\tWAIT", round(wait_time.seconds / 60, 2), "min")

    return schedule



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Create an observing schedule for target pulsars.')
    parser.add_argument('-w', '--windows', help = "Format, in minutes: start-end,start-end. Example: 0-60,120-180")

    args = parser.parse_args()

    if args.windows == None:
        args.windows = "0-60"

    windows = args.windows.split(",")
    windows = [[int(n) for n in el.split("-")] for el in windows]

    schedule = create_obs_schedule(PULSARS, windows)
