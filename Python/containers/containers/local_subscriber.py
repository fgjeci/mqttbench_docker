import tarfile
import docker
import os
import time
import argparse
import json
import datetime
import ipaddress
import netaddr
import copy
import pytz
import subprocess
import multiprocessing

# Local packages
import Exceptions

SUB_PREFIX = "sub_"
IMAGE_NAME = 'francigjeci/mqtt-py:3.8.2'
TOTAL_BROKERS = 5
PATH_MULTIPLE_TOPICS = '/home/multiple-topics.json'
TIMEZONE = pytz.timezone('Europe/Rome')


class Keywords:
    CLUSTERS = 'clusters'
    HOSTNAME = 'hostname'
    TOPICS = 'topic'
    SUBS = 'sub_clients'
    PUBS = 'pub_clients'
    SUBS_COUNT = 'sub_count'
    PUBS_COUNT = 'pub_count'
    ALL = 'all'
    DEFAULT = 'default'
    PORT = 'port'
    QOS = 'qos'
    BROKER = 'broker'
    MULTIPLE_TOPICS = 'multiple_topics'
    SUB_TIMEOUT = 'sub_timeout'
    PUB_TIMEOUT = 'pub_timeout'
    CONTAINERS = 'containers'
    CONTAINER_NUMBER = 'number'
    CONTAINER_IP_RANGE = 'ip_range'
    CONTAINER_IP_RANGE_START = 'start'
    CONTAINER_IP_RANGE_STOP = 'stop'
    CONTAINER_BROKER = 'hostname'
    DESCRIPTION = 'description'
    JSON_CONFIG = 'json_config'


class CommandLineKeywords:
    TOPIC = 'topic'
    HOSTNAME = 'hostname'
    SUBS = 'sub_clients'
    PUBS = 'pub_clients'
    SUBS_COUNT = 'sub_count'
    PUBS_COUNT = 'pub_count'
    PORT = 'port'
    DESCRIPTION = 'description'
    MULTIPLE_TOPICS = 'multiple_topics'
    SUB_TIMEOUT = 'sub_timeout'
    PUB_TIMEOUT = 'pub_timeout'
    QOS = 'qos'
    MESSAGE = 'msg'
    BRIEF = 'brief'
    CACERT = 'cacert'
    USERNAME = 'username'
    PASSWORD = 'password'


class EnvironmentVariablesKeywords:
    HOSTNAME = 'CLIENT_HOSTNAME'
    TOPIC = 'CLIENT_TOPIC'
    PORT = 'CLIENT_PORT'
    SUBS = 'CLIENT_SUBSCRIBERS'
    SUBS_COUNT = 'CLIENT_SUBSCRIBERS_COUNT'
    PUBS = 'CLIENT_PUBLISHERS'
    PUBS_COUNT = 'CLIENT_PUBLISHERS_COUNT'
    SUBS_TIMEOUT = 'CLIENT_SUBSCRIBERS_TIMEOUT'
    PUBS_TIMEOUT = 'CLIENT_PUBLISHERS_TIMEOUT'
    QOS = 'CLIENT_QOS'
    MESSAGE = 'CLIENT_MESSAGE'
    BRIEF = 'CLIENT_BRIEF'
    MULTIPLE_TOPICS = 'CLIENT_MULTIPLE_TOPICS'
    DESCRIPTION = 'DESCRIPTION'
    CAERT = 'CAERT'
    USERNAME = 'CLIENT_USERNAME'
    PASSWORD = 'CLIENT_PASSWORD'


