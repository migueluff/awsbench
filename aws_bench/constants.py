import json
from pathlib import Path
import os
import logging

class SSHConfig:
    json_path = 'instance_info.json'
    ssh_key = os.getenv('SSH_KEY_AWS')
    #path_key_us = '/home/miguelflj/.ssh/miguel_uff.pem'
    #path_key_sa = '/home/miguelflj/.ssh/miguel_uff_sa.pem'
    path_key_us = '/home/miguel/.ssh/miguel_pc_uffus.pem'
    path_key_sa = '/home/miguel/.ssh/miguel_pc_uffsa.pem'


class AWSConfig:
    aws_acess_key_id = os.getenv('AWS_KEY_ID')
    aws_acess_secret_key = os.getenv('AWS_SECRET_KEY')
    zone_letter = 'a'
    bucket_name = 'awsbenchmiguel'

    image_setup = {
        'us-east-1_x86': {
            'imageId': 'ami-0181593242c397dbc',
            'sg': 'sg-0552b31e4e34033d1',
            'sg': 'sg-0552b31e4e34033d1',
            'key_name': 'miguel_pc_uffus'
            #'key_name': 'miguel_uff'
        },
        'sa-east-1_x86': {
            'imageId': 'ami-004b93279410efd73',
            'sg': 'sg-0b37e99384d675ca2',
            'key_name': 'miguel_pc_uffsa'
            #'key_name': 'miguel_uff_sa'
        },
        'us-east-1_arm': {
            'imageId': 'ami-082628d95a1f16ab9',
            'sg': 'sg-0552b31e4e34033d1',
             'key_name': 'miguel_pc_uffus'
            #'key_name': 'miguel_uff'
        },
        'sa-east-1_arm': {
            'imageId': 'ami-01c82e87fdaf78361',
            'sg': 'sg-0b37e99384d675ca2',
             'key_name': 'miguel_pc_uffsa'
            #'key_name': 'miguel_uff_sa'
        }
    }


class LogConfig:
    logging.basicConfig(
        #filename='awsbench.log',  # Name of the log file
        level=logging.INFO,  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(asctime)s - %(levelname)s - %(message)s',  # Log message format
        datefmt='%Y-%m-%d %H:%M:%S'  # Date format

    )


class BenchmarkConfig:
    columns = [
        "Start_Time",
        "End_Time",
        "Instance",
        "Ondemand_Price",
        "Spot_Price",
        "Region",
        "Zone",
        "Algorithm_Name",
        "Class",
        "Time_in_Seconds",
        "Total_Threads",
        "Available_Threads",
        "Mops_Total",
        "Mops_per_Thread",
        "Status"
    ]
    def __init__(self, json_file: Path) -> None:
        # load json file
        with open(json_file, 'r') as file:
            self.vms = json.load(file)
