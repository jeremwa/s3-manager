from config_parser import ConfigParser
from mock import patch
import yaml
import json
import unittest
import uuid

bucket_config_with_bucket_metrics_yaml = """
bucket-name: my-bucket
bucket-security-policy:
  Statement:
  - Action: s3:*
    Condition:
      Bool:
        aws:SecureTransport: false
    Effect: Deny
    Principal: '*'
    Resource: arn:aws:s3:::STANDARD-CONFIG-BUCKET-NAME/*
    Sid: RequiredSecureTransport
bucket-metrics:
  Id: EntireBucket
"""

bucket_config_with_logging_rules_yaml = """
bucket-name: my-bucket
bucket-security-policy:
  Statement:
  - Action: s3:*
    Condition:
      Bool:
        aws:SecureTransport: false
    Effect: Deny
    Principal: '*'
    Resource: arn:aws:s3:::STANDARD-CONFIG-BUCKET-NAME/*
    Sid: RequiredSecureTransport
logging-rules:
  LoggingEnabled:
    TargetBucket: LOGGING-BUCKET-NAME
    TargetPrefix: BUCKET-NAME/
bucket-analytics:
  Id: EntireBucketAnalytics1
  StorageClassAnalysis:
    DataExport:
      Destination:
        S3BucketDestination:
          Bucket: arn:aws:s3:::LOGGING-BUCKET-NAME
          Format: CSV
          Prefix: _analytics/
      OutputSchemaVersion: V_1
"""

bucket_config_with_bucket_analytics_yaml = """
bucket-name: my-bucket
bucket-security-policy:
  Statement:
  - Action: s3:*
    Condition:
      Bool:
        aws:SecureTransport: false
    Effect: Deny
    Principal: '*'
    Resource: arn:aws:s3:::STANDARD-CONFIG-BUCKET-NAME/*
    Sid: RequiredSecureTransport
bucket-analytics:
  Id: EntireBucketAnalytics1
  StorageClassAnalysis:
    DataExport:
      Destination:
        S3BucketDestination:
          Bucket: arn:aws:s3:::LOGGING-BUCKET-NAME
          Format: CSV
          Prefix: _analytics/
      OutputSchemaVersion: V_1
"""

good_bucket_config_yaml = """
bucket-name: my-bucket
bucket-security-policy:
  Statement:
  - Action: s3:*
    Condition:
      Bool:
        aws:SecureTransport: false
    Effect: Deny
    Principal: '*'
    Resource: arn:aws:s3:::STANDARD-CONFIG-BUCKET-NAME/*
    Sid: RequiredSecureTransport
life-cycle-rules:
  Rules:
  - AbortIncompleteMultipartUpload:
      DaysAfterInitiation: 7
    Expiration:
      Days: 200
    ID: BUCKET-NAME
    Prefix: ''
    Status: Enabled
    Transitions:
      - Days: 30
        StorageClass: STANDARD_IA
"""

