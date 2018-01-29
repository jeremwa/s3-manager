import boto3
import json
import utilities.FileUtils as FileUtils
import utilities.TagUtils as TagUtils



def evaluate_bucket_policy(parameters,standardparameters):

    #Required policies
    RequiredSecureTransport = False
    RequiredEncryptedPutObject = False
    policy = {}
    if 'bucket-security-policy' in parameters:
        try:
            policy = json.loads(parameters['bucket-security-policy'])
        except TypeError:
            policy = parameters['bucket-security-policy']
    else:
        value = '{"Version":"2012-10-17","Statement":[]}'
        policy = json.loads(value)

    acct = boto3.client('sts').get_caller_identity().get('Account')
    existing_statements = set()
    for statement in policy['Statement']:
        for attribute, value in statement.iteritems():
            if attribute == 'Sid':
                existing_statements.add(value)

    for standardstatement in standardparameters['bucket-security-policy']['Statement']:
        for attribute, value in standardstatement.iteritems():
            if (attribute == 'Sid' and value not in existing_statements):
                if (value == 'RequiredSecureTransport' and TagUtils.is_tag_in_tagset('exception-https', parameters['bucket-tags']['TagSet'])):
                    continue
                if (value == 'RequiredEncryptedPutObject' and TagUtils.is_tag_in_tagset('exception-encryption', parameters['bucket-tags']['TagSet'])):
                    continue
                value = json.dumps(standardstatement)
                value = value.replace('STANDARD-CONFIG-BUCKET-NAME', parameters['bucket-name'])
                value = value.replace('STANDARD-CONFIG-ACCOUNT-ID', acct)
                policy['Statement'].append(json.loads(value))

    # Only include bucket policy if there are any statements
    if len(policy['Statement']) > 0:
        parameters['bucket-security-policy'] = policy
    else:
        parameters.pop('bucket-security-policy', None)

    FileUtils.save_file(parameters)


def evaluate_bucket_analytics_configuration(parameters,standardparameters):
    # Get Profile Account Number
    acct = boto3.client('sts').get_caller_identity().get('Account')
    value = json.dumps(standardparameters['bucket-analytics'])
    value = value.replace('STANDARD-CONFIG-BUCKET-NAME',parameters['bucket-name'])
    logging_bucket_name = acct + '-bucket-logs-' + parameters['region']
    value = value.replace('STANDARD-CONFIG-LOGGING-BUCKET-NAME', logging_bucket_name)

    # No Storage
    value = value.replace('null', '{}')
    parameters['bucket-analytics'] = json.loads(value)

    FileUtils.save_file(parameters)


def evaluate_lifecycle_policy(parameters,standardparameters):
    policy = {}

    if 'life-cycle-rules' in parameters:
        try:
            policy = json.loads(parameters['life-cycle-rules'])
        except TypeError:
            policy = parameters['life-cycle-rules']
    else:
        value = json.dumps(standardparameters['life-cycle-rules']).replace('STANDARD-CONFIG-BUCKET-NAME'
                                                                                 , parameters['bucket-name'])
        policy = json.loads(value)

    # Test for multi-part upload policy
    if 'AbortIncompleteMultipartUpload' not in policy['Rules']:
        value = json.dumps(standardparameters['life-cycle-rules']['Rules'][0]['AbortIncompleteMultipartUpload'])
        value = value.replace('STANDARD-CONFIG-BUCKET-NAME',parameters['bucket-name'])
        policy['Rules'][0]['AbortIncompleteMultipartUpload'] = json.loads(value)

        parameters['life-cycle-rules'] = policy

        FileUtils.save_file(parameters)


def evaluate_bucket_logging(parameters,standardparameters):
    # If logging not enabled, apply standard logging
    if 'logging-rules' not in standardparameters:
        # Probably doing a logging bucket
        return

#    if 'logging-rules' not in parameters:
# Always overwrite existing logging configuration
    if True:
        acct = boto3.client('sts').get_caller_identity().get('Account')
        logging_bucket_name = acct + '-bucket-logs-' + parameters['region']

        value = json.dumps(standardparameters['logging-rules'])
        value = value.replace('STANDARD-CONFIG-LOGGING-BUCKET-NAME', logging_bucket_name)
        value = value.replace('STANDARD-CONFIG-BUCKET-NAME', parameters['bucket-name'])

        parameters['logging-rules'] = json.loads(value)

        FileUtils.save_file(parameters)


def evaluate_bucket_tags(parameters,standardparameters):

    # If logging not enabled, apply standard logging
    if 'bucket-tags' not in parameters:
        parameters['bucket-tags'] = {}
        value = json.dumps(standardparameters['bucket-tags']['TagSet'])
        policy = json.loads(value)
    else:
        # Add required Tags if Missing
        policy = parameters['bucket-tags']['TagSet']

        for standard in standardparameters['bucket-tags']['TagSet']:
            for tag in policy:
                if standard['Key'] == tag['Key']:
                    break
            else:
                policy.append(standard)

    parameters['bucket-tags']['TagSet'] = policy
    FileUtils.save_file(parameters)


def evaluate_bucket_metrics_configuration(parameters,standardparameters):
    if 'bucket-metrics' not in parameters:
        value = json.dumps(standardparameters['bucket-metrics'])
        policy = json.loads(value)
        parameters['bucket-metrics'] = policy
    FileUtils.save_file(parameters)

