# Copyright 2017 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License

import argparse
import datetime
import multiprocessing
import random
import string
import time
import os
import json
import copy
import queue
import numpy
import paho.mqtt.client as mqtt
from threading import Timer
import re

SUB_QUEUE = multiprocessing.Queue()
PUB_QUEUE = multiprocessing.Queue()
LOG_QUEUE = multiprocessing.Queue()


class ContainerTimeoutError(Exception):
    def __init__(self, *args):
        if args:
            self.client = args[0]
        else:
            self.client = None

    def __str__(self):
        if self.client:
            return f'{self.client} clients timeout occured'
        else:
            return 'Container timeout occured'


class ContainerUnexpectedTypeError(Exception):
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


class ContainerFileNotFoundError(Exception):
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


class ContainerShortMessageError(Exception):
    def __init__(self, *args):
        if args:
            self.msg_size = args[0]
        else:
            self.msg_size = None

    def __str__(self):
        if self.msg_size:
            return f"Message size should be at least {self.msg_size} characters"
        else:
            return "Message size is too small"


class ContainersQueueError(Exception):
    def __str__(self):
        err_str = 'Something went horribly wrong, there are less results than sub threads' + '\n'
        err_str = err_str + 'Please check the broker you intend to connect to is running, ' \
                            'or that you haven\'t reached the timeout '
        return err_str


class Keywords:
    CLUSTERS = 'clusters'
    TOPICS = 'topic'
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
    CONTAINER_BROKER = 'hostname'
    DESCRIPTION = 'description'


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
    CONTAINER_HOST = 'HOSTNAME'


class ClientParameters:
    def __init__(self, cmd_par, host: str = None):
        self.__topic = getattr(cmd_par, CommandLineKeywords.TOPIC) or \
                       os.getenv(EnvironmentVariablesKeywords.TOPIC) or None
        self.__hostname = getattr(cmd_par, CommandLineKeywords.HOSTNAME) or \
                          os.getenv(EnvironmentVariablesKeywords.HOSTNAME) or host
        self.__port = set_value(getattr(cmd_par, CommandLineKeywords.PORT),
                                os.getenv(EnvironmentVariablesKeywords.PORT), 1883, 'port')
        self.__sub_clients = set_value(getattr(cmd_par, CommandLineKeywords.SUBS),
                                       os.getenv(EnvironmentVariablesKeywords.SUBS), 0, 'number of subscribers')
        self.__sub_count = set_value(getattr(cmd_par, CommandLineKeywords.SUBS_COUNT),
                                     os.getenv(EnvironmentVariablesKeywords.SUBS_COUNT), 0,
                                     'number of messages per subscriber')
        self.__pub_clients = set_value(getattr(cmd_par, CommandLineKeywords.PUBS),
                                       os.getenv(EnvironmentVariablesKeywords.PUBS), 0, 'number of publishers')
        self.__pub_count = set_value(getattr(cmd_par, CommandLineKeywords.PUBS_COUNT),
                                     os.getenv(EnvironmentVariablesKeywords.PUBS_COUNT), 0,
                                     'number of messages per publisher')
        self.__sub_timeout = set_value(getattr(cmd_par, CommandLineKeywords.SUB_TIMEOUT),
                                       os.getenv(EnvironmentVariablesKeywords.SUBS_TIMEOUT), 60, 'subscriber timeout')
        self.__pub_timeout = set_value(getattr(cmd_par, CommandLineKeywords.PUB_TIMEOUT),
                                       os.getenv(EnvironmentVariablesKeywords.PUBS_TIMEOUT), 60, 'publisher timeout')
        self.__qos = set_value(getattr(cmd_par, CommandLineKeywords.QOS),
                               os.getenv(EnvironmentVariablesKeywords.QOS), 0, 'qos')
        self.__msg = getattr(cmd_par, CommandLineKeywords.MESSAGE) or \
                     os.getenv(EnvironmentVariablesKeywords.MESSAGE)
        self.__brief = getattr(cmd_par, CommandLineKeywords.BRIEF) or \
                       os.getenv(EnvironmentVariablesKeywords.BRIEF) or False
        self.__multiple_topics = getattr(cmd_par, CommandLineKeywords.MULTIPLE_TOPICS) or \
                                 os.getenv(EnvironmentVariablesKeywords.MULTIPLE_TOPICS) or None
        self.__description = getattr(cmd_par, CommandLineKeywords.DESCRIPTION) or \
                             os.getenv(EnvironmentVariablesKeywords.DESCRIPTION) or ''
        self.__cacert = getattr(cmd_par, CommandLineKeywords.CACERT) or os.getenv(EnvironmentVariablesKeywords.CAERT)
        self.__username = getattr(cmd_par, CommandLineKeywords.USERNAME) or \
                          os.getenv(EnvironmentVariablesKeywords.USERNAME) or None
        self.__password = getattr(cmd_par, CommandLineKeywords.PASSWORD) or \
                          os.getenv(EnvironmentVariablesKeywords.PASSWORD) or None
        self.__auth = None
        self.__tls = None

    @property
    def topic(self):
        return self.__topic

    @property
    def hostname(self):
        return self.__hostname

    @property
    def port(self):
        return self.__port

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
    def sub_timeout(self):
        return self.__sub_timeout

    @property
    def pub_timeout(self):
        return self.__pub_timeout

    @property
    def qos(self):
        return self.__qos

    @property
    def msg(self):
        return self.__msg

    @property
    def brief(self):
        return self.__brief

    @property
    def multiple_topics(self):
        return self.__multiple_topics

    @property
    def description(self):
        return self.__description

    @property
    def cacert(self):
        return self.__cacert

    @property
    def username(self):
        return self.__username

    @property
    def password(self):
        return self.__password

    @property
    def auth(self):
        return self.__auth

    @property
    def tls(self):
        return self.__tls

    def validate_parameters(self):
        if self.__topic is None and self.__multiple_topics is None:
            raise Exception('The parameters --topic and --multiple-topics can not be both None type')
        elif self.__topic is not None and self.__multiple_topics is not None:
            raise Exception('You cannot define both parameters --topic and --multiple-topics')
        if not isinstance(self.__topic, str) and self.__multiple_topics is None:
            raise Exception('The topic parameter must be string type')
        if not isinstance(self.__hostname, str):
            raise Exception('The hostname parameter must be string type')
        if not isinstance(self.__brief, bool):
            raise Exception('The brief parameter must be boolean type')

        # Check if parameters are positive, otherwise raise an error
        is_positive(self.__sub_clients, 'number of subscribers')
        is_positive(self.__pub_clients, 'number of publishers')
        is_positive(self.__sub_count, 'number of messages per subscriber')
        is_positive(self.__pub_count, 'number of messages per publisher')

        if isinstance(self.__qos, int):
            if self.__qos not in [0, 1, 2]:
                raise Exception('The QOS value is expected to be 0, 1 or 2')
        else:
            raise Exception('The QOS parameter must be int type ')

        if self.__cacert:
            self.__tls = {'ca_certs': self.__cacert}

        if self.__username is not None and self.__password is not None:
            self.__auth = {'username': self.__username,
                           'password': self.__password}


