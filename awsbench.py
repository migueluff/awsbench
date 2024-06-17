import aws_bench.pricing_handler as aws
from aws_bench.constants import AWSConfig, SSHConfig, BenchmarkConfig

import boto3
from botocore.exceptions import ClientError
import os
import paramiko
import time
from datetime import datetime
# import click
from pathlib import Path
import argparse
import pandas as pd
from datetime import datetime
import re
import logging
from aws_bench.constants import LogConfig


def extract_info_from_text(text, info, df):
    data = {
        "Start_Time": info['Start_Time'],
        "End_Time": info['End_Time'],
        "Instance": info['Instance'],
        "Ondemand_Price": info['Ondemand_Price'],
        "Spot_Price": info['Spot_Price'],
        "Region": info['Region'],
        "Zone": info['Zone'],
        "Algorithm_Name": info["Algorithm_Name"],
        "Class": None,
        "Time_in_Seconds": None,
        "Total_Threads": None,
        "Available_Threads": None,
        "Mops_Total": None,
        "Mops_per_Thread": None,
        "Status": info['Status'],
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
    return df


def run_via_ssh(cmd, instance, region):
    if region == 'us-east-1':
        path_key = SSHConfig.path_key_us
    else:
        path_key = SSHConfig.path_key_sa

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


def get_file_name(region, instance):
    now = datetime.now()
    datetime_str = now.strftime("%Y%m%d_%H%M%S")
    file_name = f'{region}-{instance}-{datetime_str}.txt'
    return file_name


def __start_instance(region, instance_type, info={}):
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
        print(f'Tipo da instância: {instance_type}')
        print(f'Instância criada com ID: {instance.id}')
        print(f'Endereço Público: {instance.public_ip_address}')
        print(f'Endereço Privado: {instance.private_ip_address}')
        print(f'Endereço DNS Name: {instance.public_dns_name}')

        return instance

    except ClientError as e:
        BenchmarkConfig.STATUS = e.response['Error']['Code']
        logging.error(f"<EC2Manager>: Error to create instance: {e}")
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


def get_instance(region, instance_id):
    session = boto3.Session(aws_access_key_id=AWSConfig.aws_acess_key_id,
                            aws_secret_access_key=AWSConfig.aws_acess_secret_key,
                            region_name=region)

    ec2 = session.resource('ec2')
    instance = ec2.Instance(instance_id)
    print(f'Tipo da instância: {instance.instance_type}')
    print(f'Instância criada com ID: {instance.id}')
    print(f'Endereço Público: {instance.public_ip_address}')
    print(f'Endereço Privado: {instance.private_ip_address}')
    print(f'Endereço DNS Name: {instance.public_dns_name}')

    return instance




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


def benchmark(args):
    """
    :param region: Define the AWS region that the instance will be created
    :param availability_zone: Define the AWS availability zone that the instance will be created 
    :param repetitions: Number of executions inside the instance
    :return:
    """
    region = args.region
    repetions = args.repetitions
    json_file = args.json_file
    is_spot = args.spot

    json_file = Path(json_file)

    if not json_file.exists():
        print(f"File {json_file} not found")
        raise FileNotFoundError
    
    benchmark_config = BenchmarkConfig(json_file=json_file)

    df = pd.DataFrame(columns=benchmark_config.columns)

    star_test = datetime.now()
    csv_name = f"{region}_{star_test.year}-{star_test.month:02d}-{star_test.day:02d}_{star_test.strftime('%H-%M-%S')}.csv"

    for instance_type, instance_core in benchmark_config.vms.items():

        # check if the instance is available in the region


        start_time = datetime.now()
        try:
            ondemand_price = None
            spot_price = None
            if is_available(region, instance_type):
                ondemand_price = aws.get_price_ondemand(region, instance_type)
                spot_price = aws.get_price_spot(region, instance_type, region + AWSConfig.zone_letter)

            info = {}
            if is_spot:
                info =  {
                    'MarketType': 'spot',
                    'SpotOptions': {
                        'MaxPrice': str(ondemand_price),
                        'SpotInstanceType': 'one-time',
                        'InstanceInterruptionBehavior': 'terminate'}
                    }

            instance = __start_instance(region, instance_type, info)

            if instance:

                time.sleep(5)

                for i in range(repetions):
                    output = run_via_ssh(cmd=f'export OMP_NUM_THREADS={instance_core};./ep.D.x', instance=instance, region=region)
                    info_output = {
                        "Start_Time": start_time,
                        "End_Time": datetime.now(),
                        "Instance": instance_type,
                        "Ondemand_Price": ondemand_price,
                        "Spot_Price": spot_price,
                        "Region": region,
                        "Zone": instance.placement['AvailabilityZone'][-1:],
                        "Algorithm_Name": 'NAS Benchmark',
                        "Status": 'SUCCESS'
                    }
                    df = extract_info_from_text(output, info_output, df)

                _terminate_instance(instance)
            else:
                raise Exception(f'Instance {instance_type} not available')
        
        except Exception as e:
            info_output = {
                "Start_Time": start_time,
                "End_Time": datetime.now(),
                "Instance": instance_type,
                "Ondemand_Price": None,
                "Spot_Price": None,
                "Region": region,
                "Zone": None,
                "Algorithm_Name": 'NAS Benchmark',
                "Status": benchmark_config.STATUS
            }
            df = extract_info_from_text('', info_output, df)

    logging.info(f'Saving file: {csv_name}')
    df.to_csv(csv_name, index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark AWS')
    parser.add_argument('region', type=str, help='AWS region')
    parser.add_argument('json_file', type=str, help='Json file with instances configurations')
    parser.add_argument('--repetitions', type=int, default=5, help='Number of repetitions')
    parser.add_argument('--spot', type=bool, default=False, help='If you want spot instances')
    args = parser.parse_args()
    logging.info(f"Start execution in {args.region} N={args.repetitions} JsonFile={args.json_file}")
    benchmark(args)
    #start_spot_instance(args.region, 'c5a.12xlarge')
    # benchmark('us-east-1', 1, 'instance_info.json')
    # benchmark('sa-east-1', 1, 'instance_info.json')
