import json
from pathlib import Path
import os

class SSHConfig:
    json_path = 'instance_info.json'    
    ssh_key = os.getenv('SSH_KEY_AWS')

class AWSConfig:
    aws_acess_key_id = os.getenv('AWS_KEY_ID')
    aws_acess_secret_key = os.getenv('AWS_SECRET_KEY')
    zone_letter = 'a'
    bucket_name = 'awsbenchmiguel'

    image_setup = {
        'us-east-2_x86': {
            'imageId': 'ami-09040d770ffe2224f',
            'sg': 'sg-0a0e007b42a445d0e',
            'key_name': 'aws_key2'
        },
        'us-east-1_x86': {
            'imageId': 'ami-01c525d817b06bbda',
            'sg': 'sg-0552b31e4e34033d1',
            'key_name': 'miguel_uff'
        },
        'sa-east-1_x86': {
            'imageId': 'ami-011a75089588f3f88',
            'sg': 'sg-0b37e99384d675ca2',
            'key_name': 'miguel_uff_sa'
        },
        'us-east-1_arm': {
            'imageId': 'ami-01a2cf5434bbbd75f',
            'sg': 'sg-0552b31e4e34033d1',
            'key_name': 'miguel_uff'
        },
        'sa-east-1_arm': {
            'imageId': 'ami-04c591ef4b3cdb92a',
            'sg': 'sg-0b37e99384d675ca2',
            'key_name': 'miguel_uff_sa'
        }
    }


class BenchmarkConfig:
    columns = [
        'algorithm_name',
        'Class',
        'Time_in_Seconds',
        'Total_Threads',
        'Available_Threads',
        'Mops_total',
        'Mops_per_thread',
        'region',
        'Instance_name',
        'timestamp',
        'Ondemand_price',
        'Spot_price'
    ]

    def __init__(self, json_file : Path) -> None:
        # load json file
        with open(json_file, 'r') as file:
            self.vms = json.load(file)
    


