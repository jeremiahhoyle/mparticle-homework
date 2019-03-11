#!/usr/bin/env bash
set -o errexit
set -o xtrace

if [[ -z $1 ]]; then
echo "cloudformation template to deploy"
exit
else
filename="$1"
fi

if [[ -z $2 ]]; then
echo "stackname name"
exit
else
stack_name="$2"
fi

if [[ -z $3 ]]; then
echo "profile not found, assigning environment"
exit
else
profile="$3"
fi

if [[ -z $4 ]]; then
echo "No specified s3 bucket."
exit
else
bucket="$4"	        #
fi

if [[ -z $5 ]]; then
echo "vpc to number to deploy to"
exit
else
vpc="$5"
fi

if [[ -z $6 ]]; then
echo "subnet needs to be specified"
exit
else
subnet="$6"
fi

if [[ -z $7 ]]; then
echo "availability zone"
exit
else
az="$7"
fi

if [[ -z $8 ]]; then
echo "internal network ip range"
exit
else
iprange="$8"
fi

if [[ -z $9 ]]; then
echo "security key"
exit
else
securitykey="$9"
fi

if [[ -z ${10} ]]; then
echo "region"
region="us-west-2"
else
region=${10}
fi


if [[ -z ${11} ]]; then
echo "No Optional Parameters"
else
# this little mess takes the last of the arguments and interates through to get all the parameters
argc=$#
argv=($@)

for (( j=10; j<argc; j++ )); do
    parameters="$parameters ${argv[j]}"
    echo
done

fi

s3_path="$bucket/$filename"

CURRENT=$(pwd)
cloudformation_path=$CURRENT/cloudformation

# this chaos is checking to see if the stack exists and creating instead of updating
action="update"
{ # your 'try' block
    aws cloudformation describe-stacks --stack-name $stack_name --profile $profile --region $region && action="update"
} || { # your 'catch' block
   action="create"
}

# paths for s3 upload and cloudformation creationg
s3_file_path="s3://$s3_path"
s3_location="https://s3.amazonaws.com/$s3_path"

# uploading the template to s3
aws s3 cp $cloudformation_path/$filename $s3_file_path --profile $profile --region $region

# updating/creating the stack
aws cloudformation $action-stack --capabilities CAPABILITY_IAM --stack-name $stack_name \
--template-url $s3_location \
--parameters \
ParameterKey=Vpc,ParameterValue="$vpc" \
ParameterKey=CIDR,ParameterValue="$iprange" \
ParameterKey=Subnet,ParameterValue="$subnet" \
ParameterKey=Key,ParameterValue="$securitykey" \
ParameterKey=AZ,ParameterValue="$az" \
ParameterKey=Bucket,ParameterValue="$bucket" \
$parameters --profile $profile --region $region

