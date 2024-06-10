import boto3
import pricing_handler as aws
import os
from constants import instance_info, path_private_key, imageId_sa, imageId_us, sg_sa, sg_us, key_name_sa, \
    key_name_us, imageID_us_arm
import paramiko
import time
from datetime import datetime
import click

instance_types, instance_cores = [], []
for k, v in instance_info.items():
    instance_types.append(k), instance_cores.append(v)

aws_acess_key_id = os.getenv('AWS_KEY_ID')
aws_acess_secret_key = os.getenv('AWS_SECRET_KEY')


def compile_benc(host, path_private_key, user='ubuntu'):
    cliente_ssh = paramiko.SSHClient()

    cliente_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    cliente_ssh.connect(hostname=host, username=user, key_filename=path_private_key)

    stdin, stdout, stderr = cliente_ssh.exec_command(
        f'cd NPB3.4.2/NPB3.4-OMP;sudo make ep CLASS=D;cp /home/ubuntu/NPB3.4.2/NPB3.4-OMP/bin/ep.D.x /home/ubuntu/;cp ~')
    print(stdout.read().decode())

    cliente_ssh.close()


def run(host, path_private_key, index, user='ubuntu'):
    cliente_ssh = paramiko.SSHClient()

    cliente_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    cliente_ssh.connect(hostname=host, username=user, key_filename=path_private_key)

    stdin, stdout, stderr = cliente_ssh.exec_command(
        f'export OMP_NUM_THREADS={instance_cores[index]};./ep.D.x > out.out;cat out.out')

    output = str(stdout.read().decode())
    cliente_ssh.close()
    return output


def save_s3_file(content, region, bucket, file_name):
    s3_client = boto3.client('s3', region_name=region)
    s3_client.put_object(Body=content, Bucket=bucket, Key=file_name)
    print(f"Content uploaded to bucket {bucket} as {file_name}")


def get_file_name(region, instance):
    now = datetime.now()
    datetime_str = now.strftime("%Y%m%d_%H%M%S")
    file_name = f'{region}-{instance}-{datetime_str}.txt'
    return file_name


@click.command()
@click.argument("region", default="us-east-1")
@click.option("-z", "--zone", default="a", required=True, help="Define a availability zone")
@click.option("-n", "--number-exec", default=5, required=True, help="Define a number of executions")
@click.option("-c", "--compile", is_flag=True, default=False, help="If define, Save report in current directory")
def benchmark(region, zone, number_exec, compile):
    """
    :param region:
    :param availability_zone:
    :param number_executions:
    :return:
    """
    for i in range(len(instance_types)):
        try:
            session = boto3.Session(
                aws_access_key_id=aws_acess_key_id,
                aws_secret_access_key=aws_acess_secret_key,
                region_name=region
            )

            ec2 = session.resource('ec2')
            ec2_client = session.client('ec2')

            ondemand_price = aws.get_price_ondemand(region, instance_types[i])
            spot_price = aws.get_price_spot(region, instance_types[i])

            if region == 'us-east-1':

                if 'g' in instance_types[i].split('.')[0]:
                    imageId = imageID_us_arm
                else:
                    imageId = imageId_us

                sg = sg_us
                key_name = key_name_us
            else:
                imageId = imageId_sa
                sg = sg_sa
                key_name = key_name_sa

            availability_zone = region + zone
            instances = ec2.create_instances(
                ImageId=imageId,
                MinCount=1,
                MaxCount=1,
                InstanceType=instance_types[i],
                KeyName=key_name,
                SecurityGroupIds=[sg],
                Placement={'AvailabilityZone': availability_zone}
            )

            for instance in instances:
                instance.wait_until_running()
                instance.reload()  # Atualiza os atributos da instância
                print(f'Tipo da instância: {instance_types[i]}')
                print(f'Instância criada com ID: {instance.id}')
                print(f'Endereço Público: {instance.public_ip_address}')
                print(f'Endereço Privado: {instance.private_ip_address}')
                print(f'Endereço DNS Name: {instance.public_dns_name}')

            time.sleep(5)
            number_exec = int(number_exec)
            print(number_exec)
            if compile:
                compile_benc(host=instance.public_dns_name, path_private_key=path_private_key)
            for j in range(number_exec):
                content = run(host=instance.public_dns_name, index=j, path_private_key=path_private_key)
                content = content + '\nOndemand_price: ' + str(ondemand_price) + '\nSpot_price: ' + str(
                    spot_price) + '\n'
                save_s3_file(content=content, region=region, bucket='awsbenchmiguel',
                             file_name=get_file_name(region=region, instance=instance_types[i]))

            response = ec2_client.terminate_instances(InstanceIds=[instance.id])
            waiter = ec2_client.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=[instance.id])
            print(f"Instance terminated:{region}:{instance_types[i]} - {instance.id}")


        except Exception as e:
            print(e)
            print(f'Tipo da instância com erro: {instance_types[i]}')


if __name__ == '__main__':
    benchmark()
