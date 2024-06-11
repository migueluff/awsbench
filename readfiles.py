import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
import re
from constants import bucket_nameus, columns, bucket_namesa
from datetime import datetime
import pandas as pd


# Inicializar cliente Boto3 para S3
s3_client = boto3.client('s3', region_name='us-east-1')


def get_files_names(s3_client, bucket_name):
    files_names = []
    try:
        # Listar objetos no bucket
        response = s3_client.list_objects_v2(Bucket=bucket_nameus)

        # Verificar se o bucket contém objetos
        if 'Contents' in response:
            for obj in response['Contents']:
                # Obter o nome do objeto
                files_names.append(obj['Key'])
            return files_names
        else:
            print("O bucket está vazio.")
    except NoCredentialsError:
        print("Credenciais não disponíveis")
    except PartialCredentialsError:
        print("Credenciais incompletas fornecidas")
    except ClientError as e:
        print(f"Erro inesperado: {e}")


def get_file_content(s3_client, bucket_name, file_names):
    df = pd.DataFrame(columns=columns)
    for s3_object_key in file_names:
        file_response = s3_client.get_object(Bucket=bucket_nameus, Key=s3_object_key)

        # Ler o conteúdo do arquivo
        content = file_response['Body'].read().decode('utf-8')
        #print(content)

        info = extract_info_from_text(content)
        print(info)
        name_info = s3_object_key.split('-')
        region = '-'.join(name_info[0:3])
        instance_name = name_info[3]

        date = name_info[4].split('.')[0]
        timestamp_obj = datetime.strptime(date, '%Y%m%d_%H%M%S')
        info['region'] = region
        info['Instance_name'] = instance_name
        info['timestamp'] = timestamp_obj
        df.loc[len(df)] = info

    return df

def extract_info_from_text(text):
    data = {
        "algorithm_name":'EP Benchmark',
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
        "Mops_per_thread": re.compile(r"Mop/s/thread\s*=\s*([\d.]+)", re.IGNORECASE),
        "Ondemand_price": re.compile(r"Ondemand_price:\s+([\d.]+)"),
        "Spot_price": re.compile(r"Spot_price:\s+([\d.]+)")
    }

    for key, pattern in regex_patterns.items():
        match = pattern.search(text)
        if match:
            data[key] = match.group(1)

    return data


files_names = get_files_names(s3_client=s3_client, bucket_name=bucket_nameus)

df = get_file_content(s3_client=s3_client,file_names=files_names ,bucket_name=bucket_nameus)

print(df)

df.to_csv('test.csv', index=False)

print("DataFrame saved to '11jun_us.csv'.")
