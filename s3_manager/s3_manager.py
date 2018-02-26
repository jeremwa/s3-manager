#!/usr/bin/env python
import boto3
import botocore.exceptions
import json
import logging
import stdconfig.Evaluation as Evaluation
import utilities.Validation as Validation
import utilities.FileUtils as FileUtils
import utilities.TagUtils as TagUtils
import yaml
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter


myhandler = logging.StreamHandler()  # writes to stderr
myformatter = logging.Formatter(fmt='%(levelname)s: %(message)s')
myhandler.setFormatter(myformatter)


# Set up Logging
LOG_LEVEL = logging.WARN
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logging.getLogger('boto3').setLevel(logging.WARN)
logger.addHandler(myhandler)

tagargs = []


def bucket_tags(tag_string):
    """Parses the string passed into the tag argument
    and returns a list of tags."""
    if ':' not in tag_string:
        raise Exception("Malformed tag: {}. Proper form is key:value".format(tag_string))
    key, value = tag_string.split(":", 1)
    tagargs.append({'Key': key, 'Value': value})


# Organize Args
parser = ArgumentParser(description="S3 Util Args", formatter_class=RawTextHelpFormatter)
parser.add_argument("action", nargs=1, choices=['create', 'create-logging-bucket', 'update', 'delete', 'config', 'retrieve-config', 'test'],
                    help="Action on S3 Bucket - \n"
                         " create                 -  Create a new bucket with the supplied config file [--config] REQUIRED\n"
                         " create-logging-bucket  -  Create a logging bucket for a region\n"
                         " update                 -  Update a bucket based on the supplied config file [--config] REQUIRED\n"
                         " delete                 -  NOT ENABLED\n"
                         " retrieve-config        -  Retrieve the s3 configuration of a specified S3 Bucket [--bucketname] REQUIRED\n"
                         " config                 -  Evaluate against a standard configuration file [--standardconfig] REQUIRED\n"
                         " test                   -  FOR DEBUG PURPOSES ONLY\n")
parser.add_argument("-c", "--config", required=False,
                    help="Config file to use for action")
parser.add_argument("-p", "--profile", required=False,
                    help="AWS Profile as stored in ~/.aws/credentials")
parser.add_argument("-r", "--region", required=False,
                    help="For use when Creating Logging Bucket")
parser.add_argument("-V", "--validate", required=False,
                    help="Validates specified config file against schema")
parser.add_argument("-b", "--bucketname", required=False,
                    help="Specify Bucketname; to be used with CONFIG")
parser.add_argument("-s", "--standardconfig", required=False,
                    help="Standard Configuration to apply to bucket; to be used with CREATE and UPDATE")
parser.add_argument("-l", "--standardlogconfig", required=False,
                    help="Standard Configuration to apply to logging bucket; to be used with CREATE-LOGGING-BUCKET")
parser.add_argument("-t", "--tag", required=False, type=bucket_tags,
                    help="Tags to apply to the bucket; to be used with CREATE and UPDATE\n"
                        "Required Tags (for compliance): Owner, Stack, Stage, App, orbProjectId\n"
                        "Exception Tags: exception-https, exception-encryption\n"
                        "Example: -t stack:test -t stage:test -t owner:test -t app:test -t orbProjectId:1")

args = parser.parse_args()

PROFILE='default'  #

# Set Profile to run as
if args.profile != 'default':
    PROFILE = args.profile

session = boto3.Session(profile_name=PROFILE)  # Establish AWS Session
client = session.client('s3')  # Establish S3 Connection
s3 = session.resource('s3')    # Get S3 Resource Object

standardparameters = None
standardlogparameters = None

