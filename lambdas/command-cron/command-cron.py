import boto3
import json
import os
from pprint import pprint

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

    client = boto3.client('ec2')

    autoscaling_group_name = event.get("autoscaling_group_name", "")
    command = event.get("command", "")

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
            {
                'Name': 'instance-state-name',
                'Values': [
                    "running"
                ]
            },
        ]
    )
    list_of_instance_ids = []

    reservations = response.get('Reservations')
    client = boto3.client('ssm')
    for reservation in reservations:
        instances = reservation.get('Instances')
        pprint(instances)
        for instance in instances:
            instance_id = instance.get('InstanceId')
            list_of_instance_ids.append(instance_id)

            response = client.send_command(
                InstanceIds= [instance_id],
                DocumentName='AWS-RunShellScript',

                TimeoutSeconds=300,
                Comment='Running Command [{command}]'.format(command=command),
                Parameters={"commands":
                                ['/usr/bin/python3 /root/mparticle-homework/run_command.py --command "{command}" --unique_name testing --log_level debug'.format(
                                    command=command )
                                ]
                }

            )




if __name__ == "__main__":

    test_data = {
        "autoscaling_group_name": "test-cluster-AutoScalingGroup-RCK1Z7LSX3X3",
        "command": "/bin/sleep 30"
    }

    lambda_handler(test_data, "test")
