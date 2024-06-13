import json
from pathlib import Path
import os

class SSHConfig:
    json_path = 'instance_info.json'    
    ssh_key = os.getenv('SSH_KEY_AWS')
    path_key_us = '/home/miguelflj/.ssh/miguel_uff.pem'
    path_key_sa = '/home/miguelflj/.ssh/miguel_uff_sa.pem'

class AWSConfig:
    aws_acess_key_id = os.getenv('AWS_KEY_ID')
    aws_acess_secret_key = os.getenv('AWS_SECRET_KEY')
    zone_letter = 'a'
    bucket_name = 'awsbenchmiguel'

    image_setup = {
        'us-east-1_x86': {
            'imageId': 'ami-0181593242c397dbc',
            'sg': 'sg-0552b31e4e34033d1',
            #'key_name': 'miguel_pc_uffus'
            'key_name': 'miguel_uff'
        },
        'sa-east-1_x86': {
            'imageId': 'ami-004b93279410efd73',
            'sg': 'sg-0b37e99384d675ca2',
            #'key_name': 'miguel_pc_uffsa'
            'key_name': 'miguel_uff_sa'
        },
        'us-east-1_arm': {
            'imageId': 'ami-082628d95a1f16ab9',
            'sg': 'sg-0552b31e4e34033d1',
            #'key_name': 'miguel_pc_uffus'
            'key_name': 'miguel_uff'
        },
        'sa-east-1_arm': {
            'imageId': 'ami-01c82e87fdaf78361',
            'sg': 'sg-0b37e99384d675ca2',
            #'key_name': 'miguel_pc_uffsa'
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
    


