#!/usr/bin/env python3

import aws_bench.pricing_handler as aws
from aws_bench.constants import AWSConfig, SSHConfig, BenchmarkConfig

import boto3
from botocore.exceptions import ClientError
import paramiko
import time
from datetime import datetime
from pathlib import Path
import argparse
import pandas as pd
from datetime import datetime
import re
import logging



def save_row(text, row, df, csv_file):
    
    data = {
        "Start_Time": row['Start_Time'],
        "End_Time": row['End_Time'],
        "Instance": row['Instance'],
        "InstanceID": row['InstanceID'],
        "Market": row['Market'],
        "Price": row['Price'],        
        "Region": row['Region'],
        "Zone": row['Zone'],
        "Algorithm_Name": row["Algorithm_Name"],
        "Class": None,
        "Time_in_Seconds": None,
        "Total_Threads": None,
        "Available_Threads": None,
        "Mops_Total": None,
        "Mops_per_Thread": None,
        "Status": row['Status'],
    }
    regex_patterns = {
        "Class": re.compile(r"Class\s*=\s*(\S+)"),
        "Time_in_Seconds": re.compile(r"Time in seconds\s*=\s*([\d.]+)"),
        "Total_Threads": re.compile(r"Total threads\s*=\s*(\d+)"),
        "Available_Threads": re.compile(r"Avail threads\s*=\s*(\d+)"),
        "Mops_Total": re.compile(r"Mop/s\s*total\s*=\s*([\d.]+)", re.IGNORECASE),
        "Mops_per_Thread": re.compile(r"Mop/s/thread\s*=\s*([\d.]+)", re.IGNORECASE)

    }
    

    for key, pattern in regex_patterns.items():
        match = pattern.search(text)
        if match:
            data[key] = match.group(1)
        else:
            data[key] = None

    df.loc[len(df)] = data

    logging.info(f'Updating file: {csv_file}')
    df.to_csv(csv_file, index=False)

    return df


def run_via_ssh(cmd, instance, region):
    try:
        path_key = SSHConfig.path_key_us if region == 'us-east-1' else SSHConfig.path_key_sa

        lifecycle = instance.instance_lifecycle
        if lifecycle is None:
            lifecycle = 'on-demand'

        logging.info(f"Running command: {cmd} in instance {instance.id} Region: {region} Market: {lifecycle}")

        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(instance.public_ip_address,
                username="ubuntu",
                key_filename=path_key,
                allow_agent=False, look_for_keys=False)
        stdin, stdout, stderr = c.exec_command(cmd)
        output = stdout.read().decode()
        c.close()
        return output
    except Exception as e:
        logging.error(f"Error running command in instance {instance.id}: {e}")
        return None

def __start_instance(region, instance_type, info):
    session = boto3.Session(aws_access_key_id=AWSConfig.aws_acess_key_id,
                            aws_secret_access_key=AWSConfig.aws_acess_secret_key,
                            region_name=region)

    resource = session.resource('ec2')

    architecture = 'arm' if 'g' in instance_type.split('.')[0] else 'x86'
    dict_key = f'{region}_{architecture}'

    try:
        instances = resource.create_instances(ImageId=AWSConfig.image_setup[dict_key]['imageId'],
                                              InstanceType=instance_type,
                                              KeyName=AWSConfig.image_setup[dict_key]['key_name'],
                                              MaxCount=1,
                                              MinCount=1,
                                              SecurityGroupIds=[AWSConfig.image_setup[dict_key]['sg']],
                                              InstanceMarketOptions=info,
                                              TagSpecifications=[{'ResourceType': 'instance',
                                                                  'Tags': [{'Key': 'Name',
                                                                            'Value': 'awsbench'}]}])

        assert len(instances) == 1  # only one instance should be created
        instance = instances[0]
        instance.wait_until_running()
        instance.reload()
        logging.info(f'Instace Type: {instance_type}')
        logging.info(f'Instance ID: {instance.id}')        
        return instance

    except ClientError as e:
        BenchmarkConfig.STATUS = e.response['Error']['Code']
        logging.error(f"<EC2Manager>: Error to create instance {instance_type} in region {region}: {e}")
        return None


