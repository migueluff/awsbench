import boto3
import json
from pkg_resources import resource_filename
import datetime

# Search product filter. This will reduce the amount of data returned by the
# get_products function of the Pricing API
FLT = '[{{"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"}},' \
      '{{"Field": "operatingSystem", "Value": "{o}", "Type": "TERM_MATCH"}},' \
      '{{"Field": "preInstalledSw", "Value": "NA", "Type": "TERM_MATCH"}},' \
      '{{"Field": "instanceType", "Value": "{t}", "Type": "TERM_MATCH"}},' \
      '{{"Field": "location", "Value": "{r}", "Type": "TERM_MATCH"}},' \
      '{{"Field": "capacitystatus", "Value": "Used", "Type": "TERM_MATCH"}}]'

# Use AWS Pricing API through Boto3
# API only has us-east-1 and ap-south-1 as valid endpoints.
# It doesn't have any impact on your selected region for your instance.
client = boto3.client('pricing', region_name='us-east-1')


# Get current AWS price for an on-demand instance
def get_price_ondemand(region, instance):
    region = __get_region_name(region)
    f = FLT.format(r=region, t=instance, o='Linux')
    data = client.get_products(ServiceCode='AmazonEC2', Filters=json.loads(f))
    od = json.loads(data['PriceList'][0])['terms']['OnDemand']
    id1 = list(od)[0]
    id2 = list(od[id1]['priceDimensions'])[0]
    return od[id1]['priceDimensions'][id2]['pricePerUnit']['USD']


# Translate region code to region name. Even though the API data contains
# regionCode field, it will not return accurate data. However using the location
# field will, but then we need to translate the region code into a region name.
# You could skip this by using the region names in your code directly, but most
# other APIs are using the region code.
def __get_region_name(region_code):
    default_region = 'US East (N. Virginia)'
    endpoint_file = resource_filename('botocore', 'data/endpoints.json')
    try:
        with open(endpoint_file, 'r') as f:
            data = json.load(f)
        # Botocore is using Europe while Pricing API using EU...sigh...
        return data['partitions'][0]['regions'][region_code]['description'].replace('Europe', 'EU')
    except IOError:
        return default_region


def get_price_spot(region_name, instance_type, availability_zone):
    client_ec2 = boto3.client('ec2', region_name=region_name)
    response = client_ec2.describe_spot_price_history(
        ProductDescriptions=['Linux/UNIX'],
        InstanceTypes=[instance_type],
        MaxResults=1,
        AvailabilityZone=availability_zone
    )
    spot_price = response['SpotPriceHistory'][0]['SpotPrice']
    return spot_price


def get_prices_spot(region_name, instance_type, hours=5):
    client_ec2 = boto3.client('ec2', region_name=region_name)
    prices = []

    # Get the current time
    end_time = datetime.datetime.now()

    # Calculate the start time as 'hours' before the current time
    start_time = end_time - datetime.timedelta(hours=hours)

    # Iterate over hourly intervals
    current_time = start_time
    while current_time <= end_time:
        # Convert the current time to ISO 8601 format
        current_time_iso = current_time.isoformat()

        # Describe spot price history for the current time interval
        response = client_ec2.describe_spot_price_history(
            InstanceTypes=[instance_type],
            StartTime=current_time_iso,
            EndTime=current_time_iso,
            MaxResults=1
        )

        # Retrieve the spot price from the response
        spot_price = response['SpotPriceHistory'][0]['SpotPrice']
        prices.append((spot_price, current_time))

        # Move to the next hour
        current_time += datetime.timedelta(hours=1)

    return prices


def get_prices_spot_v2(region_name, instance_type, start_time, end_time):
    client_ec2 = boto3.client('ec2', region_name=region_name)
    prices = []

    # Iterate over one-second intervals
    current_time = start_time
    while current_time <= end_time:
        # Convert the current time to ISO 8601 format
        current_time_iso = current_time.isoformat()

        # Set the end time of the interval to the next second
        next_second = current_time + datetime.timedelta(seconds=1)
        next_second_iso = next_second.isoformat()

        # Describe spot price history for the current one-second interval
        response = client_ec2.describe_spot_price_history(
            InstanceTypes=[instance_type],
            StartTime=current_time_iso,
            EndTime=next_second_iso,
            MaxResults=1
        )

        # Retrieve the spot price from the response
        spot_price = float(response['SpotPriceHistory'][0]['SpotPrice'])

        # Calculate the cost for this one-second interval
        cost_per_second = spot_price / 3600.0
        prices.append((cost_per_second, current_time))

        # Move to the next second
        current_time = next_second

    # Calculate the total cost by summing up all the costs per second
    total_cost = sum(cost for cost, _ in prices)

    return prices, total_cost