# Parse topics distribution passed in a dict string format
class MultipleTopics(object):

    def __init__(self, args, json_file, pub_cnt=0, sub_cnt=0):
        self.__args = copy.deepcopy(args)
        try:
            self.__sub_clients = int(getattr(self.__args, Keywords.SUBS) or
                                     os.getenv(EnvironmentVariablesKeywords.SUBS))
        except TypeError:
            self.__sub_clients = sub_cnt
        try:
            self.__pub_clients = int(getattr(self.__args, Keywords.PUBS) or
                                     os.getenv(EnvironmentVariablesKeywords.PUBS))
        except TypeError:
            self.__pub_clients = pub_cnt
        self.__publishers = 0
        self.__subscribers = 0
        self.__json_file = json_file
        # check if the file exists
        self.__topics_dict = {}
        # print("In the call")
        if not os.path.exists(self.__json_file):
            # print('The arguments: %s' % arg)
            raise self.exception()
        with open(self.__json_file, 'r') as f:
            try:
                self.__topics_dict = json.load(f)
            except json.decoder.JSONDecodeError as err:
                raise self.exception(err)
            self.check_json_format(self.__topics_dict)

    @property
    def topics_dict(self):
        return self.__topics_dict

    @property
    def publishers(self):
        return self.__publishers

    @property
    def subscribers(self):
        return self.__subscribers

    def check_json_format(self, json_obj: dict):
        _ind = 0
        clients = get_item_from_json(json_obj, Keywords.CLUSTERS, exit_flag=True,
                                     error_msg='The JSON format of the file not recognized')
        for group in clients:
            _ind = _ind + 1
            topics = get_item_from_json(group, Keywords.TOPICS, exit_flag=True,
                                        error_msg=f'Error: Something went wrong parsing (row {_ind})')
            # Initialize the subs and pubs parameter
            nr_pubs = get_item_from_json(group, Keywords.PUBS, default_value=0)
            nr_subs = get_item_from_json(group, Keywords.SUBS, default_value=0)

            if nr_subs == 0 and nr_pubs == 0:
                print(f'Parameters missing or not set correctly (row {_ind})')
                exit(1)
            if not isinstance(nr_pubs, int):
                print(f'Error: The pubs parameter in json file must be integer type (row {_ind})')
                exit(1)
            if not isinstance(nr_pubs, int):
                print(f'Error: The subs parameter in json file must be integer type (row {_ind})')
                exit(1)
            self.__subscribers += nr_subs
            self.__publishers += nr_pubs
            if isinstance(topics, (list, tuple)):
                for topic in topics:
                    if not isinstance(topic, str):
                        raise ContainerUnexpectedTypeError(Keywords.TOPICS, f'(row {_ind})')
            else:
                if not isinstance(topics, str):
                    raise ContainerUnexpectedTypeError(Keywords.TOPICS)

        if self.__subscribers > self.__sub_clients:
            print(f'Error: The number of subscribers (--sub-clients {self.__sub_clients})  is smaller '
                  f'than the total number of subscribers reported in the (--multiple-topic {self.__subscribers})')
            exit(1)
        if self.__publishers > self.__pub_clients:
            print(f'The publishers')
            print(self.__publishers)
            print(f'Error: The number of publisher (--pub-clients) ({self.__pub_clients}) '
                  f'is smaller than the total number of publishers ({self.__publishers}) '
                  f'reported in the --multiple-topic file')
            exit(1)

    def exception(self, err=None):
        if err is not None:
            return argparse.ArgumentTypeError(err.msg)
        if self.__args is not None:
            raise ContainerFileNotFoundError(self.__json_file)
            # return argparse.ArgumentError('The JSON file could not be located')