def main():

    global standardparameters
    global standardlogparameters

    if args.standardconfig:
        standardparameters = _load_standard_parameters()
    if args.standardlogconfig:
        standardlogparameters = _load_standard_log_parameters()

    if 'test' in args.action:
        parameters = Validation.open_and_validate_config(args.config, logger)
        print TagUtils.is_tag_in_tagset('Stacks', parameters['bucket-tags']['TagSet'])

    elif 'create-logging-bucket' in args.action:
        if args.region == None:
            logger.error("No Region Specified")
            return
        _create_logging_bucket(args.region)

    elif 'retrieve-config' in args.action:
        _fetch_config(args.bucketname)

    else:
        parameters = {}
        if args.config:
            parameters = Validation.open_and_validate_config(args.config, logger)
        if args.bucketname:
            parameters['bucket-name'] = args.bucketname
        if args.region:
            parameters['region'] = args.region
        if tagargs != []:
            if 'bucket-tags' in parameters:
                # Prefer user input
                for tag_arg in tagargs:
                    found = False
                    for tag in parameters['bucket-tags']['TagSet']:
                        if tag_arg['Key'] == tag['Key']:
                            found = True
                            tag['Value'] = tag_arg['Value']
                    # Add cli tags not found in yml
                    if not found:
                        parameters['bucket-tags']['TagSet'].append({'Key': tag_arg['Key'], 'Value': tag_arg['Value']})

            else:
                parameters['bucket-tags'] = {'TagSet': tagargs}

        if 'create' in args.action:
            _create_from_config(parameters)
        elif 'update' in args.action:
            _update_from_config(parameters)
        elif 'config' in args.action:
            if args.standardconfig == None:
                logger.error("No Standard Configuration Provided [--standardconfig]")
                return
            parameters = Validation.open_and_validate_config(args.config, logger)

            _apply_standard_config(parameters, standardparameters)

def _load_standard_parameters():
    try:
        with open(args.standardconfig, 'r') as standard_file:
            parameters = yaml.load(standard_file)
    except:
        logger.error("Error opening file: {0}".format(args.standardconfig))
        return None

    return parameters

def _load_standard_log_parameters():
    try:
        with open(args.standardlogconfig, 'r') as standard_log_file:
            parameters = yaml.load(standard_log_file)
    except:
        logger.error("Error opening file: {0}".format(args.standardlogconfig))
        return None

    return parameters

def _create_from_config(parameters):
    '''
    This creates a bucket based on defaults or config
    :return:
    '''

    # Check if Bucket Already Exists
    try:
        s3.Bucket(parameters['bucket-name']).load()
        logger.warn("Bucket Already Exists")
        return
    except botocore.exceptions.ClientError:
        logger.info("Creating {}".format(parameters['bucket-name']))

    # S3 assumes US-Standard unless otherwise specified and does not accept us-east-1 as an option
    if parameters['region'] == 'us-east-1':
        bucket = client.create_bucket(Bucket=parameters['bucket-name'])
    else:
        bucket = client.create_bucket(Bucket=parameters['bucket-name'], CreateBucketConfiguration={'LocationConstraint': parameters['region'] })

    _update_from_config(parameters)


def _update_from_config(parameters):
    '''
    This creates a bucket based on defaults or config
    :return:
    '''

    # Check if Bucket Already Exists
    try:
        s3.Bucket(parameters['bucket-name']).load()
        logger.info("Updating: {}".format(parameters['bucket-name']))
    except botocore.exceptions.ClientError as e:
        logger.warn("Bucket Error ({}) {}".format(parameters['bucket-name'], e))
        return

    if standardparameters != None:
        _apply_standard_config(parameters, standardparameters)

    # Apply S3 Bucket Policy
    if 'bucket-security-policy' in parameters:
        _apply_bucket_policy(parameters)

    # Apply Lifecycle Policy
    if 'life-cycle-rules' in parameters:
        _apply_lifecycle_policy(parameters)

    # Apply Logging Rules
    if 'logging-rules' in parameters:
        _apply_bucket_logging(parameters)

    # Apply Tagging Rules if 'bucket-tags' in parameters:
    if 'bucket-tags' in parameters:
        _apply_bucket_tags(parameters)

    # Apply Analytics Rules
    if 'bucket-analytics' in parameters:
        _apply_bucket_analytics_configuration(parameters)

    # Apply Metrics Configuration
    if 'bucket-metrics' in parameters:
        _apply_bucket_metrics_configuration(parameters)

