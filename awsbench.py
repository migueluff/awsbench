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


def extract_info_from_text(text, region, instance_type,ondemand_price,spot_price, df):
    data = {
        "algorithm_name": 'EP Benchmark',
        "Class": None,
        "Time_in_Seconds": None,
        "Total_Threads": None,
        "Available_Threads": None,
        "Mops_total": None,
        "Mops_per_thread": None,
        "Ondemand_price": None,
        "Spot_price": None
    }

    # Regular expressions to match each line of interest
    regex_patterns = {
        "Class": re.compile(r"Class\s*=\s*(\S+)"),
        "Time_in_Seconds": re.compile(r"Time in seconds\s*=\s*([\d.]+)"),
        "Total_Threads": re.compile(r"Total threads\s*=\s*(\d+)"),
        "Available_Threads": re.compile(r"Avail threads\s*=\s*(\d+)"),
        "Mops_total": re.compile(r"Mop/s\s*total\s*=\s*([\d.]+)", re.IGNORECASE),
        "Mops_per_thread": re.compile(r"Mop/s/thread\s*=\s*([\d.]+)", re.IGNORECASE)

    }

    for key, pattern in regex_patterns.items():
        match = pattern.search(text)
        if match:
            data[key] = match.group(1)

    data['region'] = region + AWSConfig.zone_letter
    data['Instance_name'] = instance_type
    data['timestamp'] = datetime.now()
    data['Ondemand_price'] = ondemand_price
    data['Spot_price'] = spot_price
    data['STATUS'] = 'SUCCESS'
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


def start_instance(region, instance_type, max_retries=3, retry_backoff=2):
    session = boto3.Session(aws_access_key_id=AWSConfig.aws_acess_key_id,
                            aws_secret_access_key=AWSConfig.aws_acess_secret_key,
                            region_name=region)

    ec2 = session.resource('ec2')

    architecture = 'arm' if 'g' in instance_type.split('.')[0] else 'x86'
    dict_key = f'{region}_{architecture}'
    azs = ['a','b','c']
    retry_count = 0
    while retry_count < max_retries:
        for az in azs:
            try:
                instances = ec2.create_instances(
                    ImageId=AWSConfig.image_setup[dict_key]['imageId'],
                    MinCount=1,
                    MaxCount=1,
                    InstanceType=instance_type,
                    KeyName=AWSConfig.image_setup[dict_key]['key_name'],
                    SecurityGroupIds=[AWSConfig.image_setup[dict_key]['sg']],
                    Placement={'AvailabilityZone': region+az}
                )

                assert len(instances) == 1  # only one instance should be created

                instance = instances[0]
                AWSConfig.zone_letter = az
                instance.wait_until_running()
                instance.reload()
                print(f'Tipo da instância: {instance_type}')
                print(f'Instância criada com ID: {instance.id}')
                print(f'Endereço Público: {instance.public_ip_address}')
                print(f'Endereço Privado: {instance.private_ip_address}')
                print(f'Endereço DNS Name: {instance.public_dns_name}')

                return instance
            except ClientError as e:
                print(f'Error in {az}: {e}')
                logging.exception(f'Error in {region+az}: {e}')
                if 'InsufficientInstanceCapacity' in str(e):
                    print('InsufficientInstanceCapacity')
                    BenchmarkConfig.STATUS = 'InsufficientInstanceCapacity'
                    continue
                elif 'Unsupported' in str(e):
                    BenchmarkConfig.STATUS = 'Unsupported'
                    retry_count = max_retries # sai do laço, nao vai arrumar a instância
                else:
                    BenchmarkConfig.STATUS = 'Error'
                    raise
        retry_count += 1
        wait_time = retry_backoff ** retry_count
        print(f"Retrying in {wait_time} seconds...")
        time.sleep(wait_time)
        raise Exception("Max retries reached. Could not create instance.")