class MQTTClient(multiprocessing.Process):
    def __init__(self, host, topic, port: int = 1883, client_id: str = None, tls=None, auth=None,
                 timeout: int = 60, max_count: int = 10, qos: int = 0):
        super(MQTTClient, self).__init__()
        self.__hostname = host
        self.__port = port
        self.__client_id = client_id
        self.__tls = tls
        self.__topic = topic  # Single topic or a list of topics
        self.__auth = auth
        self.__msg_count = 0
        self.__start_time = None
        self.__max_count = max_count
        self.__end_time = None
        self.__timeout = timeout
        self.__qos = qos
        self.__client = mqtt.Client()

    @property
    def hostname(self):
        return self.__hostname

    @property
    def port(self):
        return self.__port

    @property
    def client_id(self):
        return self.__client_id

    @property
    def tls(self):
        return self.__tls

    @property
    def topic(self):
        return self.__topic

    @property
    def auth(self):
        return self.__auth

    @property
    def msg_count(self):
        return self.__msg_count

    @property
    def max_count(self):
        return self.__max_count

    @property
    def start_time(self):
        return self.__start_time

    @property
    def end_time(self):
        return self.__end_time

    @property
    def timeout(self):
        return self.__timeout

    @property
    def qos(self):
        return self.__qos

    @property
    def client(self):
        return self.__client

    @topic.setter
    def topic(self, value):
        self.__topic = value

    @msg_count.setter
    def msg_count(self, value):
        self.__msg_count = value

    @start_time.setter
    def start_time(self, value):
        self.__start_time = value

    @end_time.setter
    def end_time(self, value):
        self.__end_time = value

    def run(self) -> None: ...