def _fetch_config(bucket_name):
    '''
    Retrieves the configuration from an existing S3 bucket and ouputs a yaml config file
    describing the bucket
    :return:
    '''
    bucket = s3.Bucket(bucket_name)
    logger.info("Pulling Config for Bucket: []".format(bucket_name))
    new_config_file = {'bucket-name': bucket_name}

    # Get Region
    region = client.get_bucket_location(Bucket=bucket_name)
    print "LC: ", region['LocationConstraint']
    if region['LocationConstraint'] == None:
        new_config_file['region'] = 'us-east-1'
    else:
        new_config_file['region'] = region['LocationConstraint']

    try:
        logger.info("Retrieving Lifecycle ")
        t = { 'Rules': client.get_bucket_lifecycle_configuration(Bucket=bucket_name)['Rules'] }
        new_config_file['life-cycle-rules'] = t
    except botocore.exceptions.ClientError:
        logger.info("No Lifecycle Attached")

    try:
        logger.info("Retrieving Policy ")
        new_config_file['bucket-security-policy'] = json.loads(bucket.Policy().policy)
    except botocore.exceptions.ClientError:
        logger.info("No Bucket Policy Attached")

    try:
        logger.info("Retrieving Logging Rules")
        logging_configuration = bucket.Logging().logging_enabled
        if logging_configuration is None:
            logger.info("No Logging Policy Attached")
        else:
            new_config_file['logging-rules'] = json.loads('{ "LoggingEnabled"  : ' + json.dumps(logging_configuration) + ' } ')
    except botocore.exceptions.ClientError:
        logger.info("No Logging Policy Attached")

    try:
        logger.info("Retrieving Tags")
        new_config_file['bucket-tags'] = json.loads('{ "TagSet"  : ' + json.dumps(bucket.Tagging().tag_set) + ' } ')
    except botocore.exceptions.ClientError:
        logger.info("No Tagging Policy Attached")

    try:
        logger.info("Retrieving Analytics Config")
        new_config_file['bucket-analytics'] = client.get_bucket_analytics_configuration(Bucket=bucket_name, Id='EntireBucketAnalytics')['AnalyticsConfiguration']
    except botocore.exceptions.ClientError:
        logger.info("No Analytics Config Attached")

    try:
        logger.info("Retrieving Metrics Config")
        new_config_file['bucket-metrics'] = \
        client.get_bucket_metrics_configuration(Bucket=bucket_name, Id='EntireBucket')['MetricsConfiguration']
    except botocore.exceptions.ClientError:
        logger.info("No Analytics Config Attached")


    FileUtils.save_file(new_config_file)


def _apply_standard_config(parameters, standardparameters):

    logger.info("Evaluating Bucket Parameters Against Standard Configuration")
    Evaluation.evaluate_bucket_tags(parameters, standardparameters)
    Evaluation.evaluate_bucket_policy(parameters,standardparameters)
    Evaluation.evaluate_lifecycle_policy(parameters, standardparameters)
    Evaluation.evaluate_bucket_logging(parameters, standardparameters)
    Evaluation.evaluate_bucket_analytics_configuration(parameters, standardparameters)
    Evaluation.evaluate_bucket_metrics_configuration(parameters, standardparameters)

    if args.config:
        parameters = Validation.open_and_validate_config(args.config, logger)
    else:
        parameters = Validation.open_and_validate_config(parameters['bucket-name'] + '.yml', logger)


