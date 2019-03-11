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
    ''' Runs a docker container to train a group of images
    '''
    print("Received event: " + json.dumps(event, indent=2))

    client = boto3.client('ecs')

    # Get passed in Environment Variables
    # "muni_name": "HaltomCity",
    # "start_date": "2018-12-18",
    # "end_date": "2018-12-18"

    docker_container_name = event.get("docker_container_name", "neptune-reads")

    muni_name = event.get("muni_name", None)

    # To get all the days data, we are starting after midnight and then pulling the data from the previous day.

    # Making this an option to pass into the lambda function
    get_day_before_data = (event.get("get_day_before_data", "true").lower() == "true")

    if get_day_before_data:
        current_date = (datetime.datetime.now(timezone('MST')) - datetime.timedelta(days=1)).strftime('%Y/%m/%d')
    else:
        current_date = datetime.datetime.now(timezone('MST')).strftime('%Y/%m/%d')

    start_date = event.get("start_date", current_date)
    end_date = event.get("end_date", current_date)

    process_mius = event.get("process_mius", "True")
    process_meters = event.get("process_meters", "True")
    process_last_reads = event.get("process_last_reads", "False")

    environment = os.environ['Environment']
    version = os.environ['Version']
    db_host = os.environ['Dbhost']
    ssm_db_param_name = "{environment}-integration-db".format(environment=environment)
    backup_bucket = "{environment}-integration".format(environment=environment)

    environment_list = [
        {
            'name': 'ENVIRONMENT',
            'value': environment
        },
        {
            'name': 'DB_HOST',
            'value': db_host
        },
        {
            'name': 'PROCESS_MIUS',
            'value': process_mius
        },
        {
            'name': 'SSM_DB_PARAM_NAME',
            'value': ssm_db_param_name
        },
        {
            'name': 'BACKUP_BUCKET',
            'value': backup_bucket
        },
        {
            'name': "END_DATE",
            'value': end_date
        },
        {
            'name': "START_DATE",
            'value': start_date
        },
        {
            'name': 'PROCESS_LAST_READS',
            'value': process_last_reads
        },
        {
            'name': 'PROCESS_METERS',
            'value': process_meters
        }
    ]

    if 'prod' in environment:
        # user prod account
        account = "345060474660"
    else:
        # else use qa account id
        account = "046030275018"

    if muni_name:
        log_file_name = "{muni_name}-{docker_container_name}".format(
            muni_name=muni_name,
            docker_container_name=docker_container_name)
        environment_list.append(
            {
                'name': 'MUNI_NAME',
                'value': muni_name
            }
        )
    else:
        log_file_name = docker_container_name
    print(environment_list)

    response = client.register_task_definition(
        family="{docker_container_name}-integration".format(docker_container_name=docker_container_name),
        # taskRoleArn='string',
        # executionRoleArn='string',
        networkMode='bridge',
        containerDefinitions=[
            {
                'name': "{docker_container_name}-integration".format(docker_container_name=docker_container_name),
                'image': '{account}.dkr.ecr.us-west-2.amazonaws.com/fathom-integration:{docker_container_name}-{version}'.format(
                    version=version,
                    account=account, docker_container_name=docker_container_name),
                'cpu': 512,
                'memory': 2048,
                'memoryReservation': 2048,
                'essential': True,
                'environment': environment_list,
                'logConfiguration': {
                    'logDriver': 'awslogs',
                    'options': {
                        "awslogs-group": "{environment}-{docker_container_name}-ingestion".format(
                            environment=environment,
                            docker_container_name=docker_container_name),
                        "awslogs-region": "us-west-2",
                        "awslogs-stream-prefix": log_file_name
                    }
                },
            },
        ],
        cpu='512',
        memory='2048',
    )
    print(response)
    task_definition = response.get("taskDefinition").get("taskDefinitionArn")

    response = client.run_task(
        cluster='{environment}-integation-slave-cluster'.format(environment=environment),
        taskDefinition=task_definition,
        count=1,
        launchType='EC2'
    )

    print(response)


if __name__ == "__main__":
    lambda_handler("test", "test")