class Sub(MQTTClient):
    def __init__(self, *args, intermsg_timeout: int = 120, **kwargs):
        MQTTClient.__init__(self, *args, **kwargs)
        self.__end_time_lock = multiprocessing.Lock()
        self.__finished = False
        self.__intermsg_timeout = intermsg_timeout
        self.__intermsg_timer = Timer(self.__intermsg_timeout * 2, self._intermessage_timeout)
        self.__intermsg_timer.start()
        self.__received_msgs = 0
        # print(f'The topics in ({self.hostname}, {self.client_id})')
        # check if topic has been given as a strig, which in json is passed in a string format
        # print(f'Topic: {self.topic}')
        if isinstance(self.topic, str):
            topic_list = self._json_str_to_list(self.topic)
            if len(topic_list) > 0:
                self.topic = topic_list

    @property
    def finished(self):
        return self.__finished

    @staticmethod
    def _json_str_to_list(json_str):
        _json_list_1 = re.findall(r"'(.*?)'", json_str)
        _json_list_2 = re.findall(r'"(.*?)"', json_str)
        if isinstance(_json_list_1, str):
            _json_list_1 = [_json_list_1]
        if isinstance(_json_list_2, str):
            _json_list_2 = [_json_list_2]
        if _json_list_1:
            if _json_list_2:
                _json_list_1.extend([_json_list_2])
        else:
            _json_list_1 = _json_list_2
        return _json_list_1

    def _intermessage_timeout(self):
        # print('Timeout expired; Stopping the client')
        self.__finished = True
        # self.terminate()
        # self.client.loop_stop()

        print('Timeout: Stopping the client')
        self.client.loop_stop()
        try:
            self.terminate()
            print('Timeout: Terminating process')
        except AttributeError:
            pass


    def on_connect(self, client, userdata, flags, rc):
        # Added the condition to connect to passed topic
        if rc == 0:
            print(f'Client {self.client_id} connected to {self.hostname}')
            print(f'Client {self.client_id} subscribing to topics: {self.topic}')
            if isinstance(self.topic, str):
                # Single topic
                client.subscribe(self.topic, qos=self.qos)
            elif isinstance(self.topic, (list, tuple)):
                # Multiple topics
                for _topic in set(self.topic):
                    client.subscribe(_topic, qos=self.qos)

    def on_subscribe(self, client, obj, mid, granted_qos):
        print(f'Client {self.client_id} subscribed to {self.hostname} with granted qos: {granted_qos}')
        # print("Subscribed: " + str(mid) + " " + str(granted_qos))

    def on_message(self, client, userdata, msg):
        self.__intermsg_timer.cancel()
        self.__intermsg_timer = Timer(self.__intermsg_timeout, self._intermessage_timeout)
        self.__intermsg_timer.start()

        if self.start_time is None:
            self.start_time = datetime.datetime.utcnow()
        _msg_arrival_time = datetime.datetime.utcnow()
        # Parse the msg
        _pub_msg_dictt = parse_msg(msg)
        if isinstance(_pub_msg_dictt['publish_timestamp'], datetime.datetime):
            _pub_msg_host = _pub_msg_dictt['hostname']
            _pub_msg_pub_id = _pub_msg_dictt['pub_id']
            self.__received_msgs += 1
            print(f'New message: Receiver ({self.hostname}, {self.client_id}) & '
                  f'Sender ({_pub_msg_host}, {_pub_msg_pub_id}) & '
                  f'Total received: {self.__received_msgs}')

            # print('The dict parsing works')
            _msg_e2e_delay = _msg_arrival_time - _pub_msg_dictt['publish_timestamp']
            # Write the result
            write_to_log(pub_host=_pub_msg_dictt['hostname'], pub_id=_pub_msg_dictt['pub_id'],
                         pub_con_init=_pub_msg_dictt['pub_con_init'],
                         pub_con_accomplish=_pub_msg_dictt['pub_con_accomplish'],
                         pub_timestamp=_pub_msg_dictt['publish_timestamp'], pub_qos=_pub_msg_dictt['pub_qos'],
                         sub_host=self.hostname, sub_id=self.client_id, sub_timestamp=_msg_arrival_time,
                         e2e_delay=_msg_e2e_delay)

        self.msg_count += 1
        if self.msg_count >= self.max_count:
            # print('We hve entered in the final part ')
            self.__end_time_lock.acquire()
            if self.end_time is None:
                self.end_time = datetime.datetime.utcnow()
            self.__end_time_lock.release()
            # after we have reached the max count we stop the loop to continue further
            self.__finished = True

            print(f'Stopping client {self.client_id} on message')
            self.client.loop_stop()
            # print(f'Terminating process on message in client {self.client_id} ')
            # self.terminate()


    def run(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        if self.tls:
            self.client.tls_set(**self.tls)
        if self.auth:
            self.client.username_pw_set(**self.auth)
        self.client.connect(self.hostname, port=self.port)
        self.client.loop_start()
        while True:
            # Time sleep is no useful when we have messages coming in bursts
            time.sleep(1)
            self.__end_time_lock.acquire()
            if self.end_time:
                delta = self.end_time - self.start_time
                SUB_QUEUE.put(delta.total_seconds())
                self.client.loop_stop()
                break
            self.__end_time_lock.release()
            if self.start_time:
                current_time = datetime.datetime.utcnow()
                curr_delta = current_time - self.start_time
                if curr_delta.total_seconds() > self.timeout:
                    raise Exception('We hit the sub timeout!')


class Pub(MQTTClient):
    def __init__(self, *args, msg_size: int = 1024, **kwargs):
        MQTTClient.__init__(self, *args, **kwargs)
        self.msg_size = msg_size
        self.msg = None
        self.connect_init = None
        self.connect_accomplish = None
        if self.msg_size < 51:
            raise ContainerShortMessageError(50)

    def create_msg(self):

        if self.connect_init is None:
            self.connect_init = ''
        if self.connect_accomplish is None:
            self.connect_accomplish = ''
        _pre_msg = self.hostname + '_' + self.client_id + '_' + str(self.connect_init) + '_' \
                   + str(self.connect_accomplish) + '_' + str(datetime.datetime.utcnow()) + '_' \
                   + str(self.qos) + '_'
        return _pre_msg + ''.join(
            random.choice(string.ascii_lowercase) for _ in range(self.msg_size - len(_pre_msg.encode('utf-8'))))

    def on_publish(self, client, userdata, mid):
        # print('The message was published')
        # Used for qos 1 and 2
        # For QoS 0, this simply means that the message has left the client
        # For other qoses, this means the handshake process has successfully ended
        pass

    def publish_msg(self, client, topic):
        self.msg = self.create_msg()
        client.publish(topic, payload=self.msg, qos=self.qos)
        if self.start_time:
            current_time = datetime.datetime.utcnow()
            curr_delta = current_time - self.start_time
            if curr_delta.total_seconds() > self.timeout:
                raise Exception('We hit the pub timeout!')

    def on_connect(self, client, obj, flags, rc):
        print('Pub successfully connected')
        # print(mqtt.connack_string(rc))
        _single_topic = True if isinstance(self.topic, str) else False
        _nr_topics_to_publish = 1 if _single_topic else len(self.topic)
        self.start_time = datetime.datetime.utcnow()
        if rc == 0:
            self.connect_accomplish = self.start_time
            # print('The loop started')
            for i in range(0, self.max_count, _nr_topics_to_publish):
                if _single_topic:
                    self.publish_msg(client, self.topic)
                else:
                    # we have to publish for each topic in the list
                    _items_to_print = _nr_topics_to_publish if self.max_count - i > _nr_topics_to_publish \
                        else self.max_count - i
                    for _topic in self.topic[:_items_to_print]:
                        self.publish_msg(client, _topic)

            self.end_time = datetime.datetime.utcnow()
            delta = self.end_time - self.start_time
            PUB_QUEUE.put(delta.total_seconds())

    def run(self):

        if self.tls:
            self.client.tls_set(**self.tls)
        if self.auth:
            self.client.username_pw_set(**self.auth)

        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish

        # print('The client object was successfully created')
        self.connect_init = datetime.datetime.utcnow()
        self.client.connect(self.hostname, port=self.port)
        self.client.loop_start()

        # Keep running until we have set the end_time parameter, which happen after everything is finished
        while True:
            time.sleep(1)
            if self.end_time:
                self.client.loop_stop()
                break


def get_item_from_json(json_obj, item, error_msg: str = None, exit_flag: bool = False,
                       default_value=None):
    """Retrieves an item from the json object
    :param error_msg:
    :param json_obj:
    :param item:
    :param exit_flag: Exits from the program if the item is missing
    :param default_value: the auto-fill value to the item in the dict if it is missing
    :return: The item if it is found
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


def set_value(cmd_par, env_par, default: int, par_name: str) -> int:
    """Choose among the different option of passing the parameter and then validate
    :param cmd_par:  Parameter passed through command line in python script
    :param env_par: Parameter passed as environment parameter
    :param default: The default value
    :param par_name: Parameter name
    :return: The parsed parameter value
    """

    if cmd_par is None and env_par is None:
        return default
    else:
        if isinstance(env_par, str):
            try:
                env_par = int(env_par)
            except ValueError:
                raise Exception('The %s parameter must be of type integer' % par_name)
        if isinstance(cmd_par, str):
            try:
                cmd_par = int(cmd_par)
            except ValueError:
                raise Exception('The %s parameter must be of type integer' % par_name)
        if isinstance(env_par, int) or isinstance(cmd_par, int):
            if cmd_par is not None:
                return cmd_par
            else:
                return env_par
        else:
            raise Exception('Unexpected parameter type')


def is_positive(param: int, param_name: str):
    """Validate parameter to be positive"""
    if param < 0:
        raise Exception('The %s must be positive' % param_name)


def initialize_log(host: str, dest_path: str = 'logs', file_name: str = None, prefix: str = ''):
    """Initializes the csv file which will contain the received messages"""
    octets = host.split('.')
    if len(octets) != 4:
        raise Exception('Hostname passed is invalid')
    if file_name is None:
        file_name = prefix + '_log_' + octets[3] + '.csv'
    # dest_path = dest_path + '_' + os.getenv('HOSTNAME')
    output_path = os.path.join(dest_path, file_name)
    # Check if directory and file, else create it
    if not os.path.exists(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Writing the file header
    with open(output_path, 'w') as f:
        f.write('hostname_origin;pub_client_id;publish_connect_init;')
        f.write('publish_connect_ack;publish_timestamp;publish_qos;')
        f.write('hostname_destination;sub_client;arrival_timestamp;e2e_delay')
        f.write('\n')
        f.close()
    return output_path


def write(log, data):
    print(f'The size of the logs {len(data)}')
    with open(log, 'a') as f:
        for ind, chunk in enumerate(data):
            print(f'Writing the {ind}-th row')
            f.write(chunk)
            f.write('\n')
        f.close()


def parse_msg(msg):
    """Parse the received message at the subscriber"""
    # print('Parsing the arrived message')
    if isinstance(msg, mqtt.MQTTMessage):
        # String format of the arrived message
        msg = msg.payload.decode("utf-8")
    fields = msg.split("_", 6)
    _dict = {
        'hostname': fields[0],
        'pub_id': fields[1],
        'pub_con_init': datetime.datetime.strptime(fields[2], '%Y-%m-%d %H:%M:%S.%f'),
        'pub_con_accomplish': datetime.datetime.strptime(fields[3], '%Y-%m-%d %H:%M:%S.%f'),
        'publish_timestamp': datetime.datetime.strptime(fields[4], '%Y-%m-%d %H:%M:%S.%f'),
        'pub_qos': fields[5]
    }
    return _dict


def write_to_log(pub_host: str = None, pub_id: str = None, pub_con_init: datetime.datetime = None,
                 pub_con_accomplish: datetime.datetime = None, pub_timestamp: datetime.datetime = None,
                 pub_qos: str = None, sub_host: str = None, sub_id: str = None,
                 sub_timestamp: datetime.datetime = None, e2e_delay: datetime.timedelta = None):
    """Writing the line to the log queue"""
    # print('Writing the message to log')
    log_format = '%s' + ';%s' * 9
    LOG_QUEUE.put(log_format % (pub_host, pub_id, pub_con_init, pub_con_accomplish,
                                pub_timestamp, pub_qos,
                                sub_host, sub_id, sub_timestamp,
                                e2e_delay))
    if LOG_QUEUE.full():
        print('The log queue is full')
    print(f'Logs size {LOG_QUEUE.qsize()}')


def arg_parse():
    """Parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostname', required=((os.getenv('CLIENT_HOSTNAME') is None) and (hostname is None)),
                        help='The hostname (or ip address) of the broker to '
                             'connect to')
    parser.add_argument('--port', type=int, default=1883,
                        help='The port to use for connecting to the broker. '
                             'The default port is 1883.')
    parser.add_argument('--pub-clients', type=int, dest='pub_clients',
                        help='The number of publisher client workers to use. '
                             'By default 0 are used.')
    parser.add_argument('--sub-clients', type=int, dest='sub_clients',
                        help='The number of subscriber client workers to use. '
                             'By default 0 are used')
    parser.add_argument('--pub-count', type=int, dest='pub_count',
                        help='The number of messages each publisher client '
                             'will publish for completing. The default count '
                             'is 0')
    parser.add_argument('--sub-count', type=int, dest='sub_count',
                        help='The number of messages each subscriber client '
                             'will wait to recieve before completing. The '
                             'default count is 0.')
    parser.add_argument('--msg-size', type=int, dest='msg_size',
                        help='The payload size to use in bytes')
    # Added
    parser.add_argument('--msg', type=str, dest='msg',
                        help='The payload of the publish message')
    parser.add_argument('--sub-timeout', type=int, dest='sub_timeout',
                        help='The amount of time, in seconds, a subscriber '
                             'client will wait for messages. By default this '
                             'is 60.')
    parser.add_argument('--pub-timeout', type=int, dest='pub_timeout',
                        help="The amount of time, in seconds, a publisher "
                             "client will wait to successfully publish it's "
                             "messages. By default this is 60")
    parser.add_argument('--topic', type=str, default=None,
                        help='The MQTT topic to use for the benchmark. The '
                             'default topic is pybench')
    parser.add_argument('--multiple-topics', required=False, type=str, default=None,
                        help='The structure when clients needs to publish to multiple topics')
    parser.add_argument('--cacert',
                        help='The certificate authority certificate file that '
                             'are treated as trusted by the clients')
    parser.add_argument('--username',
                        help='An optional username to use for auth on the '
                             'broker')
    parser.add_argument('--password',
                        help='An optional password to use for auth on the '
                             'broker. This requires a username is also set')
    parser.add_argument('--brief', action='store_true',
                        help='Print results in a colon separated list instead'
                             ' of a human readable format. See the README for '
                             'the order of results in this format')
    parser.add_argument('--qos', type=int, default=0, choices=[0, 1, 2],
                        help='The qos level to use for the benchmark')
    parser.add_argument('--description', type=str, default=None,
                        help='A description of cluster topology. '
                             'Shall be used to set the name of log files of type: '
                             '*description*_*sub_1*')

    return parser.parse_args()


