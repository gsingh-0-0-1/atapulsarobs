import os
import subprocess

from astropy.coordinates import EarthLocation, SkyCoord, AltAz
from astropy.time import Time
from astropy import units as u

import datetime
import numpy as np

ATA_LAT = 40.8178
ATA_LON = 121.473


ATA = EarthLocation.of_site("Allen Telescope Array")


PSRCAT_PARAMS = [
    'PSRJ',
    'RAJ',
    'DECJ',
    'S1400'
    ]

def fetch_pulsar_data(pulsar):
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

    return result.split(" ")

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
        delta = datetime.timedelta(minutes = 30)

        timewindows = [[now - delta, now + delta]]
    
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

        search_delta = datetime.timedelta(minutes = 1)

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


        #and now check for the end
        if el_end >= 20:
            available.append(window[1])
        else:
            #if the object was available earlier on in the window,
            #then we can check for when it sets
            if available[0]:
                object_sets = window[1]
                az = az_end
                el = el_beg
                while el < 20:
                    object_sets = object_sets - search_delta

                    #since the object was available at the beginning, we don't have to check
                    #for the object_sets time being less than the start

                    az, el = radec_to_azel(RAJ_fmt, DECJ_fmt, object_sets)

                available.append(object_sets)
            #otherwise we know the object is not visible during the window
            else:
                available.append(False)


        availability.append(available)

    return availability
