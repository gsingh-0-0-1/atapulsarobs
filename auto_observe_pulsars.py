#!/home/obsuser/miniconda3/envs/ATAobs/bin/python
import atexit
from ATATools import ata_control, logger_defaults
from SNAPobs import snap_dada, snap_if, snap_config
from SNAPobs.snap_hpguppi.auxillary import _block_until_key_has_value
from string import Template

import numpy as np
import sys
import time

import argparse
import logging

import os

import requests
import json

from SNAPobs.snap_hpguppi import snap_hpguppi_defaults as hpguppi_defaults
from SNAPobs.snap_hpguppi import record_in as hpguppi_record
from SNAPobs.snap_hpguppi import auxillary as hpguppi_auxillary

import datetime
import timeslots

def main():
    logger = logger_defaults.getProgramLogger("observe", 
            loglevel=logging.INFO)

    ant_list = snap_config.get_rfsoc_active_antlist()
    antlo_list = [ant+lo.upper() for ant in ant_list for lo in ['b', 'c']]
    
    
    freqs   = [1236]*len(ant_list)
    freqs_c = [1236+672]*len(ant_list)


    #ata_control.set_freq(freqs, ant_list, lo='b', nofocus=True)
    #time.sleep(20)
    #ata_control.set_freq(freqs_c, ant_list, lo='c', nofocus=True)
    #time.sleep(20)

    ata_control.reserve_antennas(ant_list)
    atexit.register(ata_control.release_antennas, ant_list, True)

    ORIG_OUT = sys.stdout
    f = open("sched.txt", "w")
    sys.stdout = f
    schedule = timeslots.create_obs_schedule(timeslots.PULSARS, [[2, 150]])
    f.close()
    sys.stdout = ORIG_OUT

    pulsar_list = []
    obs_times = []
    start_times = []

    for window in schedule:
        for item in schedule[window]:
            pulsar_list.append(item[0])
            obs_times.append(item[1] - timeslots.OBS_BUFFER_TIME)
            start_times.append(item[2])

    obs_times = [el * 60 for el in obs_times]

    d = hpguppi_defaults.hashpipe_targets_LoB
    d.update(hpguppi_defaults.hashpipe_targets_LoC)

    obs_time = 900
    obs_start_in = 10

    obsdirs = []

    #for source, this_start_time, this_obs_time in zip(pulsar_list, start_times, obs_times):
    for target_ind in range(len(pulsar_list)):
        source = pulsar_list[target_ind]
        this_obs_time = obs_times[target_ind]
        this_start_time = start_times[target_ind]

        now = datetime.datetime.now()
        diff_to_start = this_start_time - now
        minutes_to_start = round(diff_to_start.total_seconds() / 60, 2)

        if minutes_to_start < 0:
            print("DELAYED BY", minutes_to_start, "for", source)
        else:
            print("WAITING", minutes_to_start, "for", source)
            time.sleep(minutes_to_start * 60)

        now = datetime.datetime.now()

        if target_ind != len(pulsar_list) - 1:
            new_obs_time = min(this_obs_time, 60 * ((start_times[target_ind + 1] - now).total_seconds() / 60 - timeslots.OBS_BUFFER_TIME))
        else:
            new_obs_time = this_obs_time

        print("STARTING OBS FOR", source, "for", new_obs_time)
        ata_control.make_and_track_ephems(source, ant_list)

        ra, dec = ata_control.get_source_ra_dec(source)
        keyval_dict = {'RA_OFF0': ra, 'DEC_OFF0': dec}

        hpguppi_auxillary.publish_keyval_dict_to_redis(keyval_dict,
                d,
                postproc=False)
        

        hpguppi_record.block_until_post_processing_waiting(d)
        #print('Post proc is done for\n', d)

        # Start recording -- record_in does NOT block
        hpguppi_record.record_in(obs_start_in, new_obs_time,
                hashpipe_targets = d)
        print("Recording for %.2f seconds started..." %new_obs_time)
        time.sleep(new_obs_time + obs_start_in + 5)
            

    print(obsdirs)

if __name__ == "__main__":
    main()