def main(host=None):
    parser = arg_parse()
    opts = parser

    sub_threads = []
    pub_threads = []

    cl_param = ClientParameters(opts, host)

    # Log file
    log_file = initialize_log(cl_param.hostname, dest_path='/home/logs'
                              , prefix=cl_param.description)

    # start = time.time()

    # the multiple-topics
    _multiple_topics_cl = None
    _multiple_topics_dict = None
    if cl_param.multiple_topics is not None:
        _multiple_topics_cl = MultipleTopics(parser, cl_param.multiple_topics)
        _multiple_topics_dict = _multiple_topics_cl.topics_dict

    if cl_param.topic is not None:
        # print('Single topics')
        # ALL Subscribers and publishers shall work on one single topic
        for i in range(cl_param.sub_clients):
            # set the timeout depending on the number of subs
            _timeout = cl_param.sub_timeout
            if cl_param.sub_clients > cl_param.sub_timeout:
                _timeout = cl_param.sub_clients * 3.5
            sub = Sub(cl_param.hostname, topic=cl_param.topic, port=cl_param.port, client_id='sub' + str(i),
                      tls=cl_param.tls, auth=cl_param.auth, timeout=_timeout,
                      max_count=cl_param.sub_count, qos=cl_param.qos)
            sub_threads.append(sub)
            sub.start()

        for i in range(cl_param.pub_clients):
            pub = Pub(cl_param.hostname, topic=cl_param.topic, port=cl_param.port, client_id='pub' + str(i),
                      tls=cl_param.tls, auth=cl_param.auth, timeout=cl_param.pub_timeout,
                      max_count=cl_param.pub_count, qos=cl_param.qos)
            pub_threads.append(pub)
            pub.start()

    if _multiple_topics_dict is not None:
        # print('Multiple topics')
        _clusters = _multiple_topics_dict[Keywords.CLUSTERS]
        _all = get_item_from_json(_multiple_topics_dict, Keywords.ALL)
        if isinstance(_all, str):
            _all = [_all]
        _default_topic = get_item_from_json(_multiple_topics_dict, Keywords.DEFAULT)
        if isinstance(_default_topic, str):
            _default_topic = [_default_topic]
        # print(f'Subscribing {_nr_subs} clients to {_topic}:')
        _sub_client_id = 0
        _pub_client_id = 0
        # the predefined clusters
        for _cluster in _clusters:
            _topics = list(_cluster[Keywords.TOPICS])
            if _all is not None:
                if isinstance(_all, list):
                    # List of topics
                    _topics.append(*_all)
                else:
                    # Single topic
                    _topics.append(_all)
            _nr_subs = _cluster[Keywords.SUBS]
            for _sub_ind in range(_nr_subs):
                _sub_client_id += 1
                # set the timeout depending on the number of subs
                _timeout = cl_param.sub_timeout
                if cl_param.sub_clients > cl_param.sub_timeout:
                    _timeout = cl_param.sub_clients * 3.5
                sub = Sub(cl_param.hostname, topic=_topics, port=cl_param.port,
                          client_id='sub' + str(_sub_client_id), tls=cl_param.tls,
                          auth=cl_param.auth, timeout=_timeout,
                          max_count=cl_param.sub_count, qos=cl_param.qos)
                sub_threads.append(sub)
                sub.start()
            _nr_pubs = _cluster[Keywords.PUBS]
            for _pub_ind in range(_nr_pubs):
                _pub_client_id += 1
                pub = Pub(cl_param.hostname, topic=_topics, port=cl_param.port,
                          client_id='pub' + str(_pub_client_id), tls=cl_param.tls, auth=cl_param.auth,
                          timeout=cl_param.pub_timeout, max_count=cl_param.pub_count, qos=cl_param.qos)
                pub_threads.append(pub)
                pub.start()

        if _default_topic is not None:
            if _all is not None:
                if isinstance(_all, list):
                    # List of topics
                    _default_topic.append(*_all)
                else:
                    # Single topic
                    _default_topic.append(_all)
            # The default subscribing item -> the remaining clients which ought to connect to the default topics
            for _pub_ind in range(cl_param.pub_clients - _multiple_topics_cl.publishers):
                pub = Pub(cl_param.hostname, topic=_default_topic, port=cl_param.port,
                          client_id='pub' + str(_multiple_topics_cl.publishers + _pub_ind),
                          tls=cl_param.tls, auth=cl_param.auth, timeout=cl_param.pub_timeout,
                          max_count=cl_param.pub_count, qos=cl_param.qos)
                pub_threads.append(pub)
                pub.start()

            for _sub_ind in range(cl_param.sub_clients - _multiple_topics_cl.subscribers):
                # set the timeout depending on the number of subs
                _timeout = cl_param.sub_timeout
                if cl_param.sub_clients > cl_param.sub_timeout:
                    _timeout = cl_param.sub_clients * 3.5
                sub = Sub(cl_param.hostname, topic=_default_topic, port=cl_param.port,
                          client_id='sub' + str(_multiple_topics_cl.subscribers + _sub_ind), tls=cl_param.tls,
                          auth=cl_param.auth, timeout=_timeout,
                          max_count=cl_param.sub_count, qos=cl_param.qos)
                sub_threads.append(sub)
                sub.start()

        elif _default_topic is None and _all is not None:
            # For in case just when we haven't
            for _pub_ind in range(cl_param.pub_clients - _multiple_topics_cl.publishers):
                pub = Pub(cl_param.hostname, topic=_all, port=cl_param.port,
                          client_id='pub' + str(_multiple_topics_cl.publishers + _pub_ind),
                          tls=cl_param.tls, auth=cl_param.auth, timeout=cl_param.pub_timeout,
                          max_count=cl_param.pub_count, qos=cl_param.qos)
                pub_threads.append(pub)
                pub.start()

            for _sub_ind in range(cl_param.sub_clients - _multiple_topics_cl.subscribers):
                # set the timeout depending on the number of subs
                _timeout = cl_param.sub_timeout
                if cl_param.sub_clients > cl_param.sub_timeout:
                    _timeout = cl_param.sub_clients * 3.5
                sub = Sub(cl_param.hostname, topic=_all, port=cl_param.port,
                          client_id='sub' + str(_multiple_topics_cl.subscribers + _sub_ind), tls=cl_param.tls,
                          auth=cl_param.auth, timeout=_timeout,
                          max_count=cl_param.sub_count, qos=cl_param.qos)
                sub_threads.append(sub)
                sub.start()

    # You can insert the logic of the default as well
    start_timer = datetime.datetime.utcnow()
    for client in sub_threads:
        client.join(cl_param.sub_timeout)
        curr_time = datetime.datetime.utcnow()
        delta = start_timer - curr_time
        if delta.total_seconds() >= cl_param.sub_timeout:
            raise Exception('Timed out waiting for threads to return')

    start_timer = datetime.datetime.utcnow()
    for client in pub_threads:
        client.join(cl_param.pub_timeout)
        curr_time = datetime.datetime.utcnow()
        delta = start_timer - curr_time
        if delta.total_seconds() >= cl_param.sub_timeout:
            raise Exception('Timed out waiting for threads to return')

    # Let's do some maths
    # Used to shut down the threads when they connection errors are present
    _active_sub_clients = 0
    if _multiple_topics_cl is not None:
        _active_sub_clients = _multiple_topics_cl.subscribers
    else:
        _active_sub_clients = cl_param.sub_clients

    _active_pub_clients = 0
    if _multiple_topics_cl is not None:
        _active_pub_clients = _multiple_topics_cl.publishers
    else:
        _active_pub_clients = cl_param.pub_clients

    # print(f'This came after {time.time() - start}')
    if SUB_QUEUE.qsize() < _active_sub_clients:
        # print(f'The size of the queue {SUB_QUEUE.qsize()} vs the number of sub clients {_active_sub_clients}')
        raise ContainersQueueError()

    if PUB_QUEUE.qsize() < _active_pub_clients:
        raise ContainersQueueError()
        # print(f'The size of the queue {PUB_QUEUE.qsize()} vs the number of pub clients {_active_pub_clients}')

    sub_times = []
    for i in range(_active_sub_clients):
        try:
            sub_times.append(SUB_QUEUE.get(timeout=cl_param.sub_timeout))
        except queue.Empty:
            continue
    if len(sub_times) < _active_sub_clients:
        failed_count = _active_sub_clients - len(sub_times)
        print("%s subscription workers failed" % failed_count)
    sub_times = numpy.array(sub_times)

    pub_times = []
    for i in range(_active_pub_clients):
        try:
            pub_times.append(PUB_QUEUE.get(timeout=cl_param.pub_timeout))
        except queue.Empty:
            continue
    if len(pub_times) < _active_pub_clients:
        failed_count = _active_pub_clients - len(pub_times)
        print("%s publishing workers failed" % failed_count)
    pub_times = numpy.array(pub_times)

    # Get the log from sub
    _ind_log = 0
    print('Pulling the data from the log queue')
    logs = []
    while not LOG_QUEUE.empty():
        logs.append(LOG_QUEUE.get(timeout=cl_param.sub_timeout))
        _ind_log += 1
        print(f'Pulling {_ind_log}-th item from log')

    # logs = []
    # for i in range(nr_msg):
    #     try:
    #         logs.append(LOG_QUEUE.get(_sub_timeout))
    #     except multiprocessing.queues.Empty:
    #         continue

    # if len(sub_times) < _sub_clients:
    #     failed_count = _sub_clients - len(sub_times)
    #     print("%s subscription workers failed" % failed_count)
    # if len(pub_times) < _pub_clients:
    #     failed_count = _pub_clients - len(pub_times)
    #     print("%s publishing workers failed" % failed_count)

    # if LOG_QUEUE.qsize() < nr_msg:
    #     print('Something went wrong with logging. There are less messages logged than sent')

    # Writing the result to log file
    write(log_file, logs)

    # Benchmarking components
    sub_mean_duration = sub_std_duration = sub_avg_throughput = sub_total_thpt = 0
    pub_mean_duration = pub_std_duration = pub_avg_throughput = pub_total_thpt = 0

    print('Sub times array')
    print(sub_times)
    print('Pub times array')
    print(pub_times)

    # Check whether sub are present
    if cl_param.sub_count * cl_param.sub_clients > 0:
        sub_mean_duration = numpy.mean(sub_times)
        sub_std_duration = numpy.std(sub_times)
        sub_avg_throughput = float(cl_param.sub_count) / float(sub_mean_duration)
        sub_total_thpt = float(cl_param.sub_count * cl_param.sub_clients) / float(sub_mean_duration)

    if cl_param.pub_count * cl_param.pub_clients > 0:
        pub_mean_duration = numpy.mean(pub_times)
        pub_std_duration = numpy.std(pub_times)
        pub_avg_throughput = float(cl_param.pub_count) / float(pub_mean_duration)
        pub_total_thpt = float(
            cl_param.pub_count * cl_param.pub_clients) / float(pub_mean_duration)

    # Explanation of the parameters:
    # pub_times is the overall publish time for each of the clients,
    # starting from the moment the client is connected to the broker
    # and ending when all the messages (pub_count) has been sent
    if cl_param.brief:
        output = '%s;%s;%s;%s;%s;%s;%s;%s;%s;%s'
    else:
        output = """\
[ran with %s subscribers and %s publishers]
================================================================================
Subscription Results
================================================================================
Avg. subscriber duration: %s
Subscriber duration std dev: %s
Avg. Client Throughput: %s
Total Throughput (msg_count * clients) / (avg. sub time): %s
================================================================================
Publisher Results
================================================================================
Avg. publisher duration: %s
Publisher duration std dev: %s
Avg. Client Throughput: %s
Total Throughput (msg_count * clients) / (avg. sub time): %s
"""
    # e2e Delay of msg
    # divide the components of the delay
    # throughtput input/output
    # cpu/ RAM -> broker

    print(output % (
        cl_param.sub_clients,
        cl_param.pub_clients,
        sub_mean_duration,
        sub_std_duration,
        sub_avg_throughput,
        sub_total_thpt,
        pub_mean_duration,
        pub_std_duration,
        pub_avg_throughput,
        pub_total_thpt,
    ))

    _hostname = os.getenv('HOSTNAME')
    while True:
        if all((not sub.is_alive()) for sub in sub_threads):
            print(f'{_hostname} finished its operation')
        time.sleep(2)


if __name__ == '__main__':
    # hostname = '172.20.0.2'
    hostname = None
    main(host=hostname)