class ContainerClients(object):
    def __init__(self, container_index: int = None, section_type: str = None, config: dict = None, broker: str = None,
                 topics=None, sub_clients: int = 0, sub_count: int = 0, pub_clients: int = 0, pub_count: int = 0,
                 ip_range: dict = None, description: str = None):
        self.__container_index = container_index
        self.__section_type = section_type
        self.__config = config
        if not self.__config:
            self.__broker = broker
            self.__topics = topics
            self.__sub_clients = sub_clients
            self.__sub_count = sub_count
            self.__pub_clients = pub_clients
            self.__pub_count = pub_count
            self.__ip_range = ip_range
            self.__description = description

        elif isinstance(self.__config, dict):
            self.__broker = config.get(Keywords.CONTAINER_BROKER, None)
            self.__topics = config.get(Keywords.TOPICS)
            self.__sub_clients = config.get(Keywords.SUBS, 0)
            self.__sub_count = config.get(Keywords.SUBS_COUNT, 0)
            self.__pub_clients = config.get(Keywords.PUBS, 0)
            self.__pub_count = config.get(Keywords.PUBS_COUNT, 0)
            self.__ip_range = config.get(Keywords.CONTAINER_IP_RANGE, None)
            self.__description = config.get(Keywords.DESCRIPTION, None)
        elif isinstance(self.__config, str):
            if not os.path.exists(self.__config):
                raise Exceptions.ConfigFileNotFoundError(self.__config)
            with open(self.__config, 'r') as f:
                topics_dict = json.load(f)
                self.__broker = get_item_from_json(topics_dict, Keywords.CONTAINER_BROKER, default_value=None)
                self.__topics = get_item_from_json(topics_dict, Keywords.TOPICS)
                self.__sub_clients = get_item_from_json(topics_dict, Keywords.SUBS, default_value=0)
                self.__sub_count = get_item_from_json(topics_dict, Keywords.SUBS_COUNT, default_value=0)
                self.__pub_clients = get_item_from_json(topics_dict, Keywords.PUBS, default_value=0)
                self.__pub_count = get_item_from_json(topics_dict, Keywords.PUBS_COUNT, default_value=0)
                self.__ip_range = get_item_from_json(topics_dict, Keywords.CONTAINER_IP_RANGE, default_value=None)
                self.__description = get_item_from_json(topics_dict, Keywords.DESCRIPTION, default_value=None)

        self.__check_json_format()

    @property
    def container_index(self):
        return self.__container_index

    @property
    def section_type(self):
        return self.__section_type

    @property
    def broker(self):
        return self.__broker

    @property
    def topics(self):
        return self.__topics

    @property
    def sub_clients(self):
        return self.__sub_clients

    @property
    def sub_count(self):
        return self.__sub_count

    @property
    def pub_clients(self):
        return self.__pub_clients

    @property
    def pub_count(self):
        return self.__pub_count

    @property
    def ip_range(self):
        return self.__ip_range

    @property
    def description(self):
        return self.__description

    def __validate_broker(self):
        section_position = get_section_position(container_index=self.container_index, section_type=self.section_type)
        if self.ip_range is None and self.broker is None:
            raise Exceptions.ExcessParametersError(Keywords.CONTAINER_IP_RANGE, Keywords.CONTAINER_BROKER,
                                                   section_position)
        if self.ip_range is not None and self.broker is not None:
            raise Exceptions.IncompleteParametersError(Keywords.CONTAINER_IP_RANGE, Keywords.CONTAINER_BROKER,
                                                       section_position)

        if self.broker:
            validate_type(self.broker, Keywords.CONTAINER_BROKER, str, section_position)
            try:
                ipaddress.IPv4Address(self.broker)
            except ipaddress.AddressValueError as err:
                raise Exceptions.TypeError(Keywords.CONTAINER_BROKER, 'IPv4 Address  "' + str(err) + '"',
                                           section_position)
        if self.ip_range:
            validate_type(self.ip_range, Keywords.CONTAINER_IP_RANGE, dict, section_position)
            _start = self.ip_range.get(Keywords.CONTAINER_IP_RANGE_START, None)
            _stop = self.ip_range.get(Keywords.CONTAINER_IP_RANGE_STOP, None)
            if _start is None:
                raise Exceptions.ElementNotDefined(Keywords.CONTAINER_IP_RANGE_START)
            elif _stop is None:
                raise Exceptions.ElementNotDefined(Keywords.CONTAINER_IP_RANGE_STOP)
            else:
                validate_type(_start, Keywords.CONTAINER_IP_RANGE_START, str, section_position)
                validate_type(_start, Keywords.CONTAINER_IP_RANGE_STOP, str, section_position)
                try:
                    ipaddress.IPv4Address(_start)
                except ipaddress.AddressValueError as err:
                    raise Exceptions.TypeError(Keywords.CONTAINER_IP_RANGE_START, 'IPv4 Address "' + str(err) + '"',
                                               section_position)
                try:
                    ipaddress.IPv4Address(_stop)
                except ipaddress.AddressValueError as err:
                    raise Exceptions.TypeError(Keywords.CONTAINER_IP_RANGE_STOP, 'IPv4 Address  "' + str(err) + '"',
                                               section_position)

    def __check_json_format(self):
        self.__validate_cluster_elements()
        # getting the number of publishers and subscribers
        tot_subs = tot_pubs = 0
        _ind = 0
        if not self.topics:
            raise Exceptions.ElementNotDefined(Keywords.TOPICS)
        else:
            if isinstance(self.topics, str) and self.topics.startswith('.'):
                # print('Topic is a json format')
                # It means a json file has been passed and needs to be parsed
                if not os.path.exists(self.topics):
                    raise Exceptions.ConfigFileNotFoundError(self.topics)
                with open(self.topics, 'r') as f:
                    # read the json structure from the json file and set it to self.topic
                    self.__topics = json.load(f)
                    # recheck format to parse the dict
                    self.__check_json_format()
            if isinstance(self.topics, dict):
                # print('Topics is dict')
                _clusters = get_item_from_json(self.topics, Keywords.CLUSTERS)
                _all = get_item_from_json(self.topics, Keywords.ALL)
                _default = get_item_from_json(self.topics, Keywords.DEFAULT)
                _container_section_pos = get_section_position(container_index=self.container_index,
                                                              section_type=self.section_type)

                if _clusters:
                    validate_type(_clusters, Keywords.CLUSTERS, list, _container_section_pos)
                if _all:
                    validate_type(_all, Keywords.ALL, (str, list), _container_section_pos)
                if _default:
                    validate_type(_default, Keywords.DEFAULT, (str, list), _container_section_pos)

                for group in _clusters:
                    _ind = _ind + 1
                    _topic_section_pos = get_section_position(container_index=self.container_index,
                                                              topic_index=_ind, section_type=self.section_type)
                    topics = get_item_from_json(group, Keywords.TOPICS, exit_flag=True,
                                                error_msg=f'Error: Something went wrong parsing ' + _topic_section_pos)
                    # Initialize the subs and pubs parameter
                    nr_pubs = get_item_from_json(group, Keywords.PUBS, default_value=0)
                    nr_subs = get_item_from_json(group, Keywords.SUBS, default_value=0)
                    validate_sub_pubs(nr_pubs=nr_pubs, nr_subs=nr_subs, container_index=_ind, topic_index=_ind,
                                      section_type=self.section_type)
                    tot_subs = tot_subs + nr_subs
                    tot_pubs = tot_pubs + nr_pubs
                    validate_type(topics, Keywords.TOPICS, (str, list), _topic_section_pos)
                    if isinstance(topics, list):
                        for topic in topics:
                            validate_type(topic, Keywords.TOPICS, str, _topic_section_pos)

                if tot_subs > self.sub_clients:
                    print('Error: The number of subscribers (--sub-clients) is smaller than the total number of '
                          'subscribers reported in the --multiple-topic file')
                    exit(1)
                if tot_pubs > self.pub_clients:
                    print(
                        f'Error: The number of publisher (--pub-client) is smaller than the total number of publishers '
                        f'reported in the --multiple-topic file {tot_pubs} vs {self.pub_clients}')
                    exit(1)

    def __validate_cluster_elements(self):
        validate_sub_pubs(container_index=self.container_index, nr_subs=self.sub_clients, nr_pubs=self.pub_clients)
        validate_count_clients(container_index=self.container_index, nr_clients=self.pub_clients,
                               nr_count_per_client=self.pub_count, section_type=self.section_type)
        validate_count_clients(container_index=self.container_index, nr_clients=self.sub_clients,
                               nr_count_per_client=self.sub_count, section_type=self.section_type)
        self.__validate_broker()

    def section(self):
        _section = {
            Keywords.CONTAINER_BROKER: self.broker,
            Keywords.TOPICS: self.topics,
            Keywords.SUBS: self.sub_clients,
            Keywords.SUBS_COUNT: self.sub_count,
            Keywords.PUBS: self.pub_clients,
            Keywords.PUBS_COUNT: self.pub_count
        }
        return _section


