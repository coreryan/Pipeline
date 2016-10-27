import json, boto3, logging
def handler(event, context):
  CONFIG = pull_config(context)
  print type(CONFIG)
  EVENT_TABLE = CONFIG['EVENT_TABLE']
  STATUS_TABLE = CONFIG['STATUS_TABLE']
  s3 = boto3.client('s3')
  response = s3.list_objects(
    Bucket = CONFIG['ARTIFACT_BUCKET']
  )
  print response['Contents'] 
  for key in response['Contents']:
    if (".json" in key['Key'] or ".template" in key['Key'] or ".yaml" in key['Key']) and not ("master-" in key['Key']):
      print "Processing " + key['Key']
      STRIPPED = key['Key'].rsplit('/', 1)
      STRIPPED.reverse()
      response = spin_stack(STRIPPED[0], CONFIG['ARTIFACT_BUCKET'], CONFIG['SNSTOPIC'])
      ddb_status_write(STATUS_TABLE, response, STRIPPED[0],"INITIALIZED")

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

def ddb_status_write(TABLE, CFN_DATA, FULL_KEY, CURRENT_STATUS):
  ddb = boto3.resource('dynamodb')
  table = ddb.Table(TABLE)
  print "Writing Initilizing"
  S3_KEY = FULL_KEY.rsplit('.', 1)
  table.put_item(
    Item={
      'StackId' : CFN_DATA['StackId'],
      'Active' : CURRENT_STATUS,
      'StackName' : S3_KEY[0]
    }
  )
def spin_stack(FILE_NAME, BUCKET, SNSTOPIC):
  try:
    S3_KEY = FILE_NAME.rsplit('.', 1)
    print S3_KEY
    TEMPLATE_URL = "https://" + BUCKET + ".s3.amazonaws.com/templates/" + FILE_NAME
    cfn = boto3.client('cloudformation')
    response = cfn.create_stack(
      StackName = S3_KEY[0],
      TemplateURL = TEMPLATE_URL,
      NotificationARNs=[SNSTOPIC],
      Capabilities = ['CAPABILITY_NAMED_IAM'],
      OnFailure = 'DO_NOTHING'
    )
    return response
  except:
    raise