base_config_yaml = """
######################################################################################################################
# This is an example config file for the aws-s3-util                                                                 #
######################################################################################################################
# Dict:                                                                                                              #
# 'bucket-name'             :: name of the s3 bucket associated with the config file                                 #
# 'region'                  :: region in which the bucket is located, --us-east-1 is equivilant to US-Standard--     #
# 'bucket-security-policy'  :: json string of the bucket policy assigned to this bucket                              #
# 'life-cycle-rules'        :: json string of life cycle rules. This json is the input for the standard CLI          #
######################################################################################################################

bucket-name: BUCKET-NAME
region: us-east-1
bucket-security-policy:
  Statement:
  - Action: s3:*
    Condition:
      Bool:
        aws:SecureTransport: false
    Effect: Deny
    Principal: '*'
    Resource: arn:aws:s3:::BUCKET-NAME/*
    Sid: RequiredSecureTransport
  - Action: s3:PutObject
    Condition:
      "{}":
        s3:x-amz-server-side-encryption: true
    Effect: Deny
    Principal: '*'
    Resource: arn:aws:s3:::BUCKET-NAME/*
    Sid: RequiredEncryptedPutObject
  Version: '2012-10-17'
###
# prefix of effected resources
# Transition : expire | transition
# Status: enabled | disabled
# Days : integer of days until rule takes action
# Storage Class : STANDARD_IA | GLACIER  - only needed if transition
###
life-cycle-rules:
  Rules:
  - AbortIncompleteMultipartUpload:
      DaysAfterInitiation: 7
    Expiration:
      Days: 400
    ID: BUCKET-NAME
    Prefix: ''
    Status: Enabled
    Transitions:
      - Days: 30
        StorageClass: STANDARD_IA
logging-rules:
  LoggingEnabled:
    TargetBucket: LOGGING-BUCKET-NAME
    TargetPrefix: BUCKET-NAME/
bucket-analytics:
  Id: EntireBucketAnalytics
  StorageClassAnalysis:
    DataExport:
      Destination:
        S3BucketDestination:
          Bucket: arn:aws:s3:::LOGGING-BUCKET-NAME
          Format: CSV
          Prefix: _analytics/
      OutputSchemaVersion: V_1
bucket-metrics:
  Id: EntireBucket
bucket-tags:
  TagSet:
  - Key: Stack
    Value: ''
  - Key: App
    Value: ''
  - Key: Stage
    Value: ''
  - Key: Owner
    Value: ''
  - Key: orbProjectId
    Value: ''
"""

