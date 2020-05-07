import argparse
import json
import os


MSG_SIZE_LIMIT = 120


# Parse topics distribution passed in a dict string format
class MultipleTopics(object):

    def __init__(self, parser, pub_cnt=0, sub_cnt=0):
        self.parser = parser
        self.args = parser.parse_args()
        try:
            self.sub_counts = getattr(self.args, 'sub_count')
        except AttributeError:
            self.sub_counts = sub_cnt
        try:
            self.pub_counts = getattr(self.args, 'pub_count')
        except AttributeError:
            self.pub_counts = pub_cnt

    def __call__(self, arg):
        self.arg = arg
        # The argument is the file
        # check if the file exists
        topics_dict = {}
        # print("In the call")
        if not os.path.exists(arg):
            raise self.exception()
        with open(arg, 'r') as f:
            try:
                topics_dict = json.load(f)
                # print('The dict')
                # print(topics_dict)
            except json.decoder.JSONDecodeError as err:
                raise self.exception(err)
            self.check_json_format(topics_dict)
        return topics_dict

    def check_json_format(self, json_obj: dict):
        # getting the number of publishers and subscribers
        tot_subs = tot_pubs = 0
        _ind = 0
        try:
            clients = json_obj['clients']
        except KeyError:
            print('The JSON format of the file not recognized')
            exit(1)
        for group in clients:
            _ind = _ind + 1
            try:
                topics = group['topics']
            except KeyError:
                print(f'Error: Something went wrong parsing (row {_ind})')
                exit(1)
            # Initialize the subs and pubs parameter
            try:
                nr_pubs = group['pubs']
            except KeyError:
                nr_pubs = None
            try:
                nr_subs = group['subs']
            except KeyError:
                nr_subs = None
            if nr_subs is None and nr_pubs is None:
                print(f'Parameters missing (row {_ind})')
                exit(1)
            if not isinstance(nr_pubs, int):
                print(f'Error: The pubs parameter in json file must be integer (row {_ind})')
                exit(1)
            if not isinstance(nr_pubs, int):
                print(f'Error: The subs parameter in json file must be integer (row {_ind})')
                exit(1)
            tot_subs = tot_subs + nr_subs
            tot_pubs = tot_pubs + nr_pubs
            for topic in topics:
                if not isinstance(topic, str):
                    print(f'Error: The list items of the topics parameter '
                          f'in the json file must be string type  (row {_ind})')
                    exit(1)

        if tot_subs > self.sub_counts:
            print('Error: The number of subscribers (--sub-count) is smaller than the total number of subscribers '
                  'reported in the --multiple-topic file')
            exit(1)
        if tot_pubs > self.pub_counts:
            print('Error: The number of publisher (--pub-count) is smaller than the total number of publishers '
                  'reported in the --multiple-topic file')
            exit(1)

    def exception(self, err=None):
        if err is not None:
            return argparse.ArgumentTypeError(err.msg)
        if self.arg is not None:
            return argparse.ArgumentError('The JSON file could not be located')


# Custom argparse type representing a bounded int
class IntRange:

    def __init__(self, imin=None, imax=None):
        self.imin = imin
        self.imax = imax

    def __call__(self, arg):
        try:
            value = int(arg)
        except ValueError:
            raise self.exception()
        if (self.imin is not None and value < self.imin) or (self.imax is not None and value > self.imax):
            raise self.exception()
        return value

    def exception(self):
        if self.imin is not None and self.imax is not None:
            return argparse.ArgumentTypeError(f"Must be an integer in the range [{self.imin}, {self.imax}]")
        elif self.imin is not None:
            return argparse.ArgumentTypeError(f"Must be an integer >= {self.imin}")
        elif self.imax is not None:
            return argparse.ArgumentTypeError(f"Must be an integer <= {self.imax}")
        else:
            return argparse.ArgumentTypeError("Must be an integer")


# Custom argparse to validate the message passed
class MessageValidation:

    def __init__(self, lower_limit=None):
        self.lower_limit = lower_limit

    def __call__(self, arg):
        try:
            _arg = str(arg)
        except ValueError:
            raise self.exception()
        if _arg is not None and len(_arg) < MSG_SIZE_LIMIT:
            raise self.exception(_arg)
        return _arg

    def exception(self, arg=None):
        if arg is not None:
            return argparse.ArgumentTypeError(f"The message size must be >= {MSG_SIZE_LIMIT}")
        else:
            return argparse.ArgumentTypeError("Message argument must be a string")