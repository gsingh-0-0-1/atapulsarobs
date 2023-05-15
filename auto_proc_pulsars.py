import requests
import json
import subprocess
import requests

MAIN_STEM = "/mnt/datac-netStorage-40G/projects/p009/"

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

#requests.get("http://10.10.1.31:8080/exec/procobs/" + target_dir)

#subprocess.Popen(["/home/gsingh/pulsar_analysis/ar_image_gen.sh", target_dir])

subprocess.Popen(["ssh", "gsingh@obs-node1",  "cd pulsar_analysis; conda activate pulsar; ./ar_image_gen.sh " + target_dir])