class ConfigParserTests(unittest.TestCase):
    def build_config_parser(self, get_account_mock, **kwargs):
        acct_num = str(uuid.uuid4())
        get_account_mock.return_value = acct_num
        base_config = yaml.load(base_config_yaml)
        bucket_config = yaml.load(kwargs.pop('BucketConfig', good_bucket_config_yaml))
        logging_bucket_name = str(uuid.uuid4())
        bucket_name = str(uuid.uuid4())
        config_parser = ConfigParser(LoggingBucketName=logging_bucket_name, BucketName=bucket_name, BaseConfig=base_config, BucketConfig=bucket_config)
        return config_parser
        

    def test_passing_base_config_sets_base_config(self):
        base_config = "baseconfig.yml"
        config_parser = ConfigParser(BaseConfig=base_config)
        assert(config_parser.base_config==base_config)
    
    
    def test_passing_bucket_config_sets_bucket_config(self):
        config = "baseconfig.yml"
        config_parser = ConfigParser(BucketConfig=config)
        assert(config_parser.bucket_config==config)
        
    
    def test_passing_bucket_name_sets_bucket_name(self):
        name = "test"
        config_parser = ConfigParser(BucketName=name)
        assert(config_parser.bucket_name==name)
        
    @patch('config_parser.ConfigParser.get_account')
    def test_replace_template_replaces_bucket_name(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock);
        config_parser.replace_template()
        assert(config_parser.bucket_name in json.dumps(config_parser.parsed_data) and "BUCKET-NAME" not in json.dumps(config_parser.parsed_data))
        
        
    @patch('config_parser.ConfigParser.get_account')
    def test_replace_template_replaces_logging_bucket_name(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock);
        config_parser.replace_template()
        assert(config_parser.logging_bucket_name in json.dumps(config_parser.parsed_data) and "LOGGING-BUCKET-NAME" not in json.dumps(config_parser.parsed_data))
        
        
    @patch('config_parser.ConfigParser.get_account')
    def test_get_bucket_policy_with_policy_returns_policy(self, get_account_mock):
        acct_num = str(uuid.uuid4())
        get_account_mock.return_value = acct_num
        config_parser = self.build_config_parser(get_account_mock, BucketConfig=good_bucket_config_yaml)
        policy = config_parser.get_bucket_security_policy()
        assert(policy==yaml.load(good_bucket_config_yaml)["bucket-security-policy"])

        
    @patch('config_parser.ConfigParser.get_account')
    def test_get_bucket_policy_without_bucket_policy_returns_empty_policy(self, get_account_mock):
        acct_num = str(uuid.uuid4())
        get_account_mock.return_value = acct_num
        config_parser = self.build_config_parser(get_account_mock, BucketConfig="")
        policy = config_parser.get_bucket_security_policy()
        assert(policy ==  json.loads('{"Version":"2012-10-17","Statement":[]}'))

    @patch('config_parser.ConfigParser.get_account')
    def test_get_bucket_lifecycle_policy_returns_bucket_lifecycle_policy(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock)
        config_parser.parse_lifecycle_policy()
        assert(config_parser.parsed_data['life-cycle-rules']==yaml.load(good_bucket_config_yaml)["life-cycle-rules"])

    @patch('config_parser.ConfigParser.get_account')
    def test_no_bucket_lifecycle_policy_returns_base_lifecycle_policy(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock, BucketConfig="")
        config_parser.parse_lifecycle_policy()
        assert(config_parser.parsed_data['life-cycle-rules']==yaml.load(base_config_yaml)["life-cycle-rules"])

    @patch('config_parser.ConfigParser.get_account')
    def test_bucket_analytics_parses_correctly(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock, BucketConfig="")
        config_parser.parse_bucket_analytics_policy()
        assert(config_parser.parsed_data['bucket-analytics']==yaml.load(base_config_yaml)["bucket-analytics"])

    @patch('config_parser.ConfigParser.get_account')
    def test_bucket_analytics_with_bucket_policy_returns_bucket_policy(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock, BucketConfig=bucket_config_with_bucket_analytics_yaml)
        config_parser.parse_bucket_analytics_policy()
        assert(config_parser.parsed_data['bucket-analytics']==yaml.load(bucket_config_with_bucket_analytics_yaml)["bucket-analytics"])

    @patch('config_parser.ConfigParser.get_account')
    def test_logging_rules_parses_correctly(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock, BucketConfig="")
        config_parser.parse_logging_policy()
        assert(config_parser.parsed_data['logging-rules']==yaml.load(base_config_yaml)["logging-rules"])

    @patch('config_parser.ConfigParser.get_account')
    def test_bucket_analytics_with_bucket_policy_returns_bucket_policy(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock, BucketConfig=bucket_config_with_bucket_analytics_yaml)
        config_parser.parse_logging_policy()
        assert(config_parser.parsed_data['logging-rules']==yaml.load(bucket_config_with_logging_rules_yaml)["logging-rules"])

    @patch('config_parser.ConfigParser.get_account')
    def test_no_bucket_tags_returns_base_tags(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock, BucketConfig="")
        config_parser.parse_tags()
        assert(config_parser.parsed_data['bucket-tags']==yaml.load(base_config_yaml)["bucket-tags"])

    @patch('config_parser.ConfigParser.get_account')
    def test_no_bucket_tags_returns_base_tags(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock, BucketConfig="")
        config_parser.parse_tags()
        assert(config_parser.parsed_data['bucket-tags']==yaml.load(base_config_yaml)["bucket-tags"])
        
    @patch('config_parser.ConfigParser.get_account')
    def test_no_bucket_metrics_returns_base_bucket_metrics(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock, BucketConfig="")
        config_parser.parse_bucket_metrics_policy()
        assert(config_parser.parsed_data['bucket-metrics']==yaml.load(base_config_yaml)["bucket-metrics"])
        
    @patch('config_parser.ConfigParser.get_account')
    def test_bucket_metrics_returns_bucket_metrics(self, get_account_mock):
        config_parser = self.build_config_parser(get_account_mock, BucketConfig=bucket_config_with_bucket_metrics_yaml)
        config_parser.parse_bucket_metrics_policy()
        assert(config_parser.parsed_data['bucket-metrics']==yaml.load(bucket_config_with_bucket_metrics_yaml)["bucket-metrics"])