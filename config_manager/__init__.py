import yaml
from jsonschema import validate
from jsonschema import ValidationError


class ConfigManager(object):
    def __init__(self, **kwargs):
        self.schema = kwargs.get("schema")
        self.logger = kwargs.get("logger")

    def read_yaml(self, file):
        # Open Config File
        try:
            with open(file, 'r') as config_file:
                contents = yaml.load(config_file)
            if self.is_valid(contents):
                return contents
            else:
                raise ValidationError('{} is not a valid config file'.format(file))
        except Exception as ex:
            self.logger.error("Error opening {}: {}".format(file, ex))
            return None

    def is_valid(self, data):
        '''
        Validates config file for consistancy
        :return boolean:
        '''
        try:
            validate(data, yaml.load(self.schema))  # passes
        except ValidationError as e:
            self.logger.error("Config file Failed Validation: {}"
                              .format(str(e)))
            return False

        return True
