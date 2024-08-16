import json
from pathlib import Path
import os

class SSHConfig:
    json_path = 'instance_info.json'
    path_key_us = os.getenv('SSH_KEY_AWS_US')
    path_key_sa = os.getenv('SSH_KEY_AWS_SA')
    key_name_us = path_key_us.split('/')[-1].split('.')[0]
    key_name_sa = path_key_sa.split('/')[-1].split('.')[0]  
   


class AWSConfig:
    aws_acess_key_id = os.getenv('AWS_KEY_ID')
    aws_acess_secret_key = os.getenv('AWS_SECRET_KEY')
    zone_letter = 'a'
    bucket_name = 'awsbenchmiguel'

    image_setup = {
        'us-east-1_x86': {
            'imageId': 'ami-01f4e37b183434fde',
            'sg': 'sg-0552b31e4e34033d1',
            'key_name': SSHConfig.key_name_us
        },
        'sa-east-1_x86': {
            'imageId': 'ami-004b93279410efd73',
            'sg': 'sg-0b37e99384d675ca2',
            'key_name': SSHConfig.key_name_sa
        },
        'us-east-1_arm': {
            'imageId': 'ami-082628d95a1f16ab9',
            'sg': 'sg-0552b31e4e34033d1',
             'key_name': SSHConfig.key_name_us
        },
        'sa-east-1_arm': {
            'imageId': 'ami-01c82e87fdaf78361',
            'sg': 'sg-0b37e99384d675ca2',
             'key_name': SSHConfig.key_name_sa
        }
    }




class BenchmarkConfig:
    STATUS = None
    columns = [
        "Start_Time",
        "End_Time",
        "Instance",
        "InstanceID",
        "Price",
        "Market",        
        "Region",
        "Zone",
        "Algorithm_Name",
        "Class",
        "Time_in_Seconds",
        "Total_Threads",
        "Available_Threads",
        "Mops_Total",
        "Mops_per_Thread",
        "Status",
        "Cores"

    ]
    def __init__(self, json_file: Path) -> None:
        # load json file
        with open(json_file, 'r') as file:
            self.vms = json.load(file)

  