class MultipleContainers:

    def __init__(self, json_file: str):
        self.__json_file = json_file
        self.__number = None
        self.__containers = []
        self.__default = None
        self.__all = None
        self.__topics_dict = {}
        if not os.path.exists(self.__json_file):
            raise Exceptions.ConfigFileNotFoundError(self.__json_file)
        with open(self.__json_file, 'r') as f:
            self.__topics_dict = json.load(f)
        self.__validate_json(self.__topics_dict)

    @property
    def number(self):
        return self.__number

    @property
    def containers(self):
        return self.__containers

    @property
    def default(self):
        return self.__default

    @property
    def all(self):
        return self.__all

    def __validate_json(self, json_obj: dict):

        # error_msg='JSON file is not correctly formatted', exit_flag=True
        _number = get_item_from_json(json_obj, Keywords.CONTAINER_NUMBER)
        _containers = get_item_from_json(json_obj, Keywords.CONTAINERS)
        _all = get_item_from_json(json_obj, Keywords.ALL)
        _default = get_item_from_json(json_obj, Keywords.DEFAULT)
        if not isinstance(_number, int):
            raise Exceptions.TypeError(Keywords.CONTAINER_NUMBER, 'int')
        self.__number = _number
        if _all:
            if _containers is not None or _default is not None:
                raise Exceptions.MultipleSectionDefinedError
            if not _number:
                raise Exceptions.ElementNotDefined(Keywords.CONTAINER_NUMBER)
            self.__all = ContainerClients(config=_all, section_type=Keywords.ALL)
            if self.__all.ip_range:
                _start_ip = ipaddress.IPv4Address(self.__all.ip_range.get(Keywords.CONTAINER_IP_RANGE_START))
                _stop_ip = ipaddress.IPv4Address(self.__all.ip_range.get(Keywords.CONTAINER_IP_RANGE_STOP))
                nr_addresses = int(_stop_ip) - int(_start_ip) + 1
                if nr_addresses != self.number:
                    raise Exceptions.IPRangeOutOfBound(Keywords.ALL)

        else:
            if _containers:
                nr_single_con = len(_containers)
                if _number is not None:
                    if nr_single_con > _number:
                        raise Exceptions.NumberInconsistency
                    if not _default:
                        raise Exceptions.ElementNotDefined(Keywords.DEFAULT)
                for ind, container in enumerate(_containers):
                    _cont = ContainerClients(config=container, container_index=ind,
                                             section_type=Keywords.CONTAINERS)
                    # print(f'Parsing inside container - container{ind}')
                    # print(_cont.section())
                    self.__containers.append(_cont)
            if _default:
                # Checking the default section data
                if not _number:
                    raise Exceptions.ElementNotDefined(Keywords.CONTAINER_NUMBER)
                self.__default = ContainerClients(config=_default, section_type=Keywords.DEFAULT)
                if self.__default.ip_range:
                    _start_ip = ipaddress.IPv4Address(self.__default.ip_range.get(Keywords.CONTAINER_IP_RANGE_START))
                    _stop_ip = ipaddress.IPv4Address(self.__default.ip_range.get(Keywords.CONTAINER_IP_RANGE_STOP))
                    nr_addresses = int(_stop_ip) - int(_start_ip) + 1
                    if nr_addresses != self.number - len(self.containers):
                        raise Exceptions.IPRangeOutOfBound(Keywords.DEFAULT)
                    _ip_range = [str(_ip) for _ip in netaddr.iter_iprange(str(_start_ip), str(_stop_ip), 1)]
                    if any(_cont.broker in _ip_range for _cont in self.containers):
                        raise Exceptions.IPOverlapError(Keywords.CONTAINERS, Keywords.DEFAULT)

    def get_containers(self):
        if hasattr(self.__all, Keywords.CONTAINER_IP_RANGE):
            containers = []
            _start_ip = ipaddress.IPv4Address(self.__all.ip_range.get(Keywords.CONTAINER_IP_RANGE_START))
            _stop_ip = ipaddress.IPv4Address(self.__all.ip_range.get(Keywords.CONTAINER_IP_RANGE_STOP))
            _ip_range = netaddr.iter_iprange(_start_ip, _stop_ip, 1)
            for _broker_ip in _ip_range:
                _single_cont = self.__all.section()
                _single_cont[Keywords.HOSTNAME] = _broker_ip
                containers.append(_single_cont)
            return containers
        elif hasattr(self.__all, Keywords.HOSTNAME):
            return [self.__all.section() for _ in range(self.number)]
        elif hasattr(self.__default, Keywords.CONTAINER_IP_RANGE):
            containers = [_cont.section() for _cont in self.containers]
            _start_ip = self.__default.ip_range.get(Keywords.CONTAINER_IP_RANGE_START)
            _stop_ip = self.__default.ip_range.get(Keywords.CONTAINER_IP_RANGE_STOP)
            _ip_range = [str(_ip) for _ip in netaddr.iter_iprange(_start_ip, _stop_ip, 1)]
            for _broker_ip in _ip_range:
                _single_cont = self.__default.section()
                _single_cont[Keywords.HOSTNAME] = _broker_ip
                containers.append(_single_cont)
                # print(_single_cont)
            return containers
        elif hasattr(self.__default, Keywords.HOSTNAME):
            _sections = []
            for i in range(self.number - len(self.containers)):
                _sections.append(self.__default.section())
            return _sections
        else:
            return [_cont.section() for _cont in self.containers]


