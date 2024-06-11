import aws_bench.pricing_handler as aws
from aws_bench.constants import AWSConfig, SSHConfig, BenchmarkConfig

import boto3
import os
import paramiko
import time
from datetime import datetime
#import click
from pathlib import Path
import argparse


def run_via_ssh(cmd, instance):
    k = paramiko.RSAKey.from_private_key_file("/home/luan/aws_key2.pem")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(hostname=instance.public_dns_name, 
              username="ubuntu", 
              pkey=k, 
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

def start_instance(region, instance_type):
    
    session = boto3.Session(aws_access_key_id=AWSConfig.aws_acess_key_id,
                            aws_secret_access_key=AWSConfig.aws_acess_secret_key,
                            region_name=region)
    
    ec2 = session.resource('ec2')

    architecture = 'arm' if 'g' in instance_type.split('.')[0] else 'x86'
    dict_key = f'{region}_{architecture}'    

    instances = ec2.create_instances(
        ImageId=AWSConfig.image_setup[dict_key]['imageId'],
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        KeyName=AWSConfig.image_setup[dict_key]['key_name'],
        SecurityGroupIds=[AWSConfig.image_setup[dict_key]['sg']],
        Placement={'AvailabilityZone': region + AWSConfig.zone_letter}
    )
    
    assert len(instances) == 1 # only one instance should be created
    
    instance = instances[0]

    
    instance.wait_until_running()
    instance.reload()
    print(f'Tipo da instância: {instance_type}')
    print(f'Instância criada com ID: {instance.id}')
    print(f'Endereço Público: {instance.public_ip_address}')
    print(f'Endereço Privado: {instance.private_ip_address}')
    print(f'Endereço DNS Name: {instance.public_dns_name}')    

    return instance
   
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
    
    for instance_type, instance_core in benchmark_config.vms.items():
        ondemand_price = aws.get_price_ondemand(region, instance_type)
        #spot_price = aws.get_price_spot(region, instance_type)
        #instance = start_instance(region, instance_type)
        instance = get_instance(region, 'i-05243c319ad6847ee')

        for i in range(repetions):
            output = run_via_ssh(cmd='ls', instance=instance)
            print(output)
        
        instance.terminate()



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark AWS')
    parser.add_argument('region', type=str, help='AWS region')
    parser.add_argument('json_file', type=str, help='Json file with instances configurations')
    parser.add_argument('--repetitions', type=int, default=5, help='Number of repetitions')    
    args = parser.parse_args()
    benchmark(args.region, args.repetitions, args.json_file)
    
    #benchmark('us-east-1', 1, 'instance_info.json')
    #benchmark('sa-east-1', 1, 'instance_info.json')
