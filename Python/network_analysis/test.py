import argparse
import os
import datetime
import json
import re
import io
import tarfile

pwd = os.getcwd()


def get_args(args:argparse.Namespace) -> str:
    args_str = ''
    for key, value in args.__dict__.items():
        if value is not None:
            args_str = args_str + ' --' + key + ' ' + str(value)
    return args_str


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


# Parse dict
class TopicsType(object):

    def __init__(self, parser):
        self.parser = parser
        self.args = parser.parse_args()

    def __call__(self, arg):
        self.arg = arg
        # The argument is the file
        # check if the file exists
        topics_dict = {}
        if not os.path.exists(arg):
            raise self.exception()
        with open(arg, 'r') as f:
            try:
                topics_dict = json.load(f)
            except json.decoder.JSONDecodeError as err:
                raise self.exception(err)
            self.check_json_format(topics_dict)
        return topics_dict

    def check_json_format(self, json_obj: dict):
        # getting the number of publishers and subscribers
        tot_subs = tot_pubs = 0
        sub_counts = getattr(self.args, 'sub_count')
        pub_counts = getattr(self.args, 'pub_count')
        clients = json_obj['clients']
        for group in clients:
            topics = group['topics']
            nr_pubs = group['pubs']
            nr_subs = group['subs']
            if not isinstance(nr_pubs, int):
                print('Error: The pubs parameter in json file must be integer')
                exit(1)
            if not isinstance(nr_pubs, int):
                print('Error: The subs parameter in json file must be integer')
                exit(1)
            tot_subs = tot_subs + nr_subs
            tot_pubs = tot_pubs + nr_pubs
            for topic in topics:
                if not isinstance(topic, str):
                    print('The list items of the topics parameter in the json file must be string type')
                    exit(1)

        if tot_subs > sub_counts:
            print('Error: The number of subscribers (--sub-count) is smaller than the total number of subscribers '
                  'reported in the --multiple-topic json file')
            exit(1)
        if tot_pubs > pub_counts:
            print('Error: The number of publishers (--pub-count) is smaller than the total number of publishers '
                  'reported in the --multiple-topic json file')
            exit(1)

    def exception(self, err=None):
        if err is not None:
            return argparse.ArgumentTypeError(err.msg)
        if self.arg is not None:
            return argparse.ArgumentError('The JSON file could not be located')


# Parse topics distribution passed in a dict string format
class MultipleTopics(object):

    def __init__(self):
        pass

    def __call__(self, arg):
        topics_dict = {}
        if arg is not None:
            try:
                topics_dict = json.loads(arg)
            except json.decoder.JSONDecodeError as err:
                raise self.exception(err)
            # check the format
        return topics_dict

    def exception(self, err = None):
        if err is not None:
            return argparse.ArgumentTypeError(err.msg)
        else:
            return argparse.ArgumentTypeError("Argument must be a dictionary in a string format")


# def validate_json_format()

def get_item_from_json(json_obj, item, error_msg: str = None, exit_flag: bool = False,
                       default_value=None):
    """ Retrieves an item from the json object
    :param json_obj:
    :param item:
    :param msg_if_error:
    :param exit_flag: Exits from the program if the item is missing
    :param default_value: the auto-fill value to the item in the dict if it is missing
    :return: The item if it is fount
    """
    _item = None
    try:
        _item = json_obj[item]
    except KeyError:
        if default_value is None:
            if error_msg is not None:
                print(error_msg)
            if exit_flag:
                exit(1)
        else:
            _item = json_obj[item] = default_value
    return _item


class Foo(object):    # don't need 'object' in Python 3
    def __init__(self):
        self.__franci = None
    @property
    def franci(self):
        print('Getter')
        return self.__franci

    @franci.setter
    def franci(self, value):
        print('Setter')
        print(self.franci)
        self.__franci = value


class json_module:
    JSON_CLUSTERS = 'clusters'
    JSON_TOPICS = 'topics'
    JSON_SUBS = 'sub_clients'
    JSON_PUBS = 'pub_clients'
    JSON_ALL = 'all'
    JSON_DEFAULT = 'default'
    # Of the containers json file
    JSON_CONTAINER_NUMER = 'number'
    JSON_CONTAINER_CLUSTERS = 'containers'
    JSON_CONTAINER_DEFAULT = JSON_DEFAULT
    JSON_CONTAINER_ALL = 'all'
    JSON_CONTAINER_IP_RANGE = 'ip_range'
    JSON_CONTAINER_IP_RANGE_START = 'start'
    JSON_CONTAINER_IP_RANGE_STOP = 'stop'

