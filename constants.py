import json

region_names = ['sa-east-1','us-east-1']
json_path = 'instance_info.json'
path_private_key = '/home/miguelflj/.ssh/miguel_uff.pem'
bucket_name = 'awsbenchmiguel'
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


imageId_us = 'ami-01c525d817b06bbda'
sg_us = 'sg-0552b31e4e34033d1'
key_name_us = 'miguel_uff'

sg_sa = 'sg-0b37e99384d675ca2'
imageId_sa = 'ami-011a75089588f3f88'
key_name_sa = 'miguel_uff_sa'

imageID_us_arm = 'ami-01a2cf5434bbbd75f'

with open(json_path, 'r') as file:
    instance_info = json.load(file)