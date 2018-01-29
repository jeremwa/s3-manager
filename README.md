##      ----Help----
```
usage: s3-util.py [-h] [-c CONFIG] [-p PROFILE] [-r REGION] [-V VALIDATE]
                  [-b BUCKETNAME] [-s STANDARDCONFIG]
                  {create,create-logging-bucket,update,delete,config,retrieve-config,test}

S3 Util Args

positional arguments:
  {create,create-logging-bucket,update,delete,config,retrieve-config,test}
                        Action on S3 Bucket - 
                         create                 -  Create a new bucket supplied config file [--config] REQUIRED
                         create-logging-bucket  -  Creates a Logging bucket for a region
                         update                 -  Updates a bucket based on supplied config file [--config] REQUIRED
                         delete                 -  NOT ENABLED
                         retrieve-config        -  Retrieves the s3 configuration of a specified S3 Bucket [--bucketname] REQUIRED
                         config                 -  Only Evaluates against a standard configuration file [--standardconfig] REQUIRED
                         test                   -  FOR DEBUG PURPOSES ONLY

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Specify config file to use for Action
  -p PROFILE, --profile PROFILE
                        AWS Profile as Stored in ~/.aws/credentials
  -r REGION, --region REGION
                        For use when Creating Logging Bucket
  -V VALIDATE, --validate VALIDATE
                        Validates specified config file against schema
  -b BUCKETNAME, --bucketname BUCKETNAME
                        Specify Bucketname; to be used with CONFIG
  -s STANDARDCONFIG, --standardconfig STANDARDCONFIG
                        Standard Configuration to apply to bucket; to be used with CREATE and UPDATE
  -l STANDARDLOGCONFIG, --standardlogconfig STANDARDLOGCONFIG
                        Standard Configuration to apply to logging bucket; to be used with CREATE-LOGGING-BUCKET
  -t TAG, --tag TAG
                        Tag to apply to the bucket; to be used with CREATE and UPDATE
                        Required Tags (for compliance): Owner, Stack, Stage, App, orbProjectId
                        Exception Tags: exception-https, exception-encryption
                        Example: -t stack:test -t stage:test -t owner:test -t app:test -t orbProjectId:1
```