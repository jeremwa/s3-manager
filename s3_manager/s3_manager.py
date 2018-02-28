#!/usr/bin/env python
import boto3
import logging
import click
from config_manager import ConfigManager


myhandler = logging.StreamHandler()  # writes to stderr
myformatter = logging.Formatter(fmt='%(levelname)s: %(message)s')
myhandler.setFormatter(myformatter)


# Set up Logging
LOG_LEVEL = logging.ERROR
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logging.getLogger('boto3').setLevel(logging.ERROR)
logger.addHandler(myhandler)

tagargs = []

session = boto3.Session()  # Establish AWS Session
client = session.client('s3')  # Establish S3 Connection
s3 = session.resource('s3')    # Get S3 Resource Object

config_schema = """
    type: object
    properties:
      bucket-name:
        type: string
      region:
        type: string
      bucket-security-policy:
        type: object
      life-cycle:
        type: object
    required:
      - bucket-name
      - region
    """


class Settings(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


settings = Settings()


@click.group()
@click.option('--standard/--logging', default=True)
@click.option('--bucket-name', help='Name of the bucket')
@click.option('--create-region', help='Region where to create bucket',
              default='us-east-1')
@click.option('--config', help='yaml config file')
def cli(standard, create_region, bucket_name, config):
    settings.is_standard = standard
    settings.create_region = create_region
    settings.bucket_name = bucket_name
    config_manager = ConfigManager(schema=config_schema)
    settings.config = config_manager.read_yaml(config)
    pass


@cli.command()
def create():
    '''
    Create a bucket
    '''

    # Check if Bucket Already Exists
    if s3.Bucket(settings.bucket_name) in s3.buckets.all():
        logger.warn("Bucket Already Exists")
        click.echo("Bucket already exists . . . skipping create")
        return

    # S3 assumes US-Standard unless otherwise specified and does not accept
    # us-east-1 as an option
    if settings.create_region == 'us-east-1':
        click.echo("Creating bucket {}".format(settings.bucket_name))
        client.create_bucket(Bucket=settings.bucket_name)
    else:
        click.echo("Creating bucket {} in region {}"
                   .format(settings.bucket_name, settings.create_region))
        client.create_bucket(Bucket=settings.bucket_name,
                             CreateBucketConfiguration={'LocationConstraint':
                                                        settings.create_region})


if __name__ == '__main__':
    cli()
