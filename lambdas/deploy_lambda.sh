#!/usr/bin/env bash

set -o errexit
set -o xtrace

if [[ -z $1 ]]; then
echo "The name is required since everything revolves around the name."
exit
else
name=$1
fi

if [[ -z $2 ]]; then
echo "profile not found"
exit
else
profile=$2
fi

if [[ -z $3 ]]; then
echo "No specified s3 bucket."
exit
else
bucket="$3"	        #
fi

if [[ -z $4 ]]; then
echo "vpc to number to deploy to"
exit
else
vpc="$4"
fi

if [[ -z $5 ]]; then
echo "subnet needs to be specified"
exit
else
subnet="$5"
fi

if [[ -z $6 ]]; then
echo "availability zone"
exit
else
az="$6"
fi

if [[ -z $7 ]]; then
echo "internal network ip range"
exit
else
iprange="$7"
fi

if [[ -z $8 ]]; then
echo "security key"
exit
else
securitykey="$8"
fi

if [[ -z ${9} ]]; then
echo "region"
region="us-west-2"
else
region=${9}
fi

if [[ -z ${10} ]]; then
echo "the version to be deployed, if there is not one specified, \
then it will get the lastest version in QA and increment it."
# this gets the current version in QA and increments it by 1 to make a new version to deploy
{ # your 'try' block
    version=$(aws lambda get-function --function-name $name-lambda --query 'Tags.{version:version}' --profile $profile --region us-west-2 --output text)\
    &&  version=$(($version+1))
} || { # your 'catch' block
   version="1"
}
else
echo "the version to be deployed, if there is not one specified, \
then it will get the lastest version in QA and increment it."
version=${10}
fi



CURRENT=$(pwd)
temp_location="$CURRENT/lambdatemp"
code_location="$CURRENT/lambdas/$name"
zip_filename="$name-$version.zip"
s3_file_path="s3://$bucket/lambda/"

rm -fr $temp_location

mkdir -p $temp_location

cp -r $code_location/* $temp_location

pip install -t $temp_location -r $temp_location/requirements.txt

cd $temp_location

ls -ltr

zip -r $zip_filename *

cd $CURRENT

aws s3 cp $temp_location/$zip_filename $s3_file_path --profile $profile --region $region

parameters="ParameterKey=Name,ParameterValue=$name ParameterKey=Version,ParameterValue=$version"

/bin/bash $CURRENT/cloudformation/deploy-cloudformation.sh \
lambda.yaml \
$name \
$profile \
$bucket \
$vpc \
$subnet \
$az \
$iprange \
$securitykey \
$region \
$parameters

rm -fr $temp_location

echo $version