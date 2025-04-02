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
            'imageId': 'ami-0181593242c397dbc',
            'sg': 'sg-0552b31e4e34033d1',
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

    INSTANCES_BY_REGION = {
    'us-east-1': [
        'c5.2xlarge-4', 'c5a.2xlarge-4', 'c5n.18xlarge-36', 'c5.24xlarge-48', 'c5a.24xlarge-48', 'c5ad.24xlarge-48', 
        'c5d.24xlarge-48', 'c6a.24xlarge-48', 'c6id.24xlarge-48', 'c6in.24xlarge-48', 'm5.24xlarge-48', 'm5a.24xlarge-48', 
        'm5ad.24xlarge-48', 'm5d.24xlarge-48', 'm5dn.24xlarge-48', 'm5n.24xlarge-48', 'm6a.24xlarge-48', 'm6i.24xlarge-48', 
        'm6in.24xlarge-48', 'm7a.24xlarge-48', 'm7i.24xlarge-48', 'r5.24xlarge-48', 'r5a.24xlarge-48', 'r5ad.24xlarge-48', 
        'r5b.24xlarge-48', 'r5d.24xlarge-48', 'r5dn.24xlarge-48', 'r5n.24xlarge-48', 'r6a.24xlarge-48', 'r6i.24xlarge-48', 
        'r6id.24xlarge-48', 'r6idn.24xlarge-48', 'r6in.24xlarge-48', 'r7a.24xlarge-48', 'r7i.24xlarge-48', 'c6i.32xlarge-64', 
        'c7a.48xlarge-96', 'c7i.48xlarge-96'
    ],
    'sa-east-1': [
        'c5.2xlarge-4', 'c5a.2xlarge-4', 'c5n.18xlarge-36', 'c5.24xlarge-48', 'c5a.24xlarge-48', 'c5ad.24xlarge-48', 
        'c5d.24xlarge-48', 'c6a.24xlarge-48', 'c6id.24xlarge-48', 'c6in.24xlarge-48', 'm5.24xlarge-48', 'm5a.24xlarge-48', 
        'm5ad.24xlarge-48', 'm5d.24xlarge-48', 'm6a.24xlarge-48', 'm6i.24xlarge-48', 'm7i.24xlarge-48', 'r5.24xlarge-48', 
        'r5a.24xlarge-48', 'r5ad.24xlarge-48', 'r5b.24xlarge-48', 'r5d.24xlarge-48', 'r5n.24xlarge-48', 'r6i.24xlarge-48', 
        'r7i.24xlarge-48', 'c6i.32xlarge-64', 'c7i.48xlarge-96'
    ]
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
        "Allocation_Strategy",
        "Class",
        "Time_in_Seconds",
        "Total_Threads",
        "Available_Threads",
        "Mops_Total",
        "Mops_per_Thread",
        "Status"
    ]
    '''
    def __init__(self, json_file: Path) -> None:
        # load json file
        with open(json_file, 'r') as file:
            self.vms = json.load(file)
    '''
  