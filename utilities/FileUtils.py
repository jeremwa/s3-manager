import yaml


def save_file(parameters):
    filename = parameters['bucket-name'] + '.yml'
    with open(filename, 'w') as outfile:
        yaml.safe_dump(parameters, outfile, default_flow_style=False)