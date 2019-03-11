import boto3
import argparse
import os, sys
import watchtower, logging
from slackclient import SlackClient
import time
import socket
import subprocess

"""
This script will run a command that is given as a variable and ensure it is the only one running.

This script can be ran as a cron job or using RunCommand manager in AWS

Requirements:
The location the script is ran must have access to AWS keys

To setup the IAM keys on the AWS instance, please use these instructions.

"""


class Monitoring:

    """
        This class will handle the monitoring in cloudwatch metrics
    """

    def __init__(self, unique_name):
        self.client = boto3.client('cloudwatch')
        self.name = unique_name
        self.name_space = "run_command"
    def put_run_time(self, seconds):

        metric_name = "{name}-run-time".format(name=self.name)
        response = self.client.put_metric_data(
            Namespace=self.name_space,
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': seconds,
                    'Unit': 'Seconds'
                },
            ]
        )

    def put_error(self, time):
        metric_name = "{name}-errors".format(name=self.name)
        response = self.client.put_metric_data(
            Namespace=self.name_space,
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': time,
                    'Unit': 'Seconds'
                },
            ]
        )


class Notifying:
    """
        This will notify a slack channel
    """

    def __init__(self, unique_name):

        self.client = boto3.client('ssm')

        self.slack_token = self.__get_paraeter()


    def send_message(self, message):

        sc = SlackClient(self.slack_token)
        sc.api_call(
            "chat.postMessage",
            channel="run_command",
            text=message
        )

    def __get_paraeter(self):
        response = self.client.get_parameters(
            Names=[
                "SLACK_API_TOKEN"
            ]
        )

        return response['Parameters'][0]['Value']

class RunningCheck:
    """
        This will handling checking if the application is running somewhere else or on the same instance
        we are going store the status of the unique key in ssm key value store. We could encrypt it but
        I am not doing that here.
    """

    def __init__(self, unique_name):

        self.client = boto3.client('ssm')
        self.parameter = "{name}-lock".format(name=unique_name)


    def __get_paraeter(self):

        response = self.client.get_parameters(
            Names=[
                self.parameter
            ]
        )

        return response['Parameters'][0]['Value']

    def is_running(self):
        """
            This checks to see if the process is running somewhere else.
        """
        try:
            status = self.__get_paraeter()
        except:
            return False

        logger.info("Current Status [{status}]".format(status=status))

        if status == "running":
            return True
        else:
            return False

    def set_to_running(self):
        """
            This will set the ssm parameter to running
        """
        response = self.client.put_parameter(
            Name=self. parameter,
            Description='run-command value for {name} '.format(name=self.parameter),
            Value='running',
            Type='String',
            Overwrite=True

        )

    def set_to_stop(self):

        response = self.client.put_parameter(
            Name=self.parameter,
            Description='run-command value for {name} '.format(name=self.parameter),
            Value='stop',
            Type='String',
            Overwrite=True
        )


class RunCommand:

    def __init__(self, command, unique_name, log_level, hostname=None):

        self.command = command
        self.client = boto3.client('cloudwatch')
        self.monitoring = Monitoring(unique_name=unique_name)
        self.run_check = RunningCheck(unique_name=unique_name)
        self.notifying = Notifying(unique_name=unique_name)

    def run_command(self):
        """
            This will run the command
        """
        # we will get the local hosts name it is running on

        hostname = socket.gethostname()

        # This is the start maessage
        message = "Starting to Run Command [{command}] on ({hostname})".format(command=self.command,
                                                                               hostname=hostname)
        # send start message to the logging system
        logger.info(message)

        # send start message to slack
        self.notifying.send_message(message=message)

        # tracking the timeing of the command length
        start_time = time.time()

        if self.run_check.is_running():

            message = """Error Running [{command}] on ({hostname}).
            It is already running somewhere else
            """.format(command=self.command, hostname=hostname)

            # calculate start and end time
            end_time = time.time()
            total_time = float(end_time - start_time)
            self.__error_notify(message=message, time=total_time)

            # logging time
            message = """This took [{seconds}] seconds to run.
                """.format(seconds=total_time)
            logger.info(message)

        else:
            # set the flag to running
            self.run_check.set_to_running()
            try:
                output = subprocess.check_output(self.command.split())

            except:
                message = """Received an error running command [{command}].
                Message: {error}
                """.format(command=self.command, error=sys.exc_info())

                # calculating time and adding to cloudwatch
                end_time = time.time()
                total_time = float(end_time - start_time)
                self.__error_notify(message=message, time=total_time)

                # set the flag to not running
                self.run_check.set_to_stop()
                return message

            message = """
            Sucessfully ran command [{command}] on ({hostname}) .
            Output is:
            {output}
            """.format(command=self.command,
                       output=output,
                       hostname=hostname)
            self.__info_notify(message=message)

            # calculate start and end time
            end_time = time.time()
            total_time = float(end_time - start_time)

            # send metrics to cloudwatch
            self.monitoring.put_run_time(seconds=total_time)

            # logging time
            message = """This took [{seconds}] seconds to run.
                    """.format(seconds=total_time)
            logger.info(message)

            # set the flag to not running
            self.run_check.set_to_stop()

    def __error_notify(self, message, time):

        # send error message
        logger.error(message)

        # send message to slack
        self.notifying.send_message(message=message)

        # set update statistics
        self.monitoring.put_error(time=time)

    def __info_notify(self, message):

        # sending information
        logger.info(message)

        # send message to slack
        self.notifying.send_message(message=message)


def parse_args():
    """
        This parses the arguments to the python script

    """

    parser = argparse.ArgumentParser(description='running a command with logging a checking')
    parser.add_argument("--command", required=True, type=str, help="Command to be run")
    parser.add_argument("--unique_name", required=True, type=str,
                        help="This will be a unqiue name will ensure no other commands are being ran anywhere else")
    parser.add_argument("--host", required=False, type=str,
                        help="Hostname or IP address of the server being ran on")

    parser.add_argument("--log_level", type=str, choices=['debug', 'info', 'error','critical'], default='info',
                        help="This is the logging level")


    args = parser.parse_args()

    return args

if __name__ == '__main__':

    args = parse_args()


    # converting the log levels from text input
    if args.log_level == 'debug':
        input_log_level = logging.DEBUG
    elif args.log_level == 'error':
        input_log_level = logging.ERROR
    elif args.log_level == 'critical':
        input_log_level = logging.CRITICAL
    else:
        input_log_level = logging.INFO

    syslog = "/var/log/syslog"
    #syslog = "/tmp/syslog"
    log_group_name = 'run_command'
    stream_name = "{unqiue_name}-logs".format(unqiue_name=args.unique_name)
    logging.basicConfig(level=input_log_level,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename=syslog,
                        filemode='a')

    watch_tower = watchtower.CloudWatchLogHandler(log_group=log_group_name,
                                                  stream_name=stream_name,
                                                  create_log_group=True)

    logger = logging.getLogger(args.unique_name)

    logger.addHandler(watch_tower)

    RunCommand(command=args.command, unique_name=args.unique_name, log_level=input_log_level).run_command()