def argparse():
    parser = argparse.ArgumentParser()

    parser.add_argument('-H', '--hostname', required=False)  # , default="mqtt.eclipse.org"
    parser.add_argument('-t', '--topic', required=False, default="test")  # default="paho/test/opts"
    parser.add_argument('-q', '--qos', required=False, type=int, default=0)
    parser.add_argument('-c', '--clientid', required=False, default=None)
    parser.add_argument('-u', '--username', required=False, default=None)
    parser.add_argument('-d', '--disable-clean-session', action='store_true',
                        help="disable 'clean session' (sub + msgs not cleared when client disconnects)")
    parser.add_argument('-p', '--password', required=False, default=None)
    parser.add_argument('-P', '--port', required=False, type=int, default=None,
                        help='Defaults to 8883 for TLS or 1883 for non-TLS')
    parser.add_argument('-k', '--keepalive', required=False, type=int, default=60)
    parser.add_argument('-s', '--use-tls', action='store_true')
    parser.add_argument('--insecure', action='store_true')
    parser.add_argument('-F', '--cacerts', required=False, default=None)
    parser.add_argument('--tls-version', required=False, default=None,
                        help='TLS protocol version, can be one of tlsv1.2 tlsv1.1 or tlsv1\n')
    parser.add_argument('-D', '--debug', action='store_true')

    parser.add_argument("--topics", required=False, type=MultipleTopics(),
                        help="JSON configuration string for this operation")

    parser.add_argument('--sub-count', type=int, dest='sub_count', default=1,
                        help='The number of messages each subscriber client '
                             'will wait to receive before completing. The '
                             'default count is 1.')

    parser.add_argument('--pub-count', type=int, dest='pub_count', default=1,
                        help='The number of messages each publisher client '
                             'will publish for completing. The default count '
                             'is 1')

    return parser


if __name__ == '__main__':


    # __json_file = './broker-clients.json'
    # if os.path.exists(__json_file):
    #     print('Path exists')
    #
    #
    # with open(__json_file, 'r') as f:
    #     __topics_dict = json.load(f)
    #     print(__topics_dict)


    json_obj = {
        'names':['AB', 'BS'],
        'values':[12, 1]
    }
    #
    # conf_parse = TopicsType()
    # adsas = conf_parse(json.dumps(json_obj) )
    #
    # print(adsas)

    # args = parser.parse_args()
    # print('Arguments are parsed')
    # args_dict = vars(args)
    # print(args_dict)
    #

    # print(type(args))
    #
    # for cmd_par, env_par in json_obj.items():
    #     print(cmd_par, env_par)
    #
    # container = [1]
    # if container:
    #     print('UEs')
    #
    # cont = container.copy()
    # cont.append(2)
    #
    # print(container)
    # print(cont)
    #
    # file = 'broker-clients.json'
    # print(os.path.abspath(file))
    # print(os.path.exists(os.path.abspath(file)))

    folder = '/home/franci/Documents/Docker_Files/Python/network_analysis/containers/logs'
    tar_file_1 = '06_10_14_50__sub__1_star(0).tar'
    tar_file_2 = '06_13_17_50__star.tar'
    tar_file_result = 'tar_file_result.tar'
    tar_file = 'logs_test.tar'
    _str_to_find = 'logs/'
    final_file = os.path.join(folder, tar_file)

    f1_bytes = b''
    f2_bytes = b''

    with open(os.path.join(folder, tar_file_1), 'rb') as f1:
        f1_bytes = f1.read()
        # print(f1.read().decode('utf-8'))

    with open(os.path.join(folder, tar_file_2), 'rb') as f2:
        f2_bytes = f2.read()
        # print(f2_bytes)

    f_bytes = f2_bytes + f1_bytes
    # print(f_bytes)

    # with open(os.path.join(folder, tar_file_result), 'ab') as result_f:
    #     result_f.write(f_bytes)


    with tarfile.open(fileobj=os.path.join(folder, tar_file_1), mode="r:gz") as t1, \
            tarfile.open(fileobj=os.path.join(folder, tar_file_2), mode="r:gz") as t2, \
            tarfile.open(fileobj=os.path.join(folder, tar_file_result), mode="w:gz") as dest:

        t1_members = [m for m in t1.getmembers()]
        t1_names = t1.getnames()
        print(t1_members)
        print(t1_names)
        t2_members = [m for m in t2.getmembers() if m.name not in t1_names]
        print(t2_members)

        for member in t1_members:
            if member.isdir():
                dest.addfile(member)
            else:
                dest.addfile(member, t1.extractfile(member))

        for member in t2_members:
            if member.isdir():
                dest.addfile(member)
            else:
                dest.addfile(member, t2.extractfile(member))

    # with open(final_file, 'rb') as f:
    #
    #     _file_content = f.read().decode(encoding='utf-8')
    #     _positions = [m.start() for m in re.finditer('logs/', _file_content)]
    #
    #     print(_file_content)
    #     print(_positions)
    #     print(_file_content[_positions[2]:])



    # _json_list_2.extend(['new_test', 'new_test 2'])
    # print('In found')
    # print(_json_list_2)
    # for found in _json_list_2:
    #     print(found)