def _create_logging_bucket(region):
    '''
    Creates a logging bucket
    :return:
    '''

    acct = boto3.client('sts').get_caller_identity().get('Account')
    logging_bucket_name = acct + '-bucket-logs-' + region

    # Check if Bucket Already Exists
    try:
        s3.Bucket(logging_bucket_name).load()
        logger.warn("Bucket Already Exists")

    except botocore.exceptions.ClientError:
        logger.info("Creating Log Bucket {}".format(logging_bucket_name))
        # S3 assumes US-Standard unless otherwise specified and does not accept us-east-1 as an option
        if region == 'us-east-1':
            bucket = client.create_bucket(Bucket=logging_bucket_name,ACL='log-delivery-write')
        else:
            bucket = client.create_bucket(Bucket=logging_bucket_name,ACL='log-delivery-write',
                                          CreateBucketConfiguration={'LocationConstraint': region})

    # Apply Logging Bucket Policy
    schema = """
    Rules:
    - AbortIncompleteMultipartUpload:
        DaysAfterInitiation: 7
      Expiration:
        Days: 400
      ID: STANDARD-CONFIG-BUCKET-NAME
      Prefix: ''
      Status: Enabled
      Transitions:
        - Days: 90
          StorageClass: GLACIER
        - Days: 30
          StorageClass: STANDARD_IA
    """
    if standardlogparameters == None:
        policy = json.loads(json.dumps(yaml.load(schema)).replace('STANDARD-CONFIG-BUCKET-NAME', logging_bucket_name))
        client.put_bucket_lifecycle_configuration(Bucket=logging_bucket_name,
                                                  LifecycleConfiguration=dict(policy))
    else:
        parameters = {'bucket-name': logging_bucket_name}
        parameters['region'] = region
        _apply_standard_config(parameters, standardlogparameters)
        _update_from_config(parameters)


def _apply_bucket_policy(parameters):
    try:
        client.put_bucket_policy(Bucket=parameters['bucket-name'], Policy=parameters['bucket-security-policy'])
    except:
        client.put_bucket_policy(Bucket=parameters['bucket-name'], Policy=json.dumps(parameters['bucket-security-policy']))

def _apply_lifecycle_policy(parameters):
    '''
    Loads lifecycle policy from config

    accepts LifecycleConfiguration as a string or json object.
    :param parameters:
    :return:
    '''
    try:
        client.put_bucket_lifecycle_configuration(Bucket=parameters['bucket-name'],
                                    LifecycleConfiguration=json.loads(parameters['life-cycle-rules'])
                                    )
    except:
        client.put_bucket_lifecycle_configuration(Bucket=parameters['bucket-name'],
                                    LifecycleConfiguration=parameters['life-cycle-rules']
                                    )


def _apply_bucket_logging(parameters):
    try:
        acct = boto3.client('sts').get_caller_identity().get('Account')
        logging_bucket_name = acct + '-bucket-logs-' + parameters['region']
        s3.Bucket(logging_bucket_name).load()
    except botocore.exceptions.ClientError:
        _create_logging_bucket(parameters['region'])


    try:
        client.put_bucket_logging(Bucket=parameters['bucket-name'],
                                  BucketLoggingStatus=json.loads(parameters['logging-rules'])
                                  )
    except TypeError:
        client.put_bucket_logging(Bucket=parameters['bucket-name'],
                                  BucketLoggingStatus=parameters['logging-rules'])

def _apply_bucket_tags(parameters):
    try:
        tagset = json.loads(parameters['bucket-tags']['TagSet'])
    except TypeError:
        tagset = parameters['bucket-tags']['TagSet']

    # Filter out empty tags
    tagset = list(e for e in tagset if e['Value'])

    client.put_bucket_tagging(Bucket=parameters['bucket-name'],
                              Tagging={ 'TagSet': tagset })


def _apply_bucket_analytics_configuration(parameters):
    try:
        client.put_bucket_analytics_configuration(Bucket=parameters['bucket-name'],
                                                  Id=parameters['bucket-analytics']['Id'],
                                                  AnalyticsConfiguration=json.loads(parameters['bucket-analytics'])
                                  )
    except TypeError:
        client.put_bucket_analytics_configuration(Bucket=parameters['bucket-name'],
                                                  Id=parameters['bucket-analytics']['Id'],
                                                  AnalyticsConfiguration=dict(parameters['bucket-analytics']))


def _apply_bucket_metrics_configuration(parameters):


    try:
        client.put_bucket_metrics_configuration(Bucket=parameters['bucket-name'],
                                                  Id=parameters['bucket-metrics']['Id'],
                                                MetricsConfiguration=json.loads(parameters['bucket-metrics'])
                                                )
    except TypeError:
        client.put_bucket_metrics_configuration(Bucket=parameters['bucket-name'],
                                                  Id=parameters['bucket-metrics']['Id'],
                                                MetricsConfiguration=parameters['bucket-metrics'])


if __name__ == "__main__":
    main()



