import json, boto3, time
from boto3.dynamodb.conditions import Key, Attr
def handler(event, context):    #10
  print event
  config = pull_config(context)
  print config
  try:
    event['INITIALRUN']
  except KeyError:
    print "NormalRun"
    normal_run(event, config)
  else:
    print "InitialRun"
    initial_run(event, config)
  return
def initial_run(event, config):
  try:
    print event
    TEMPLATE_URL = 'https://' + event['ARTIFACT_BUCKET'] + '.s3.amazonaws.com/templates/' + event['MASTER_STACK_NAME']['Full']
    STACK_NAME = "master-" + event['SERVICE']
    cfn = boto3.client('cloudformation')
    response = cfn.create_stack(
      StackName = event['MASTER_STACK_NAME']['Name'],
      TemplateURL = TEMPLATE_URL,
      NotificationARNs=[event['SNSTOPIC']],
      Capabilities = ['CAPABILITY_NAMED_IAM'],
      OnFailure = 'DO_NOTHING'
    )
    return response
  except:
    raise
def normal_run(event, CONFIG):
  CFN_DATA = parse_cfn(event)

  EVENT_TABLE = CONFIG['EVENT_TABLE']
  STATUS_TABLE = CONFIG['STATUS_TABLE']
  FAILED = "_FAILED"
  RESOURCE_STATUS = CFN_DATA['ResourceStatus']
  RESOURCE_TYPE = CFN_DATA['ResourceType']

  if  "AWS::CloudFormation::Stack" in RESOURCE_TYPE: #20
    print CFN_DATA
    if "CREATE_IN_PROGRESS" in CFN_DATA['ResourceStatus']:
      print "CREATE_IN_PROGRESS handler"
      ddb_status_write(STATUS_TABLE, CFN_DATA, "PENDING")
      ddb_event_write(EVENT_TABLE, CFN_DATA)
    elif "CREATE_COMPLETE" in CFN_DATA['ResourceStatus']:
      print "CREATE_COMPLETE HANDLER"
      ddb_event_write(EVENT_TABLE, CFN_DATA)
      if "master-" in CFN_DATA['StackName']: #If master stack is in CREATE_COMPLETE kick off the rest of the stacks
        print "Master stack handler"
        client = boto3.client('lambda')
        response = client.invoke(
          FunctionName=CONFIG['PROCESS_TEMPLATES'],
          InvocationType='RequestResponse', 
          LogType='None'
        )
        print response
      else:
        print "Checking for complete"
        check_for_complete(STATUS_TABLE, CONFIG['PROCESS_CLEANUP'])
    elif "DELETE_COMPLETE" in CFN_DATA['ResourceStatus']:
      print "DELETE_COMPLETE HANDLER"
      ddb_event_write(EVENT_TABLE, CFN_DATA)
    else: #Something weird
      print "CATCH ALL HANDLER"
      ddb_event_write(EVENT_TABLE, CFN_DATA)
  if 'FAILED' in CFN_DATA['ResourceStatus']: #Catch and process failed events
    print "FAILED HANDLER"
    ddb_event_write(EVENT_TABLE, CFN_DATA)

def check_for_complete(STATUS_TABLE, CLEANUP_FUNCTION):
  print "CHECKING for complete"
  time.sleep(2) #Found that there was a slight delay with getting the Stream data written to the table
  ddb = boto3.resource('dynamodb')
  table = ddb.Table(STATUS_TABLE)
  response = table.scan(
    TableName=STATUS_TABLE,
    Select='ALL_ATTRIBUTES',
    FilterExpression = 'Active = :val1',
    ExpressionAttributeValues = { 
      ":val1" : 'PENDING'
    }
  )

  print response
  if response['Count'] == 0:
    print "Nothing in pending. Cleaning up"
    client = boto3.client('lambda')
    response = client.invoke(
      FunctionName=CLEANUP_FUNCTION,
      InvocationType='RequestResponse', 
      LogType='None'
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

def ddb_status_write(TABLE, CFN_DATA, CURRENT_STATUS):
  ddb = boto3.resource('dynamodb')
  table = ddb.Table(TABLE)
  print "Writing " + CFN_DATA['ResourceStatus']
  
  table.put_item(
    Item={
      'StackId' : CFN_DATA['StackId'],
      'Active' : CURRENT_STATUS,
      'StackName' : CFN_DATA['StackName'], #30
      'StackStatus' : CFN_DATA['ResourceStatus'], 
      'StampTime' : CFN_DATA['Timestamp']
    }
  )  
def ddb_event_write(TABLE, CFN_DATA):
  ddb = boto3.resource('dynamodb')
  table = ddb.Table(TABLE)
  print "Writing " + CFN_DATA['ResourceStatus']
  table.put_item(
    Item={
      'StackId' : CFN_DATA['StackId'],
      'StackName' : CFN_DATA['StackName'],
      'StampTime' : CFN_DATA['Timestamp'],
      'ResourceType' : CFN_DATA['ResourceType'],         
      'ResourceStatus' : CFN_DATA['ResourceStatus'],
      "LogicalResourceId" : CFN_DATA['LogicalResourceId']
    }
  )   
def parse_cfn(event):
  snsmessage = event['Records'][0]['Sns']['Message'] 
  MESSAGE_CONTENTS = {}
  cfndetails = snsmessage.replace('\n', '').replace('\r', '')
  groups = cfndetails.split("'")
  TotalCount = (len(groups) / 2)
  for Current in xrange(TotalCount):
    n =  2
    Property = "'".join(groups[:n])
    Explode = Property.split('=')
    PropertyName = Explode[0]
    PropertyValue = Explode[1].replace("'", '')
    groups = "'".join(groups[n:])
    groups = groups.split("'")
    MESSAGE_CONTENTS.update({PropertyName:PropertyValue})
  return MESSAGE_CONTENTS