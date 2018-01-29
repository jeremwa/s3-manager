
import yaml
from jsonschema import validate
from jsonschema import ValidationError

def open_and_validate_config(file, logger):
    # Open Config File
    try:
        with open(file, 'r') as config_file:
            parameters = yaml.load(config_file)
    except:
        logger.error("Error opening file: {0}".format(file))
        return None
    # Check if Valid Config File
    if not validate_config(parameters,logger):
        return None

    return parameters


def validate_config(_yml, logger):
    '''
    Validates config file for consistancy
    :return boolean:
    '''
    schema = """
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
    try:
        validate(_yml, yaml.load(schema))  # passes
    except ValidationError as e:
        logger.error("Config file Failed Validation: {}".format(str(e)))
        return False

    return True