def _terminate_instance(instance):
    # if instance is spot, we have to remove its request
    client = boto3.client('ec2', region_name=instance.placement['AvailabilityZone'][:-1])

    if instance.instance_lifecycle == 'spot':
        client.cancel_spot_instance_requests(
            SpotInstanceRequestIds=[
                instance.spot_instance_request_id
            ]
        )
                
    instance.terminate()
    instance.wait_until_terminated()
    logging.info(f"Instance {instance.id} has been terminated.")


def is_available(region, instance_type):

    session = boto3.Session(aws_access_key_id=AWSConfig.aws_acess_key_id,
                            aws_secret_access_key=AWSConfig.aws_acess_secret_key,
                            region_name=region)

    ec2 = session.client('ec2')
    try:
        response = ec2.describe_instance_types(InstanceTypes=[instance_type])
        return len(response['InstanceTypes']) > 0
    except ClientError as e:
        return False


def create_fleet(region, cluster_size, allocation_strategy, target_capacity):
    """
    Cria uma frota de instâncias EC2 usando `create_fleet`.

    :param region: Região AWS onde a frota será criada
    :param cluster_size: Número de instâncias a serem lançadas
    :param allocation_strategy: Estratégia de alocação (ex: 'lowest-price', 'capacity-optimized')
    :param target_capacity: Capacidade alvo da frota
    :return: Lista de instâncias iniciadas
    """
    overrides = []
    for instance in AWSConfig.INSTANCES_BY_REGION[region]:
            overrides.append({'InstanceType': instance.split("-")[0]})
            
    session = boto3.Session(
        aws_access_key_id=AWSConfig.aws_acess_key_id,
        aws_secret_access_key=AWSConfig.aws_acess_secret_key,
        region_name=region
    )
    
    ec2_client = session.client("ec2")
    ec2_resource = session.resource("ec2")

    launch_template_config = [
        {
            "LaunchTemplateSpecification": {
                "LaunchTemplateName": "Spotfleet_Launch",
                "Version": "$Latest"
            },
            "Overrides": overrides  
        }
    ]

    fleet_config = {
        "LaunchTemplateConfigs": launch_template_config,
        "TargetCapacitySpecification": {
            "TotalTargetCapacity": target_capacity,
            "DefaultTargetCapacityType": "spot"
        },
        "SpotOptions": {
            "AllocationStrategy": allocation_strategy
            #"MaxTotalPrice": str(spot_price) if spot_price else None
        },
        "Type": "instant",
        "TagSpecifications" : [{
                'ResourceType': 'instance',
                'Tags':[{'Key': 'Name', 'Value': 'SpotFleet-SSCAD'}]
        }]
    }

    try:
        response = ec2_client.create_fleet(**fleet_config)
        #print(response)
        instance_ids = [inst for fleet in response.get("Instances", []) for inst in fleet["InstanceIds"]]
        
        if instance_ids:
            logging.info(f"Fleet created with instances: {instance_ids}")
        else:
            logging.warning("No instances were launched.")
            return []
   
        instances = list(ec2_resource.instances.filter(InstanceIds=instance_ids))
        for instance in instances:
            instance.wait_until_running()
            instance.reload()

        return instances
    
    except ClientError as e:
        logging.error(f"Error creating fleet in region {region}: {e}")
        return []