def get_item_from_json(json_obj: dict, item: str, error_msg: str = None, exit_flag: bool = False,
                       default_value=None):
    """ Retrieves an item from the json object
    :param json_obj:
    :param item:
    :param error_msg:
    :param exit_flag: Exits from the program if the item is missing
    :param default_value: the auto-fill value to the item in the dict if it is missing
    :return: The item if it is fount
    """
    _item = None
    _item = json_obj.get(item, default_value)
    if _item is None:
        if error_msg is not None:
            print(error_msg)
        if exit_flag:
            exit(1)
    return _item


def validate_type(parameter, parameter_category: str, type_expected, position_str: str = None):
    if type(type_expected) == tuple:
        if not isinstance(parameter, type_expected):
            raise Exceptions.TypeError(parameter_category, [_type.__name__ for _type in type_expected], position_str)
    else:
        if not isinstance(parameter, type_expected):
            raise Exceptions.TypeError(parameter_category, type_expected.__name__, position_str)


def get_section_position(container_index=None, topic_index=None, section_type: str = None):
    _between_round_brackets_comment = ''
    if container_index is None:
        if section_type:
            _between_round_brackets_comment = "(" + section_type + " section"
        else:
            _between_round_brackets_comment = f"(default section"
        if topic_index is not None:
            _between_round_brackets_comment = _between_round_brackets_comment + f', topic {topic_index})'
        else:
            _between_round_brackets_comment = _between_round_brackets_comment + ')'
    else:
        _between_round_brackets_comment = f"(container {container_index}"
        if topic_index is not None:
            _between_round_brackets_comment = _between_round_brackets_comment + f', topic {topic_index})'
        else:
            _between_round_brackets_comment = _between_round_brackets_comment + ')'

    return _between_round_brackets_comment


