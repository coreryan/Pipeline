import boto3, logging, json, time
def handler(event, context):
  CONFIG = pull_config(context)
  STATUS_TABLE = CONFIG['STATUS_TABLE']
  response = ddb_scan(STATUS_TABLE)
  print response
  STACKS = response['Items']
  for STACK in STACKS:
    if 'master-' in STACK['StackId']:
      MASTER = STACK
    else:
      cfn = boto3.client('cloudformation')
      response = cfn.delete_stack(
        StackName = STACK['StackId']
      )
  print MASTER
  delete_dependencies(STACKS)
  delete_master(MASTER)
  print "DONE DELETING"
def pull_config(context):
  PULL_NAME = context.function_name.split('-')
  STACK_NAME = PULL_NAME[0]
  cfn = cfn = boto3.client('cloudformation')
  response = cfn.describe_stack_resource(
    StackName=STACK_NAME,
    LogicalResourceId='TemplateBucket'
  )
  BUCKET = response['StackResourceDetail']['PhysicalResourceId']
  s3 = boto3.resource('s3')
  CONFIG = s3.Object(BUCKET,'config/config.txt')
  return json.loads(CONFIG.get()["Body"].read())
def delete_master(MASTER):
  cfn = boto3.client('cloudformation')
  response = cfn.delete_stack(
    StackName = MASTER['StackId']
  )
  CURRENT_STATUS = ""
  while CURRENT_STATUS <> "DELETE_COMPLETE":
    response = cfn.describe_stacks(
      StackName = MASTER['StackId']
    )
    CURRENT_STATUS = response['Stacks'][0]['StackStatus']
    time.sleep(1)

def delete_dependencies(STACKS):
  index = 0
  while (len(STACKS)-1) > index:
    cfn = boto3.client('cloudformation')
    if "master-" in STACKS[index]['StackId']:
      print "At master increasing index"
      index+=1
    #print "Describing " + STACKS[index]['StackName']
    response = cfn.describe_stacks(
      StackName = STACKS[index]['StackId']
    )
    CURRENT_STATUS = response['Stacks'][0]['StackStatus']
    time.sleep(1)
    print 'The Current Status: ' + CURRENT_STATUS
    if "IN_PROGRESS" not in CURRENT_STATUS:
      print "Stack not in Progress"
      if CURRENT_STATUS == 'DELETE_COMPLETE':
        print "Stack in Delete Complete - Removing item from list"
        index += 1
      else:
        print "Attempting a delete on " + STACK['StackName']
        cfn = boto3.client('cloudformation')
        response = cfn.delete_stack(
          StackName = STACKS[index]['StackId']
        )
  return      
def ddb_scan(STATUS_TABLE):
  ddb = boto3.resource('dynamodb')
  table = ddb.Table(STATUS_TABLE)
  response = table.scan(
    TableName=STATUS_TABLE,
    Select='ALL_ATTRIBUTES',
    FilterExpression = 'Active <> :val1',
    ExpressionAttributeValues = {
      ":val1" : 'NO'
    }
  )
  return response    