def start_spot_instance(region, instance_type):
    session = boto3.Session(aws_access_key_id=AWSConfig.aws_acess_key_id,
                            aws_secret_access_key=AWSConfig.aws_acess_secret_key,
                            region_name=region)

    ec2_client = session.client('ec2')
    architecture = 'arm' if 'g' in instance_type.split('.')[0] else 'x86'
    dict_key = f'{region}_{architecture}'
    spot_request = {
        'InstanceCount': 1,
        'Type': 'one-time',
        'LaunchSpecification': {
            'ImageId': AWSConfig.image_setup[dict_key]['imageId'],
            'InstanceType': instance_type,
            'KeyName': AWSConfig.image_setup[dict_key]['key_name'],
            'SecurityGroupIds': [AWSConfig.image_setup[dict_key]['sg']],
            'Placement': {
                'AvailabilityZone': region + AWSConfig.zone_letter
            }
        }
    }
    response = ec2_client.request_spot_instances(**spot_request)
    spot_instance_request_ids = [req['SpotInstanceRequestId'] for req in response['SpotInstanceRequests']]
    print(f"Spot Instance Request IDs: {spot_instance_request_ids}")


    instance_ids = []
    while not instance_ids:
        describe_response = ec2_client.describe_spot_instance_requests(SpotInstanceRequestIds=spot_instance_request_ids)
        print("Waiting for Spot Instances to be fulfilled...")
        for request in describe_response['SpotInstanceRequests']:
            if 'InstanceId' in request:
                instance_ids.append(request['InstanceId'])
        if not instance_ids:
            time.sleep(10)

    print(f"Instance IDs: {instance_ids}")


    instances = ec2_client.describe_instances(InstanceIds=instance_ids)

    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            public_dns_name = instance.get('PublicDnsName', 'N/A')
            print(f"Instance ID: {instance_id}, Public DNS Name: {public_dns_name}")


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


def instance_error(region,instance_type,df):
    data = {"algorithm_name": 'EP Benchmark', "Class": None, "Time_in_Seconds": None, "Total_Threads": None,
            "Available_Threads": None, "Mops_total": None, "Mops_per_thread": None,
            'region': region + AWSConfig.zone_letter,
            'Instance_name': instance_type,'timestamp':datetime.now() ,"Ondemand_price": None, "Spot_price": None,"STATUS":BenchmarkConfig.STATUS}
    df.loc[len(df)] = data
    return df

def benchmark(region, repetions, json_file):
    """
    :param region: Define the AWS region that the instance will be created
    :param availability_zone: Define the AWS availability zone that the instance will be created 
    :param repetitions: Number of executions inside the instance
    :return:
    """

    json_file = Path(json_file)

    if not json_file.exists():
        print(f"File {json_file} not found")
        raise FileNotFoundError
    benchmark_config = BenchmarkConfig(json_file=json_file)

    df = pd.DataFrame(columns=benchmark_config.columns)
    star_test = datetime.now()
    csv_name = f"{region}_{star_test.year}-{star_test.month:02d}-{star_test.day:02d}_{star_test.strftime('%H-%M-%S')}.csv"

    for instance_type, instance_core in benchmark_config.vms.items():
        try:

            try:
                ondemand_price = aws.get_price_ondemand(region, instance_type)
                spot_price = aws.get_price_spot(region, instance_type, region + AWSConfig.zone_letter)
            except Exception as e:
                logging.exception(f'Error getting price for {instance_type}')
                ondemand_price = ''
                spot_price = ''

            instance = start_instance(region, instance_type)
            # instance = get_instance(region, 'i-068ee0206841f4643')
            time.sleep(5)
            for i in range(repetions):
                output = run_via_ssh(cmd='./ep.D.x', instance=instance, region=region)
                #print(output)
                df = extract_info_from_text(output, region, instance_type, ondemand_price, spot_price, df)

            instance.terminate()
            instance.wait_until_terminated()
            print(f"Instance {instance.id} has been terminated.")
        except Exception as e:
            logging.exception(f'An exception occurred:{e}')
            df = instance_error(region, instance_type,df)
            df.to_csv(csv_name, index=False)


    df.to_csv(csv_name, index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark AWS')
    parser.add_argument('region', type=str, help='AWS region')
    parser.add_argument('json_file', type=str, help='Json file with instances configurations')
    parser.add_argument('--repetitions', type=int, default=5, help='Number of repetitions')
    args = parser.parse_args()
    logging.info(f"Start execution in {args.region} N={args.repetitions} JsonFile={args.json_file}")
    #benchmark(args.region, args.repetitions, args.json_file)
    start_spot_instance(args.region, 'c5a.12xlarge')
    # benchmark('us-east-1', 1, 'instance_info.json')
    # benchmark('sa-east-1', 1, 'instance_info.json')
