import boto3
import json
import os
import datetime
from pytz import timezone

print('Loading function')


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def lambda_handler(event, context):
    ''' Gets all the instances in an autoscaling group and puts them in a queue to run with 15 minute intervals
    '''
    print("Received event: " + json.dumps(event, indent=2))

    client = boto3.client('sqs')

    autoscaling_group_name = event.get("autoscaling_group_name", "")
    intervals = event.get("intervals", "15")
    queue = os.environ.get('queue')

    response = client.describe_instances(
        Filters=[
            {
                'Name': 'tag:aws:autoscaling:groupName',
                'Values': [
                    autoscaling_group_name,
                ]
            },
        ]
    )
    list_of_ips = []

    reservations = response.get('Reservations')
    instances = reservations.get('Instances')

    for instance in instances:
        private_ip_address = instance.get('PrivateIpAddress')
        list_of_ips.append(private_ip_address)










if __name__ == "__main__":
    lambda_handler("test", "test")
