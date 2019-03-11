#!/usr/bin/env bash
set -o errexit
set -o xtrace


if [[ -z $1 ]]; then
echo "environment to deploy"
echo "example: deploy-cloudformation.sh qa dyanmodb.yaml dyanmodb"
exit
fi

if [[ -z $2 ]]; then
echo "template to deploy"
echo "example: deploy-cloudformation.sh qa dyanmodb.yaml dyanmodb"
exit
fi

if [[ -z $3 ]]; then
echo "stackname name"
echo "example: deploy-cloudformation.sh qa dyanmodb.yaml dyanmodb"
exit
fi

if [[ -z $4 ]]; then
echo "profile not found, assigning environment"
profile=$1
else
profile=$4
fi

if [[ -z $5 ]]; then
echo "No Optional Parameters"
else
# this little mess takes the last of the arguments and interates through to get all the parameters
argc=$#
argv=($@)

for (( j=4; j<argc; j++ )); do
    parameters="$parameters ${argv[j]}"
    echo
done

fi

CURRENT=$(pwd)
cloudformation_path=$CURRENT/cloudformation
filename="$2"
environment="$1"
stack_name="$environment-$3"
action="update"

# check if stackname exists

{ # your 'try' block
    aws cloudformation describe-stacks --stack-name $stack_name --profile $profile --region us-west-2 && action="update"
} || { # your 'catch' block
   action="create"
}

if [ $environment = "prod" ]; then
    fathom_env="Shared Production"
	s3_path="com-gwfathom-cf-deploy/$filename"
else
	s3_path="com-gwfathom-dev-deploy/$filename"
	fathom_env="Development"
fi


s3_file_path="s3://$s3_path"
s3_location="https://s3.amazonaws.com/$s3_path"


aws s3 cp $cloudformation_path/$filename $s3_file_path --profile $profile --region us-west-2

# add optional parameters
aws cloudformation $action-stack --capabilities CAPABILITY_IAM --stack-name $stack_name \
--template-url $s3_location \
--parameters  ParameterKey=Vpc,ParameterValue=$environment $parameters --profile $profile --region us-west-2 \
--tags Key=Environment,Value="$fathom_env" Key=Customer,Value=FATHOM Key=Customer,Value=FATHOM

