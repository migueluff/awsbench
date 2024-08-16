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
        "Cores": row['Cores']
    }
    print(text)

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


def run_via_ssh_MPI(cmd, instances, region):


    path_key = SSHConfig.path_key_us if region == 'us-east-1' else SSHConfig.path_key_sa

    lifecycle = 'on-demand'

    #logging.info(f"Running command: {cmd} in instance {instance.id} Region: {region} Market: {lifecycle}")

    public_dns_names = [instance.public_dns_name for instance in instances]

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())



    ssh_client.connect(hostname=public_dns_names[0],username="ubuntu",
              key_filename=path_key,
              allow_agent=False, look_for_keys=False)

    ips = ",".join([instance.private_ip_address for instance in instances])

    run_mpi_command = f"mpiexec -hosts {ips} -np {3*24} ./ft.D.x "

    stdin, stdout, stderr = ssh_client.exec_command(run_mpi_command)
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh_client.close()

def __start_instances_to_MPI_(region, instance_type):
    session = boto3.Session(aws_access_key_id=AWSConfig.aws_acess_key_id,
                            aws_secret_access_key=AWSConfig.aws_acess_secret_key,
                            region_name=region)
    resource = session.resource('ec2')


    architecture = 'arm' if 'g' in instance_type.split('.')[0] else 'x86'
    dict_key = f'{region}_{architecture}'
    instances = resource.create_instances(
        ImageId=AWSConfig.image_setup[dict_key]['imageId'],
        InstanceType=instance_type,
        KeyName=AWSConfig.image_setup[dict_key]['key_name'],
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[AWSConfig.image_setup[dict_key]['sg']]
    )
    # Wait for i   nstances to initialize
    for instance in instances:
        instance.wait_until_running()

    # Reload instance attributes
    for instance in instances:
        instance.reload()

    return instances

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

def benchmark_test(args):
    region = args.region
    repetions = args.repetitions
    is_spot = args.spot
    json_file = Path(args.json_file)

    if not json_file.exists():
        logging.error(f"File {json_file} not found")
        raise FileNotFoundError

    benchmark_config = BenchmarkConfig(json_file=json_file)
    market = 'spot' if is_spot else 'ondemand'

    # iterate over the instances
    for instance_type, instance_core in benchmark_config.vms.items():

        instances = __start_instances_to_MPI_(region, instance_type)

        # if instance is not None, we can run the benchmark
        if instances:
                output = run_via_ssh_MPI(cmd='cg.A.x', instances=instances, region=region)
                print(output)
        else:
            raise Exception(f'Instance {instance_type} not available')




def benchmark(args):
    """
    :param region: Define the AWS region that the instance will be created
    :param availability_zone: Define the AWS availability zone that the instance will be created 
    :param repetitions: Number of executions inside the instance
    :return:
    """
    region = args.region
    repetions = args.repetitions  
    is_spot = args.spot
    json_file = Path(args.json_file)

    if not json_file.exists():
        logging.error(f"File {json_file} not found")
        raise FileNotFoundError
        
    benchmark_config = BenchmarkConfig(json_file=json_file)
    market = 'spot' if is_spot else 'ondemand'
    csv_file = Path(args.output_folder, f"results_MPI_{region}.csv")

    if csv_file.exists():
        df = pd.read_csv(csv_file)
    else:
        df = pd.DataFrame(columns=benchmark_config.columns)

    # iterate over the instances
    for instance_type, instance_core in benchmark_config.vms.items():        
        start_time = datetime.now()

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
            
            # start the instance
            instance = __start_instance(region, instance_type, info)

            # if instance is not None, we can run the benchmark
            if instance:
                time.sleep(5)
                execution_count = 0
                #logging.info(f"Binding threads in cores")

                #binding_threads = 'export GOMP_CPU_AFFINITY="' + ' '.join(str(i) for i in range(instance_core)) + '"'

                #metrics = run_via_ssh(cmd=f'python3 rprof-host.py -d -m -n -c -u -i 2.0 &', instance=instance, region=region)

                while execution_count < repetions:
                    logging.info(f"Execution {execution_count + 1} of {repetions}")
                    for bench in ['cg', 'mg','ft']:
                        for c in [8,16,24]:
                            logging.info(f"Running benchmark {bench} with {c} processors")
                            output = run_via_ssh(cmd=f'python3 rprof-host.py -d -m -n -c -u -i 2.0 &;mpiexec -np {c} ./{bench}.C.x', instance=instance, region=region)

                            '''
                            output = run_via_ssh(cmd=f'export OMP_PLACES=cores;export OMP_PROC_BIND=spread;export '
                                                     f'OMP_NUM_THREADS={instance_core};./ep.D.x', instance=instance,
                                                 region=region)
                            '''
                            row = {"Start_Time": start_time,
                                   "End_Time": datetime.now(),
                                   "Instance": instance_type,
                                   "InstanceID": instance.id,
                                   "Market": market,
                                   "Price":  price,
                                   "Region": region,
                                   "Zone": instance.placement['AvailabilityZone'][-1:],
                                   "Algorithm_Name": f'NAS Benchmark - {bench}.C.x',
                                   "Status": 'SUCCESS',
                                   "Cores": c}
                            print(row)
                            df = save_row(output, row, df, csv_file)
                            logging.info(f"Waiting 10 seconds.")
                            time.sleep(10)
                    execution_count += 1

                output = run_via_ssh(cmd=f'cat cpu.csv', instance=instance, region=region)
                arq = open(f'cpu_MPI_{instance}.csv', 'a')
                arq.write(output)
                arq.close()
                output = run_via_ssh(cmd=f'cat cpu_usage.csv', instance=instance, region=region)
                arq = open(f'cpu_usage_MPI_{instance}.csv', 'a')
                arq.write(output)
                arq.close()
                output = run_via_ssh(cmd=f'cat disk.csv', instance=instance, region=region)
                arq = open(f'disk_MPI_{instance}.csv', 'a')
                arq.write(output)
                arq.close()
                output = run_via_ssh(cmd=f'cat memory.csv', instance=instance, region=region)
                arq = open(f'memory_MPI_{instance}.csv', 'a')
                arq.write(output)
                arq.close()
                output = run_via_ssh(cmd=f'cat network.csv', instance=instance, region=region)
                arq = open(f'network_MPI_{instance}.csv', 'a')
                arq.write(output)
                arq.close()
                #   _terminate_instance(instance)
            else:
                raise Exception(f'Instance {instance_type} not available')
        
        except Exception as e:
            row = { "Start_Time": start_time,
                    "End_Time": datetime.now(),
                    "Instance": instance_type,
                    "InstanceID": None,
                    "Market": market,
                    "Price": None,                
                    "Region": region,
                    "Zone": None,
                    "Algorithm_Name": 'NAS Benchmark',
                    "Status": BenchmarkConfig.STATUS}
            
            df = save_row('', row, df, csv_file)

        
        


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark AWS')
    parser.add_argument('region', type=str, help='AWS region')
    parser.add_argument('json_file', type=str, help='Json file with instances configurations')
    parser.add_argument('--repetitions', type=int, default=5, help='Number of repetitions')
    parser.add_argument('--output_folder', type=str, default='.', help='Output folder')
    parser.add_argument('--spot', action='store_true', help='Use spot instances')
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
        
    logging.info(f"Start execution in {args.region} N={args.repetitions} JsonFile={args.json_file}")
    benchmark(args)
    #benchmark_test(args)
