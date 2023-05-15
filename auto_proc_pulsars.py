import requests
import json
import subprocess
import os
import redis
from hashpipe_keyvalues.standard import HashpipeKeyValues


MAIN_STEM = "/mnt/datac-netStorage-40G/projects/p009/"
'''
hpkv = HashpipeKeyValues(
    "seti-node1",
    0,
    redis.Redis("redishost", decode_responses=True)
)
print(os.path.join(*hpkv.observation_stempath))
'''

host = "10.10.0.3"
port = "8081"

nodehost = "seti-node1"
instnum = "0"

hashpipe_data_req = requests.get("http://" + host + ":" + port + "/hashpipestatus?nodehostname=" + nodehost + "&instancenum=" + instnum)
hashpipe_data_res = hashpipe_data_req.text

hashpipe_data = json.loads(hashpipe_data_res)


postproc_data_req = requests.get("http://" + host + ":" + port + "/postprocstatus?nodehostname=" + nodehost + "&instancenum=" + instnum)
postproc_data_res = postproc_data_req.text

postproc_data = json.loads(postproc_data_res)

target_dir = postproc_data['CPDELAYARG']

target_dir = target_dir.replace(MAIN_STEM, "").split("/")[0]

subprocess.Popen(["/home/gsingh/pulsar_analysis/ar_image_gen.sh", target_dir])