def benchmark(args):
    """
    :param region: Define the AWS region that the instance will be created
    :param availability_zone: Define the AWS availability zone that the instance will be created 
    :param repetitions: Number of executions inside the instance
    :return:
    """
    region = args.region
    #repetions = args.repetitions  
    is_spot = True
    app = args.benchmark
    #json_file = Path(args.json_file)
    allocation_strategy = args.strategy
    nodes = int(args.nodes)
    '''
    if not json_file.exists():
        logging.error(f"File {json_file} not found")
        raise FileNotFoundError
    ''' 
    benchmark_config = BenchmarkConfig()
    market = 'spot' if is_spot else 'ondemand'    
    csv_file = Path(args.output_folder, f"results_{region}.csv")

    if csv_file.exists():
        df = pd.read_csv(csv_file)
    else:
        df = pd.DataFrame(columns=benchmark_config.columns)

   
        

    instances = create_fleet(region,cluster_size=nodes, allocation_strategy=allocation_strategy, target_capacity=nodes)

    if instances:
        logging.info(f"Instâncias iniciadas: {instances}")
    else:
        logging.error("Falha ao iniciar instâncias.")
        return 0
   
    for instance in instances:
        start_time = datetime.now()

        instance_type = instance.instance_type

        for instance_verify in AWSConfig.INSTANCES_BY_REGION[region]:
            if instance_type in instance_verify:
                instance_core = instance_verify.split("-")[1]

        try:
            price = None 
        
            if is_available(region, instance_type):
                price_spot = aws.get_price_spot(region, instance_type, region + AWSConfig.zone_letter)
                price_ondemand = aws.get_price_ondemand(region, instance_type)
            
                price = price_spot if is_spot else price_ondemand


            info = {}

            if is_spot:
                info =  {
                    'MarketType': 'spot',
                    'SpotOptions': {
                        'MaxPrice': '10.0',
                        'SpotInstanceType': 'one-time',
                        'InstanceInterruptionBehavior': 'terminate'}
                    }   
            
        
            # if instance is not None, we can run the benchmark
        
            #time.sleep(15)
                
            logging.info(f"Binding threads in cores, instance have {instance_core} cores")

            #app = 'ep.D.x'
            output = run_via_ssh(cmd=f'export OMP_PLACES=cores;export OMP_PROC_BIND=spread;export '
                                        f'OMP_NUM_THREADS={instance_core};./{app}', instance=instance,
                                            region=region)
                    
            print(output)

            row = {"Start_Time": start_time,
                    "End_Time": datetime.now(),
                    "Instance": instance_type,
                    "InstanceID": instance.id,
                    "Market": market,
                    "Price":  price,                               
                    "Region": region,
                    "Zone": instance.placement['AvailabilityZone'][-1:],
                    "Algorithm_Name": app,
                    "Allocation_Strategy": allocation_strategy,
                    "Status": 'SUCCESS'}
            
            print(row)
            df = save_row(output, row, df, csv_file)
            #execution_count += 1

            _terminate_instance(instance)


        except Exception as e:
            row = { "Start_Time": start_time,
                    "End_Time": datetime.now(),
                    "Instance": instance_type,
                    "InstanceID": None,
                    "Market": market,
                    "Price": None,                
                    "Region": region,
                    "Zone": None,
                    "Algorithm_Name": {app},
                    "Allocation_Strategy": allocation_strategy,
                    "Status": BenchmarkConfig.STATUS}
            
            df = save_row('', row, df, csv_file)

                
        


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark AWS')
    parser.add_argument('region', type=str, help='AWS region')
    #parser.add_argument('json_file', type=str, help='Json file with instances configurations')
    parser.add_argument('strategy', type=str, default='lowest-price', choices=['lowest-price', 'diversified', 'capacity-optimized', 'capacity-optimized-prioritized', 'price-capacity-optimized'], help='Allocation Strategy')
    parser.add_argument('benchmark', type=str,default='ep.D.x', choices=['ep.A.x','ep.B.x','ep.D.x','ep.E.x'])
    #parser.add_argument('--repetitions', type=int, default=5, help='Number of repetitions')
    parser.add_argument('--nodes', type=int, default=1, help='Number of repetitions')
    parser.add_argument('--output_folder', type=str, default='.', help='Output folder')
    #parser.add_argument('--spot', action='store_true', help='Use spot instances')
    parser.add_argument('--log', action='store_true', help='Log file')

    args = parser.parse_args()

    if args.log:
        # write the log in the stdout
        logging.basicConfig(level=logging.INFO,  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                            format='%(asctime)s - %(levelname)s - %(message)s',  # Log message format
                            datefmt='%Y-%m-%d %H:%M:%S')
    else:
        logging.basicConfig(filename=f'{args.output_folder}/{args.region}_awsbench.log',  # Name of the log file
                            level=logging.INFO,  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                            format='%(asctime)s - %(levelname)s - %(message)s',  # Log message format
                            datefmt='%Y-%m-%d %H:%M:%S')
        
    logging.info(f"Start execution in {args.region} Nodes={args.nodes} Benchmark={args.benchmark} Allocation Strategy={args.strategy}") 
    benchmark(args)