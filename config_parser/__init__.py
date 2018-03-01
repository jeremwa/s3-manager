import yaml
import boto3
import json
from jsonschema import validate
from jsonschema import ValidationError


class ConfigParser(object):
    def __init__(self, **kwargs):
        self.base_config = kwargs.get("BaseConfig")
        self.bucket_config = kwargs.get("BucketConfig")
        self.parsed_data = {}
        self.bucket_name = kwargs.get("BucketName")
        self.logging_bucket_name = kwargs.get("LoggingBucketName")
        pass

    def parse(self):
        self.replace_template()
        self.parsed_data = self.parse_bucket_policy()

    def get_account(self):
        acct = boto3.client('sts').get_caller_identity().get('Account')
        return acct

    def replace_template(self):
        acct = self.get_account()
        config = json.dumps(self.base_config).replace('LOGGING-BUCKET-NAME', self.logging_bucket_name).replace('BUCKET-NAME', self.bucket_name)
        self.parsed_data = json.loads(config)

    def get_bucket_security_policy(self):
        if self.bucket_config and 'bucket-security-policy' in self.bucket_config:
            return self.bucket_config['bucket-security-policy']
        else:
            return json.loads('{"Version":"2012-10-17","Statement":[]}')
            
    def get_lifecycle_policy(self):
        if self.bucket_config and 'life-cycle-rules' in self.bucket_config:
            return self.bucket_config['life-cycle-rules']
        else:
            return self.base_config['life-cycle-rules']

    def get_bucket_metrics_policy(self):
        if self.bucket_config and 'bucket-metrics' in self.bucket_config:
            return self.bucket_config['bucket-metrics']
        else:
            return self.base_config['bucket-metrics']

    def get_bucket_analytics_policy(self):
        if self.bucket_config and 'bucket-analytics' in self.bucket_config:
            return self.bucket_config['bucket-analytics']
        else:
            return self.base_config['bucket-analytics']

    def get_logging_policy(self):
        if self.bucket_config and 'logging-rules' in self.bucket_config:
            return self.bucket_config['logging-rules']
        else:
            return self.base_config['logging-rules']
            
    def parse_lifecycle_policy(self):
        self.parsed_data['life-cycle-rules'] = self.get_lifecycle_policy()

    def parse_bucket_policy(self):
        policy = self.get_bucket_security_policy()

        existing_statements = set()
        for statement in policy['Statement']:
            for attribute, value in statement.iteritems():
                if attribute == 'Sid':
                    existing_statements.add(value)
    
        for statement in self.base_config['bucket-security-policy']['Statement']:
            for attribute, value in statement.iteritems():
                if (attribute == 'Sid' and value not in existing_statements):
                    if (value == 'RequiredSecureTransport' and TagUtils.is_tag_in_tagset('exception-https', self.bucket_config['bucket-tags']['TagSet'])):
                        continue
                    if (value == 'RequiredEncryptedPutObject' and TagUtils.is_tag_in_tagset('exception-encryption', self.bucket_config['bucket-tags']['TagSet'])):
                        continue
                    json_statement = json.dumps(statement)
                    policy['Statement'].append(json.loads(json_statement))
    
        # Only include bucket policy if there are any statements
        if len(policy['Statement']) > 0:
            self.parsed_data['bucket-security-policy'] = policy


    def parse_bucket_analytics_policy(self):
        self.parsed_data['bucket-analytics'] = self.get_bucket_analytics_policy()

    def parse_logging_policy(self):
        self.parsed_data['logging-rules'] = self.get_logging_policy()

    
    def parse_tags(self):
        tags = []
        if self.bucket_config and 'bucket-tags' in self.bucket_config and 'TagSet' in self.bucket_config['bucket-tags']:
            for item in self.bucket_config['bucket-tags']['TagSet']:
               tags.append(item)
               
        if 'bucket-tags' in self.base_config and 'TagSet' in self.base_config['bucket-tags']:
            for item in self.base_config['bucket-tags']['TagSet']:
               tags.append(item)
               
        self.parsed_data['bucket-tags'] = {}
        self.parsed_data['bucket-tags']['TagSet'] = tags

    def parse_bucket_metrics_policy(self):
        self.parsed_data['bucket-metrics'] = self.get_bucket_metrics_policy()