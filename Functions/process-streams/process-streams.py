import json, boto3, logging

def handler(event, context):
  CONFIG = pull_config(context)
  STATUS_TABLE = CONFIG['STATUS_TABLE']
  print event
  RECORD = event['Records'][0]
  EVENT_NAME = RECORD['eventName']
  if EVENT_NAME != 'REMOVE':

    STACK_NAME = RECORD['dynamodb']['NewImage']['StackName']['S']
    TIME_STAMP = RECORD['dynamodb']['NewImage']['StampTime']['S']
    NEW_STATUS = RECORD['dynamodb']['NewImage']['ResourceStatus']['S']
    STACK_ID = RECORD['dynamodb']['NewImage']['StackId']['S']
    SKIP = 'False'
    if "CREATE_COMPLETE" in NEW_STATUS:
      UPDATE_STATUS = 'DONE'
      TESTING_STATUS = 'PASSED'
    elif "DELETE_COMPLETE" in NEW_STATUS: 
      UPDATE_STATUS = 'NO'
      SKIP = 'True'
    elif "CREATE_FAILED" in NEW_STATUS:
      UPDATE_STATUS = 'FAILED'
      TESTING_STATUS = 'FAILED'
    elif "DELETE_IN_PROGRESS" in NEW_STATUS:
      UPDATE_STATUS = 'PENDING'
      SKIP = 'True'
    else:
      UPDATE_STATUS = 'PENDING'
      SKIP = 'True'

    ddb = boto3.resource('dynamodb')
    table = ddb.Table(STATUS_TABLE)
    if 'True' in SKIP:
      table.update_item(
        Key = {
          'StackName': STACK_NAME
        },
        UpdateExpression='SET StampTime = :val1, StackStatus = :val2, StackId = :val3, Active = :val4',
        ExpressionAttributeValues = {
          ':val1': TIME_STAMP,
          ':val2': NEW_STATUS,
          ':val3': STACK_ID,
          ':val4': UPDATE_STATUS
        }
      )
    else:
      table.update_item(
        Key = {
          'StackName': STACK_NAME
        },
        UpdateExpression='SET StampTime = :val1, StackStatus = :val2, StackId = :val3, Active = :val4, Testing = :val5',
        ExpressionAttributeValues = {
          ':val1': TIME_STAMP,
          ':val2': NEW_STATUS,
          ':val3': STACK_ID,
          ':val4': UPDATE_STATUS,
          ':val5': TESTING_STATUS
        }
      )
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