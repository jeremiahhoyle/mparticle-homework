#!/usr/bin/env bash

set -o errexit
set -o xtrace

if [[ -z $1 ]]; then
echo "Environment in which you are deploying"
echo "example: deploy.sh 3"
exit
else
environment=$1
fi

if [[ -z $2 ]]; then
echo "The name is required since everything revolves around the name."
echo "example: deploy.sh 3"
exit
else
name=$2
fi

if [[ -z $3 ]]; then
echo "profile not found, assigning environment"
profile=$1
else
profile=$3
fi

if [[ -z $4 ]]; then
echo "the version to be deployed, if there is not one specified, \
then it will get the lastest version in QA and increment it."
{ # your 'try' block
    version=$(aws lambda get-function --function-name $environment-$name-lambda --query 'Tags.{version:version}' --profile $profile --region us-west-2 --output text)\
    &&  version=$(($version+1))
} || { # your 'catch' block
   version="1"
}
else
echo "the version to be deployed, if there is not one specified, \
then it will get the lastest version in QA and increment it."
version=$4
fi



CURRENT=$(pwd)
temp_location="$CURRENT/lambdatemp"
code_location="$CURRENT/lambdas/$name"
zip_filename="$name-$version.zip"
s3_path="$environment-fathom-integration/lambda/"
s3_file_path="s3://$s3_path"

mkdir -p $temp_location

cp -r $code_location/* $temp_location

pip install -t $temp_location -r $temp_location/requirements.txt

cd $temp_location

ls -ltr

zip -r $zip_filename *

#zip -u $zip_filename "$name.py"

cd $CURRENT

aws s3 cp $temp_location/$zip_filename $s3_file_path --profile $profile --region us-west-2

parameters="ParameterKey=Name,ParameterValue=$name ParameterKey=Version,ParameterValue=$version"

/bin/bash $CURRENT/cloudformation/deploy-cloudformation.sh $environment lambda.yaml $name $profile $parameters

rm -fr $temp_location

echo $version