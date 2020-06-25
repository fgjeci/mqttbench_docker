

class Keywords:
    CLUSTERS = 'clusters'
    TOPICS = 'topics'
    SUBS = 'sub_clients'
    PUBS = 'pub_clients'
    SUBS_COUNT = 'sub_count'
    PUBS_COUNT = 'pub_count'
    ALL = 'all'
    DEFAULT = 'default'
    CONTAINERS = 'containers'
    CONTAINER_NUMBER = 'number'
    CONTAINER_IP_RANGE = 'ip_range'
    CONTAINER_IP_RANGE_START = 'start'
    CONTAINER_IP_RANGE_STOP = 'stop'
    CONTAINER_BROKER = 'broker'
    DESCRIPTION = 'description'


class ConfigFileNotFoundError(Exception):
    def __init__(self, *args):
        if args:
            self.json_file = args[0]
        else:
            self.json_file = None

    def __str__(self):
        if self.json_file:
            return f'JSON config file not found : ' + self.json_file
        else:
            return f'JSON config file not found'


class TypeError(Exception):
    def __init__(self, *args):
        if args:
            self.parameter = args[0]
            self.type = args[1]
            try:
                self.position = args[2]
            except IndexError:
                self.position = None
        else:
            self.parameter = None
            self.type = None
            self.position = None

    def __str__(self):
        if self.parameter:
            _ret_str = f"The parameter {self.parameter} must be {self.type} type"
            if self.position:
                return _ret_str + ' ' + self.position
            return _ret_str
        else:
            return "Unexpected parameter type in the config file"


class FileNotFound(Exception):
    def __init__(self, *args):
        if args:
            self.parameter = args[0]
        else:
            self.parameter = None

    def __str__(self):
        if self.parameter:
            return f"The file {self.parameter} is not found"
        else:
            return "Unexpected parameter type in the config file"


class UnexpectedType(Exception):
    def __init__(self, *args):
        if args:
            self.parameter = args[0]
            try:
                self.position = args[1]
            except IndexError:
                self.position = None
        else:
            self.parameter = None

    def __str__(self):
        if self.parameter:
            _ret_str = f"Unexpected parameter type in {self.parameter}"
            if self.position:
                return _ret_str + ' ' + self.position
            return _ret_str
        else:
            return "Unexpected parameter type in the config file"


class MultipleSectionDefinedError(Exception):

    def __str__(self):
        return f"You cannot activate {Keywords.ALL} and " \
               f"({Keywords.CONTAINERS}/{Keywords.DEFAULT}) section contemporary"


class ElementNotDefined(Exception):
    def __init__(self, *args):
        if args:
            self.parameter = args[0]
        else:
            self.parameter = None

    def __str__(self):
        if self.parameter:
            return f"The parameter {self.parameter} is not defined"


class IncompleteParametersError(Exception):
    def __init__(self, *args):
        if args:
            self.arg1 = args[0]
            self.arg2 = args[1]
            self.position = args[2]
        else:
            self.arg1 = None
            self.arg2 = None
            self.position = None

    def __str__(self):
        _ret_str = f'One of the two parameters "{self.arg1}" or "{self.arg2}" must be defined'
        if self.position:
            return _ret_str + ' ' + self.position
        return _ret_str


class ExcessParametersError(Exception):
    def __init__(self, *args):
        if args:
            self.arg1 = args[0]
            self.arg2 = args[1]
            self.position = args[2]
        else:
            self.arg1 = None
            self.arg2 = None
            self.position = None

    def __str__(self):
        _ret_str = f'Only one of the two parameters "{self.arg1}" or "{self.arg2}" can be defined'
        if self.position:
            return _ret_str + ' ' + self.position
        return _ret_str


class IPRangeOutOfBound(Exception):
    def __init__(self, *args):
        if args:
            self.section = args[0]
        else:
            self.section = None

    def __str__(self):
        if self.section:
            return f'The IP address range given in "{self.section}" doesn\'t match the number ' \
                   f'"{Keywords.CONTAINER_NUMBER}"'
        else:
            return f'The IP address range doesn\'t match the number "{Keywords.CONTAINER_NUMBER}"'


class IPOverlapError(Exception):
    def __init__(self, *args):
        if args:
            self.section1 = args[0]
            self.section2 = args[1]
        else:
            self.section1 = None
            self.section2 = None

    def __str__(self):
        if self.section1:
            return f'Overlap in IP addresses between {self.section1} and {self.section2} sections'


class NumberInconsistency(Exception):

    def __str__(self):
        return f'The number of single containers in "{Keywords.CONTAINERS}" section' \
               f'is greater than the number defined in "{Keywords.CONTAINER_NUMBER}" section'