def validate_sub_pubs(nr_subs: int = 0, nr_pubs: int = 0, container_index=None, topic_index=None,
                      section_type: str = None):
    section_position = get_section_position(container_index=container_index, topic_index=topic_index,
                                            section_type=section_type)
    if nr_subs == 0 and nr_pubs == 0:
        raise Exceptions.IncompleteParametersError(Keywords.SUBS, Keywords.PUBS,
                                                   section_position)
    validate_type(nr_pubs, Keywords.PUBS, int, section_position)
    validate_type(nr_subs, Keywords.SUBS, int, section_position)


def validate_count_clients(nr_clients: int, nr_count_per_client: int, container_index=None, section_type: str = None):
    _between_round_brackets_comment = get_section_position(container_index=container_index, section_type=section_type)
    if nr_clients > 0 and nr_count_per_client == 0:
        print(f"Unexpected parameter: sub/pub-count cannot be 0 whilst sub/pub-clients is defined "
              + _between_round_brackets_comment)
        exit(1)


def get_archive_from_container(container_name, docker_src_file: str):
    container = docker.from_env().containers.get(container_name)
    # Get the content
    # _result = container.exec_run('ls /home/logs')
    # _filename = _result.output.decode('utf-8')
    # print(_filename)
    bits, stat = container.get_archive(os.path.join(docker_src_file))
    return bits, stat


def create_tar_file_destination(destination: str, dst_file_prefix: str = None):
    if not os.path.exists(destination):
        os.mkdir(destination)
    if dst_file_prefix is None:
        dst_file_prefix = 'output'
    index = 0
    _dest = os.path.join(destination, (dst_file_prefix + '.tar'))
    while os.path.exists(_dest):
        index += 1
        _dest = os.path.join(destination, (dst_file_prefix + '(%d).tar' % index))
    return _dest


def collect_containers_logs(containers, docker_src_file: str, destination: str, dst_file_prefix: str = None) -> str:
    file_destination = create_tar_file_destination(destination, dst_file_prefix)
    docker_src_directory_prefix = 'logs'

    # removing all available csv file
    for file_path in os.listdir(os.path.join(os.getcwd(), docker_src_directory_prefix)):
        if file_path.endswith('.csv') and file_path.find('_log_') != -1:
            os.remove(os.path.join(os.getcwd(), docker_src_directory_prefix, file_path))

    final_tar = tarfile.open(file_destination, 'w')
    for ind, container in enumerate(containers):
        file_destination_cont = create_tar_file_destination(destination, dst_file_prefix + '_' + container.name)

        with open(file_destination_cont, 'wb') as f:
            docker_src_file_final = os.path.join(docker_src_file, docker_src_directory_prefix)
            print(f'Get archive {docker_src_file_final} from container {container.name}')
            bits, stat = get_archive_from_container(container.name, docker_src_file_final)
            for chunk in bits:
                f.write(chunk)

        # docker_src_file_final = os.path.join(docker_src_file, docker_src_directory_prefix)
        # print(f'Get archive {docker_src_file_final} from container {container.name}')
        # bits, stat = get_archive_from_container(container.name, docker_src_file_final)
        # for d in bits:
        #     print(d.decode('utf-8'))
        #     pw_tar = tarfile.TarFile(fileobj=io.StringIO(d.decode('utf-8')))
        #     pw_tar.extractall()  # "extract_to/"
        #     pw_tar.close()

        # Extract the csv file in the tar
        tar = tarfile.open(file_destination_cont)
        tar.extractall()
        tar.close()

        # remove the temporary tar file
        os.remove(file_destination_cont)
    # After finishing the extraction, we put then in the final tar
    for file_path in os.listdir(os.path.join(os.getcwd(), docker_src_directory_prefix)):
        if file_path.endswith('.csv') and file_path.find('_log_') != -1:
            _complete_file_path = os.path.join(docker_src_directory_prefix, file_path)
            final_tar.add(_complete_file_path)
            os.remove(_complete_file_path)
    final_tar.close()

    return file_destination


