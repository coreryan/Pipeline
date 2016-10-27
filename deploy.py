import boto3, os, time, zipfile
from subprocess import call
from os.path import basename



DEPLOY_DIR = '/Users/coreryan/Documents/Pipeline/Functions/'
WRITE_DIR = '/Users/coreryan/Documents/Pipeline/Artifacts/'
TEMPLATE_DIR = '/Users/coreryan/Documents/Pipeline/Templates/'
BUCKET = 'ctr-pipeline-artifacts'
CURRENT_TEMPLATE = 'PipelineDev.yaml'
TEMPLATE_URL = "https://" +  BUCKET + ".s3.amazonaws.com/" + CURRENT_TEMPLATE

TO_DELETE = "aws s3 rm s3://" + BUCKET + " --recursive"

#call ([TO_DELETE])

#os.system(TO_DELETE)

for OLD in os.listdir(WRITE_DIR):
  os.remove(WRITE_DIR + OLD)


LIST = os.listdir(DEPLOY_DIR)
TIME = str(int(time.time()))

for FUNCTION in LIST:
  if not FUNCTION.startswith('.'):
    FUNCTION_DIR = DEPLOY_DIR + FUNCTION + '/' 
    FUNCTION_FILE = WRITE_DIR + FUNCTION + TIME + '.zip'
    os.system("zip -r -j " + FUNCTION_FILE + " " + FUNCTION_DIR + "> /dev/null")


DEPLOY_LIST = os.listdir(WRITE_DIR)
print TIME

for PACKAGE in DEPLOY_LIST:
  if not PACKAGE.startswith('.'):
    os.system("aws s3 cp " + WRITE_DIR+PACKAGE +" s3://"+BUCKET)

os.system("aws s3 cp " + TEMPLATE_DIR + CURRENT_TEMPLATE + " s3://"+BUCKET)

cfn = cfn = boto3.client('cloudformation')
response = cfn.update_stack(
  StackName = 'Pipeline',
  TemplateURL = TEMPLATE_URL,
  Parameters = [
    {
      'ParameterKey': 'TimeStamp',
      'ParameterValue': TIME
    },
    {
      'ParameterKey': 'DeploymentBucket',
      'ParameterValue': BUCKET
    }
  ]
)