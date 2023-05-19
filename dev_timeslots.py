import os
import subprocess
import argparse

from astropy.coordinates import EarthLocation, SkyCoord, AltAz
from astropy.time import Time
from astropy import units as u

import datetime
import numpy as np
import pandas as pd

ATA_PULSAR_DATA = pd.read_csv("PULSARS.csv")

ATA_PULSARS = PULSARS = list(ATA_PULSAR_DATA["PULSAR"])

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

OBS_BUFFER_TIME = 2

PSRCAT_PARAMS = [
    'PSRJ',
    'RAJ',
    'DECJ',
    'S1400'
    ]

ATA = EarthLocation(lat = 40.8175, lon = -121.47333)

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

        availability.append(available)

    return availability


class Window:
    def __init__(self, beg, end, target = None):
        self.beg = beg
        self.end = end
        self.target = target

    def len(self):
        return self.end - self.beg

    def rawlen(self):
        return self.len().total_seconds()

class Schedule:
    def __init__(self, beg, end, targets, buf = OBS_BUFFER_TIME):
        self.now = datetime.datetime.now()
        self.beg = self.now + datetime.timedelta(minutes = beg)
        self.end = self.now + datetime.timedelta(minutes = end)
        self.avail = []
        self.sched = []

        self.buf = buf
        self.ORIG_TARGETS = targets
        self.targets = targets
        self.obstimes = []

        self.avail.append(Window(self.beg, self.end))

    def timefmt(self, dt):
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def time(self, mins):
        return self.now + datetime.timedelta(minutes = mins)

    def set_targets(self, targets):
        self.targets = targets

    def set_buf(self, buf):
        self.buf = buf

    def get_longest_availability(self):
        max_len = 0
        for window in self.avail:
            if window.rawlen() > max_len:
                max_len = window.rawlen()

        return max_len

    def get_shortest_obstime(self):
        return min(self.obstimes)

    def compute_target_obstime(self, target):
        fluxdens = float(fetch_pulsar_data(target, "S1400"))
        basetime = MIN_OBS_TIME + OBS_TIME_RANGE * ((max(FLUX_DENS_HIGH_PLAT - fluxdens, 0) / FLUX_DENS_HIGH_PLAT) ** (1 / 2))
        maxtime = MAX_OBS_TIME
        obstime = self.buf + min(basetime, MAX_OBS_TIME)

        obstime = min( max( MIN_OBS_TIME, MIN_OBS_TIME / ((fluxdens / FLUX_DENS_HIGH_PLAT) ** 2)), MAX_OBS_TIME) + self.buf

        return obstime * 60

    def compute_target_obstimes(self):
        self.obstimes = []
        for target in self.targets:
            t = self.compute_target_obstime(target)
            self.obstimes.append(t)

    def split_avail_window(self, index, dt):
        original_window = self.avail[index]
        new_first = Window(original_window.beg, dt)
        new_second = Window(dt, original_window.end)
        del self.avail[index]
        self.avail.insert(index, new_first)
        self.avail.insert(index + 1, new_second)

    def reserve_window(self, index, target):
        window = self.avail[index]
        del self.avail[index]
        window.target = target
        self.sched.append(window)
        self.sched.sort(key = lambda x : x.beg)

    def schedule_item(self, beg_avail, end_avail, tlen, target):
        #dt beg_avail
        #dt end_avail
        #int tlen
        #str target
        
        #tstart = self.time(beg_avail)
        #tend = self.time(end_avail)
        #tlen = tend - tstart

        obs_del = datetime.timedelta(seconds = tlen)

        for window_ind in range(len(self.avail)):
            window = self.avail[window_ind]
            if (window.end >= beg_avail + obs_del and 
                    window.beg + obs_del <= end_avail and
                    window.len() > obs_del):
            #if tstart >= window.beg and window.len() > tlen:
                if beg_avail <= window.beg:
                    self.split_avail_window(window_ind, window.beg + obs_del)
                    sched_ind = window_ind
                else:
                    self.split_avail_window(window_ind, beg_avail)
                    self.split_avail_window(window_ind + 1, beg_avail + obs_del)
                    sched_ind = window_ind + 1
        
                self.reserve_window(sched_ind, target)

                break

    def schedule_targets(self):
        self.targets = self.ORIG_TARGETS

        self.compute_target_obstimes()
        while self.get_longest_availability() > self.get_shortest_obstime():
            target = self.targets[0]
            t = self.obstimes[0]
            target_avail = check_pulsar_availability(target, [[self.beg, self.end]])
            if target_avail[0][0]:
                self.schedule_item(target_avail[0][0], target_avail[0][1], t, target)

            del self.targets[0]
            del self.obstimes[0]

            if target_avail[0][0]:
                self.targets.append(target)
                self.obstimes.append(t)
            
            if len(self.targets) == 0:
                break

        self.print()


    def print(self):
        temp = self.sched + self.avail
        temp.sort(key = lambda x : x.beg)
        for window in temp:
            print("@", self.timefmt(window.beg))
            t = window.rawlen()
            if window.target is None:
                print("\tWAIT \t\t\tfor {:.2f} s".format(t))
            else:
                print("\tOBSERVE", window.target, "\tfor {:.2f} + {:.2f} s".format(t - self.buf * 60, self.buf * 60))

    '''
    Returns a schedule in the form of a list, with each entry formatted as:

    [target / WAIT, begin_time, len]

    All times are in seconds
    '''
    def get_formatted_schedule(self):
        ret = []
        temp = self.sched + self.avail
        temp.sort(key = lambda x : x.beg)
        for window in temp:
            t = window.rawlen()
            new = []
            if window.target is None:
                new = ["WAIT", window.beg, t]
            else:
                new = [window.target, window.beg, t - self.buf * 60]
            ret.append(new)

        return ret