def get_args(args: argparse.Namespace) -> str:
    _args = copy.deepcopy(args)
    args_dict = _args.__dict__
    del args_dict[Keywords.CONTAINERS]
    del args_dict[Keywords.JSON_CONFIG]
    args_str = ''
    for key, value in args_dict.items():
        if value is not None:
            args_str = args_str + ' --' + key.replace('_', '-') + ' ' + str(value)
    return args_str


def list_to_string(_list):
    _str = '' + _list[0]
    if any([not isinstance(elem, str) for elem in _list]):
        raise Exceptions.TypeError('list of topics', 'string')
    for elem in _list[1:]:
        _str = _str + ';' + elem
    return _str


def map_command_parameters_to_environmental() -> dict:
    return {
        Keywords.TOPICS: 'CLIENT_TOPIC',
        Keywords.HOSTNAME: 'CLIENT_HOSTNAME',
        Keywords.PORT: 'CLIENT_PORT',
        Keywords.SUBS: 'CLIENT_SUBSCRIBERS',
        Keywords.SUBS_COUNT: 'CLIENT_SUBSCRIBERS_COUNT',
        Keywords.PUBS: 'CLIENT_PUBLISHERS',
        Keywords.PUBS_COUNT: 'CLIENT_PUBLISHERS_COUNT',
        Keywords.SUB_TIMEOUT: 'CLIENT_SUBSCRIBERS_TIMEOUT',
        Keywords.PUB_TIMEOUT: 'CLIENT_PUBLISHERS_TIMEOUT',
        Keywords.QOS: 'CLIENT_QOS',
        'msg': 'CLIENT_MESSAGE',
        'brief': 'CLIENT_BRIEF',
        'multiple_topics': 'CLIENT_MULTIPLE_TOPICS',
        'description': 'DESCRIPTION'
    }


def create_container(docker_client, args, image: str = IMAGE_NAME, network: str = 'pumba_net', volumes: list = None,
                     working_dir='/home', detach=True, tty=True, stdin_open=True, hostname=None,
                     name=None, **kwargs):
    _env_vars = {}
    _map_keys_cmd_environmental_parameters = map_command_parameters_to_environmental()
    for cmd_par, env_par in _map_keys_cmd_environmental_parameters.items():
        if hasattr(args, cmd_par):
            _env_vars[env_par] = getattr(args, cmd_par)
        else:
            try:
                _env_vars[env_par] = args[cmd_par]
            except KeyError:
                pass
            except TypeError:
                pass
    print(f'Environmental parameters passed to container {name}')
    print(_env_vars)
    return docker_client.containers.run(image,
                                        detach=detach,
                                        entrypoint='python3 script.py',
                                        working_dir=working_dir,
                                        tty=tty,
                                        # terminal driver, necessary since you are running the python in bash
                                        stdin_open=stdin_open,
                                        # stream=True,
                                        volumes=volumes,
                                        environment=_env_vars,
                                        network=network,  # the network this container must be connected
                                        hostname=hostname,
                                        name=name,
                                        **kwargs
                                        )


def create_containers_from_json(json_config, docker_client):
    container_volumes = [os.getcwd() + '/clients/container_python.py:/home/script.py']
    containers = []

    multi_cont = MultipleContainers(json_config)
    container_clients = multi_cont.get_containers()

    print("Creating new containers")
    for _ind, _cont in enumerate(container_clients):
        _topic = _cont.get(Keywords.TOPICS)
        _container_topic = ''
        _container_volumes = container_volumes.copy()
        _args = copy.deepcopy(_cont)
        # print('Containers parameters ')
        # print(_args)
        if isinstance(_topic, dict):
            _destination = os.getcwd() + '/config_files'
            # If topic is dict then we have store it in a json to pass to the container as a json file
            if not os.path.exists(_destination):
                os.mkdir(_destination)
            with open(_destination + '/config' + str(_ind) + '.json', 'w') as json_file:
                json.dump(_topic, json_file)
                _container_topic = _destination + '/config' + str(_ind) + '.json'
        elif isinstance(_topic, (list, tuple)):
            _container_topic = _topic
        elif isinstance(_topic, str):
            _container_topic = _topic
        else:
            raise Exceptions.UnexpectedType(Keywords.TOPICS)
        if isinstance(_container_topic, str) and _container_topic.endswith('.json'):
            if not os.path.exists(_container_topic):
                _container_topic_full_path = os.getcwd() + '/' + _container_topic
                if not os.path.exists(_container_topic_full_path):
                    raise Exceptions.ConfigFileNotFoundError(_container_topic)
            destination_json_file = PATH_MULTIPLE_TOPICS
            _args[Keywords.MULTIPLE_TOPICS] = destination_json_file
            # After having set the --multiple-topics, we have to remove --topic, not to create a crush
            # inside the container
            if Keywords.TOPICS in _args.keys():
                del _args[Keywords.TOPICS]
            _container_volumes.append(os.path.abspath(_container_topic) + ':' + destination_json_file)
        container_name = f"{SUB_PREFIX}_{_ind}"
        _container = create_container(docker_client, _args, volumes=_container_volumes, network='pumba_net',
                                      hostname=container_name, name=container_name)
        print(f"Container {container_name} created")
        containers.append(_container)
    return containers


def kill_containers_with_prefix(docker_client, prefix: str = None) -> None:
    def kill_containers():
        for container in docker_client.containers.list(all=True):
            if prefix is not None:
                if prefix in container.name:
                    container.stop()
                    container.remove()
                    print(f"Container {container.name} killed")
            else:
                container.stop()
                container.remove()
                print(f"Container {container.name} killed")

    print("Killing available containers")
    nr_tries = 0
    for _try in range(0, 2):
        try:
            nr_tries = nr_tries + 1
            kill_containers()
            break
        except:
            print('An error occurred stopping the containers')
            print(f'Retrying ({nr_tries} times)...')
    if nr_tries == 2:
        kill_containers()
    print("All containers are cleared")


def arg_parse(hostname: str = None, port: int = None, topic=None, sub_clients: int = 1, containers: int = 5,
              sub_count: int = 1, qos: int = 0, username: str = None, password: str = None, sub_timeout: int = 60,
              cacert=None, multiple_topics: str = None, description: str = None, json_config: str = None):
    parser = argparse.ArgumentParser()

    parser.add_argument('-H', '--hostname', required=False, default=hostname)
    parser.add_argument('-P', '--port', required=False, type=int, default=port,
                        help='Defaults to 8883 for TLS or 1883 for non-TLS')
    parser.add_argument('-t', '--topic', required=False, default=topic)
    parser.add_argument('--sub-clients', type=int, dest='sub_clients', default=sub_clients,
                        help='The number of subscriber client workers to use. '
                             'By default 1 is used')
    parser.add_argument('--containers', type=int, default=containers,
                        help='The number of containers')
    parser.add_argument('--sub-count', type=int, dest='sub_count', default=sub_count,
                        help='The number of messages each subscriber client '
                             'will wait to receive before completing. The '
                             'default count is 1.')
    parser.add_argument('-q', '--qos', required=False, type=int, default=qos, choices=[0, 1, 2])
    # parser.add_argument('-c', '--clientid', required=False, default=None)
    parser.add_argument('-u', '--username', required=False, default=username)
    # parser.add_argument('-d', '--disable-clean-session', action='store_true',
    #                     help="disable 'clean session' (sub + msgs not cleared when client disconnects)")
    parser.add_argument('-p', '--password', required=False, default=password)
    # parser.add_argument('-k', '--keepalive', required=False, type=int, default=60)
    parser.add_argument('--sub-timeout', type=int, dest='sub_timeout', required=False, default=sub_timeout,
                        help='The amount of time, in seconds, a subscriber '
                             'client will wait for messages. By default this '
                             'is 60.')
    parser.add_argument('-F', '--cacert', required=False, default=cacert)
    parser.add_argument('--multiple-topics', required=False, default=multiple_topics, type=str,
                        help='The structure when clients needs to publish to multiple topics')
    parser.add_argument('--description', type=str, default=description,
                        help='A description of cluster topology. '
                             'Shall be used to set the name of log files of type: '
                             '*description*_*sub_1*')

    parser.add_argument('--json-config', type=str, default=json_config,
                        help='The config json file')

    # parser.add_argument('-s', '--use-tls', action='store_true')
    # parser.add_argument('--insecure', action='store_true')
    # parser.add_argument('--tls-version', required=False, default=None,
    #                     help='TLS protocol version, can be one of tlsv1.2 tlsv1.1 or tlsv1\n')
    # parser.add_argument('-D', '--debug', action='store_true')

    return parser.parse_args()


class Subscribers(multiprocessing.Process):
    def __init__(self, **kwargs):
        super(Subscribers, self).__init__()
        self.__pwd = os.getcwd()
        self.__args = arg_parse(**kwargs)
        self.__docker_client = docker.from_env()
        self.__containers = []
        self.__ready_to_receive_msgs = multiprocessing.Value('i', False, lock=True)



    @property
    def ready_to_receive_msgs(self):
        return self.__ready_to_receive_msgs.value

    def run(self):
        # kill the previous created containers
        kill_containers_with_prefix(self.__docker_client, prefix='sub')

        container_volumes = [self.__pwd + '/clients/container_python.py:/home/script.py']
        json_config = getattr(self.__args, 'json_config')
        # string or list
        if json_config:
            self.__containers = create_containers_from_json(json_config, self.__docker_client)
        else:
            nr_containers = getattr(self.__args, Keywords.CONTAINERS)
            topics_json_file = getattr(self.__args, Keywords.MULTIPLE_TOPICS)
            _args = copy.deepcopy(self.__args)
            if topics_json_file is not None:
                destination_json_file = PATH_MULTIPLE_TOPICS
                _args[Keywords.MULTIPLE_TOPICS] = destination_json_file
                if Keywords.TOPICS in _args.keys():
                    del _args[Keywords.TOPICS]
                container_volumes.append(os.path.abspath(topics_json_file) + ':' + destination_json_file)

            print("Creating new containers")
            for my_cont in range(nr_containers):
                container_name = f"{SUB_PREFIX}_{my_cont}"
                _cont = create_container(self.__docker_client, _args, volumes=container_volumes, name=container_name,
                                         hostname=container_name)
                print(f"Container {container_name} created")
                self.__containers.append(_cont)

        print('Starting containers')
        time.sleep(2)
        for container in self.__containers:
            if container.status == 'created':
                print(f'Container {container.name} started')
                print(f'Running python script in container {container.name}')

        # At this point, once the python scripts are running, subscribers are ready to receive messages
        # self.__ready_to_receive_msgs = True
        self.__ready_to_receive_msgs = multiprocessing.Value('i', True, lock=True)
        # print('Now subs are ready to receive msgs')
        # print(self.ready_to_receive_msgs)

        container_finished = [False] * len(self.__containers)
        print('Analysing printed logs')
        while True:
            for ind, container in enumerate(self.__containers):
                str_to_capture = f'{container.name} finished its operation'
                process = subprocess.Popen(f'docker logs {container.name}', stdout=subprocess.PIPE, stderr=None,
                                           shell=True, encoding="utf8")
                # Launch the shell command:
                output = process.communicate()[0]
                if str_to_capture in output:
                    print(f'Container {container.name} finished its work')
                    container_finished[ind] = True
            print('Status of containers')
            print(container_finished)
            if all(container_finished):
                print('All containers have finished their work')
                break
            time.sleep(2)

        print('Collecting the results from containers')
        _date = datetime.datetime.now(tz=TIMEZONE).strftime('%m_%d_%H_%M') + '_'
        _log_tar_file = collect_containers_logs(self.__containers, docker_src_file='/home/',
                                                destination=self.__pwd + '/logs', dst_file_prefix=_date + '_' + 'star')

        print('Printing containers log')
        for container in self.__containers:
            _cont_output = container.logs()
            print(_cont_output.decode("utf-8"))

        print('Printing containers stats')
        for container in self.__containers:
            print(container.stats(stream=False))

        print('Stopping and killing the containers')
        kill_containers_with_prefix(self.__docker_client, SUB_PREFIX)

        # final_tar = tarfile.open(_log_tar_file, 'a')
        # _extra_file = os.path.join(os.getcwd(), 'local_publisher.py')
        # print(_extra_file)
        # final_tar.add('local_publisher.py')
        # final_tar.close()


if __name__ == '__main__':
    subs = Subscribers()
    subs.start()