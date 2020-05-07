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
# under the License.

import argparse
import datetime
import multiprocessing
import random
import string
import time
import os
import json

import numpy
import paho.mqtt.client as mqtt

from .subsidiary_code import MultipleTopics

BASE_TOPIC = 'test'

SUB_QUEUE = multiprocessing.Queue()
PUB_QUEUE = multiprocessing.Queue()
LOG_QUEUE = multiprocessing.Queue()

nr_msg = 0


# Class Timer might be used to control the execution time of the sub and pub
# class Timer(multiprocessing.Process):
#     def __init__(self, interval, function, args=[], kwargs={}):
#         super(Timer, self).__init__()
#         self.interval = interval
#         self.function = function
#         self.args = args
#         self.kwargs = kwargs
#         self.finished = multiprocessing.Event()
#
#     def cancel(self):
#         """Stop the timer if it hasn't finished yet"""
#         self.finished.set()
#
#     def run(self):
#         self.finished.wait(self.interval)
#         if not self.finished.is_set():
#             self.function(*self.args, **self.kwargs)
#         self.finished.set()


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
            return cmd_par or env_par
        else:
            raise Exception('Unexpected parameter type')


def is_positive(param: int, param_name: str):
    """Validate parameter to be positive"""
    if param < 0:
        raise Exception('The %s must be positive' % param_name)


def initialize_log(hostname: str, dest_path: str = 'logs', file_name: str = None, prefix: str = ''):
    octets = hostname.split('.')
    if len(octets) != 4:
        raise Exception('Hostname passed is invalid')
    if file_name is None:
        file_name = prefix + '_log_' + octets[3] + '.csv'
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
    with open(log, 'a') as f:
        for chunk in data:
            f.write(chunk)
            f.write('\n')
        f.close()


class Sub(multiprocessing.Process):
    def __init__(self, hostname, port: int = 1883, client_id: str = None, tls=None, auth=None, topic: str = None,
                 timeout: int = 60, max_count: int = 10, qos: int = 0):
        super(Sub, self).__init__()
        self.hostname = hostname
        self.port = port
        self.client_id = client_id
        self.tls = tls
        self.topic = topic or BASE_TOPIC
        self.auth = auth
        self.msg_count = 0
        self.start_time = None
        self.max_count = max_count
        self.end_time = None
        self.timeout = timeout
        self.qos = qos
        self.end_time_lock = multiprocessing.Lock()

    def write_to_log(self, pub_host: str = None, pub_id: str = None, pub_con_init: datetime.datetime = None,
                     pub_con_accomplish: datetime.datetime = None, pub_timestamp: datetime.datetime = None,
                     pub_qos: str = None, sub_host: str = None, sub_id: str = None,
                     sub_timestamp: datetime.datetime = None, e2e_delay: datetime.timedelta = None):
        # print('Writing the message to log')
        log_format = '%s' + ';%s' * 9
        LOG_QUEUE.put(log_format % (pub_host, pub_id, pub_con_init, pub_con_accomplish,
                                    pub_timestamp, pub_qos,
                                    sub_host, sub_id, sub_timestamp,
                                    e2e_delay))

    def parse_msg(self, msg):
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

    def on_connect(self, client, userdata, flags, rc):
        # Added the condition to connect to passed topic
        # print('Client connected to broker')
        if self.topic is None:
            client.subscribe(BASE_TOPIC + '/#', qos=self.qos)
        else:
            client.subscribe(self.topic, qos=self.qos)

    def on_subscribe(self, client, obj, mid, granted_qos):
        pass
        # print("Subscribed: " + str(mid) + " " + str(granted_qos))

    def on_message(self, client, userdata, msg):
        # print('A new message has arrived')
        if self.start_time is None:
            self.start_time = datetime.datetime.utcnow()

        _msg_arrival_time = datetime.datetime.utcnow()
        # Parse the msg
        _pub_msg_dictt = self.parse_msg(msg)
        if isinstance(_pub_msg_dictt['publish_timestamp'], datetime.datetime):
            # print('The dict parsing works')
            _msg_e2e_delay = _msg_arrival_time - _pub_msg_dictt['publish_timestamp']
            # Write the result
            self.write_to_log(pub_host=_pub_msg_dictt['hostname'], pub_id=_pub_msg_dictt['pub_id'],
                              pub_con_init=_pub_msg_dictt['pub_con_init'],
                              pub_con_accomplish=_pub_msg_dictt['pub_con_accomplish'],
                              pub_timestamp=_pub_msg_dictt['publish_timestamp'], pub_qos=_pub_msg_dictt['pub_qos'],
                              sub_host=self.hostname, sub_id=self.client_id, sub_timestamp=_msg_arrival_time,
                              e2e_delay=_msg_e2e_delay)

        self.msg_count += 1
        if self.msg_count >= self.max_count:
            # print('We hve entered in the final part ')
            self.end_time_lock.acquire()
            if self.end_time is None:
                self.end_time = datetime.datetime.utcnow()
            self.end_time_lock.release()
            # after we have reached the max count we stop the loop to continue further
            self.client.loop_stop()

    def run(self):

        self.client = mqtt.Client()
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
            self.end_time_lock.acquire()
            if self.end_time:
                delta = self.end_time - self.start_time
                SUB_QUEUE.put(delta.total_seconds())
                self.client.loop_stop()
                break
            self.end_time_lock.release()
            if self.start_time:
                current_time = datetime.datetime.utcnow()
                curr_delta = current_time - self.start_time
                if curr_delta.total_seconds() > self.timeout:
                    raise Exception('We hit the sub timeout!')


class Pub(multiprocessing.Process):
    def __init__(self, hostname, port=1883, client_id: str = None, tls=None, auth=None, topic: str = None,
                 timeout: int = 60, max_count: int = 10, msg_size: int = 1024, qos: int = 0):
        super(Pub, self).__init__()
        self.hostname = hostname
        self.port = port
        self.client_id = client_id
        self.tls = tls
        self.topic = topic or BASE_TOPIC
        self.auth = auth
        self.start_time = None
        self.max_count = max_count
        self.end_time = None
        self.timeout = timeout
        self.msg = None
        self.qos = qos
        self.msg_size = msg_size
        self.connect_init = None
        self.connect_accomplish = None
        if self.msg_size < 51:
            raise Exception('Message size should be at least 50 characters')

    def create_msg(self):

        if self.connect_init is None:
            self.connect_init = ''
        if self.connect_accomplish is None:
            self.connect_accomplish = ''
        _pre_msg = self.hostname + '_' + self.client_id + '_' + str(self.connect_init) + '_' \
                   + str(self.connect_accomplish) + '_' + str(datetime.datetime.utcnow()) + '_' \
                   + str(self.qos) + '_'
        return _pre_msg + ''.join(
            random.choice(string.ascii_lowercase) for i in range(self.msg_size - len(_pre_msg.encode('utf-8'))))

    def on_publish(self, client, userdata, mid):
        # print('The message was published')
        # Used for qos 1 and 2
        # For QoS 0, this simply means that the message has left the client
        # For other qoses, this means the handshake process has successfully ended
        pass

    def on_connect(self, client, obj, flags, rc):
        # print(mqtt.connack_string(rc))
        self.start_time = datetime.datetime.utcnow()
        if rc == 0:
            self.connect_accomplish = self.start_time
            # print('The loop started')
            for i in range(self.max_count):
                self.msg = self.create_msg()
                client.publish(self.topic, payload=self.msg, qos=self.qos)
                if self.start_time:
                    current_time = datetime.datetime.utcnow()
                    curr_delta = current_time - self.start_time
                    if curr_delta.total_seconds() > self.timeout:
                        raise Exception('We hit the pub timeout!')
            self.end_time = datetime.datetime.utcnow()
            delta = self.end_time - self.start_time
            PUB_QUEUE.put(delta.total_seconds())

    def run(self):

        client = mqtt.Client()
        if self.tls:
            client.tls_set(**self.tls)
        if self.auth:
            client.username_pw_set(**self.auth)

        client.on_connect = self.on_connect
        client.on_publish = self.on_publish

        # print('The client object was successfully created')
        self.connect_init = datetime.datetime.utcnow()
        client.connect(self.hostname, port=self.port)
        client.loop_start()

        # Keep running until we have set the end_time parameter, which happen after everything is finished
        while True:
            time.sleep(1)
            if self.end_time:
                client.loop_stop()
                break


def main(hostname=None):
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
    parser.add_argument('--topic',
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

    opts = parser.parse_args()

    sub_threads = []
    pub_threads = []

    ### parse the parameters
    _topic = getattr(opts, 'topic') or os.getenv('CLIENT_TOPIC') or BASE_TOPIC
    _hostname = getattr(opts, 'hostname') or os.getenv('CLIENT_HOSTNAME') or hostname
    _port = set_value(getattr(opts, 'port'), os.getenv('CLIENT_PORT'), 1883, 'port')
    _sub_clients = set_value(getattr(opts, 'sub_clients'), os.getenv('CLIENT_SUBSCRIBERS'), 0, 'number of subscribers')
    _sub_count = set_value(getattr(opts, 'sub_count'), os.getenv('CLIENT_SUBSCRIBERS_COUNT'), 0,
                           'number of messages per subscriber')
    _pub_clients = set_value(getattr(opts, 'pub_clients'), os.getenv('CLIENT_PUBLISHERS'), 0, 'number of publishers')
    _pub_count = set_value(getattr(opts, 'pub_count'), os.getenv('CLIENT_PUBLISHERS_COUNT'), 0,
                           'number of messages per publisher')
    _sub_timeout = set_value(getattr(opts, 'sub_timeout'), os.getenv('CLIENT_SUBSCRIBERS_TIMEOUT'), 60,
                             'subscriber timeout')
    _pub_timeout = set_value(getattr(opts, 'pub_timeout'), os.getenv('CLIENT_PUBLISHERS_TIMEOUT'), 60,
                             'publisher timeout')
    _qos = set_value(getattr(opts, 'qos'), os.getenv('CLIENT_QOS'), 0, 'qos')
    _msg = getattr(opts, 'msg') or os.getenv('CLIENT_MESSAGE')
    _brief = getattr(opts, 'brief') or os.getenv('CLIENT_BRIEF') or False
    _multiple_topics = getattr(opts, 'multiple_topics') or os.getenv('CLIENT_MULTIPLE_TOPICS') or None
    _description = getattr(opts, 'description') or os.getenv('DESCRIPTION') or ''

    if not isinstance(_topic, str):
        raise Exception('The topic parameter must be string type')
    if not isinstance(_hostname, str):
        raise Exception('The hostname parameter must be string type')
    if not isinstance(_brief, bool):
        raise Exception('The brief parameter must be boolean type')

    # Check if parameters are positive, otherwise raise an error
    is_positive(_sub_clients, 'number of subscribers')
    is_positive(_pub_clients, 'number of publishers')
    is_positive(_sub_count, 'number of messages per subscriber')
    is_positive(_pub_count, 'number of messages per publisher')

    if isinstance(_qos, int):
        if _qos not in [0, 1, 2]:
            raise Exception('The QOS value is expected to be 0, 1 or 2')
    else:
        raise Exception('The QOS parameter must be int type ')

    _tls = None
    if getattr(opts, 'cacert'):
        _tls = {'ca_certs': opts.cacert}
    # Check if certificate has been given as env parameter
    elif os.getenv('CAERT'):
        _tls = {'ca_certs': os.getenv('CAERT')}

    _auth = None
    if opts.username:
        _auth = {'username': opts.username,
                 'password': getattr(opts, 'password')}
    elif os.getenv('CLIENT_USERNAME'):
        _auth = {'username': os.getenv('CLIENT_USERNAME'),
                 'password': os.getenv('CLIENT_PASSWORD')}

    # Not necessary for our use-case
    # if _pub_count * _pub_clients < _sub_count:
    #     print('The configured number of publisher clients and published '
    #           'message count is too small for the configured subscriber count.'
    #           ' Increase the value of --pub-count and/or --pub-clients, or '
    #           'decrease the value of --sub-count.')
    #     exit(1)
    # Log file
    log_file = initialize_log(_hostname, dest_path='/home/logs', prefix=_description)
    # raise Exception('Log file successfully created')
    # print('Log file created')

    ## the multiple-topics
    multi_tocic_cl = MultipleTopics(parser)
    _multiple_topics_dict = {}
    if _multiple_topics is not None:
        _multiple_topics_dict = multi_tocic_cl(_multiple_topics)

    for i in range(_sub_clients):
        # print('Starting the sub')
        sub = Sub(_hostname, port=_port, client_id='sub' + str(i), tls=_tls,
                  auth=_auth, topic=_topic, timeout=_sub_timeout,
                  max_count=_sub_count, qos=_qos)
        sub_threads.append(sub)
        sub.start()

    for i in range(_pub_clients):
        pub = Pub(_hostname, port=_port, client_id='pub' + str(i), tls=_tls,
                  auth=_auth, topic=_topic, timeout=_pub_timeout,
                  max_count=_pub_count, qos=_qos)
        pub_threads.append(pub)
        pub.start()

    start_timer = datetime.datetime.utcnow()
    for client in sub_threads:
        client.join(_sub_timeout)
        curr_time = datetime.datetime.utcnow()
        delta = start_timer - curr_time
        if delta.total_seconds() >= _sub_timeout:
            raise Exception('Timed out waiting for threads to return')

    start_timer = datetime.datetime.utcnow()
    for client in pub_threads:
        client.join(_pub_timeout)
        curr_time = datetime.datetime.utcnow()
        delta = start_timer - curr_time
        if delta.total_seconds() >= _sub_timeout:
            raise Exception('Timed out waiting for threads to return')

    # Check if message has been given as a parameter when the nr of pub is greater than 0
    # if _pub_count > 0 and _msg is None:
    #     print('--msg is needed when publishers '
    #           'are present')
    #     exit(1)

    # Let's do some maths
    # Used to shut down the threads when they connection errors are present
    if SUB_QUEUE.qsize() < _sub_clients:
        print('Something went horribly wrong, there are less results than '
              'sub threads')
        exit(1)
    if PUB_QUEUE.qsize() < _pub_clients:
        print('Something went horribly wrong, there are less results than '
              'pub threads')
        exit(1)

    sub_times = []
    for i in range(_sub_clients):
        try:
            sub_times.append(SUB_QUEUE.get(_sub_timeout))
        except multiprocessing.queues.Empty:
            continue
    if len(sub_times) < _sub_clients:
        failed_count = _sub_clients - len(sub_times)
    sub_times = numpy.array(sub_times)

    pub_times = []
    for i in range(_pub_clients):
        try:
            pub_times.append(PUB_QUEUE.get(_pub_timeout))
        except multiprocessing.queues.Empty:
            continue
    if len(pub_times) < _pub_clients:
        failed_count = _pub_clients - len(pub_times)
    pub_times = numpy.array(pub_times)

    # Get the log from sub
    logs = []
    while not LOG_QUEUE.empty():
        logs.append(LOG_QUEUE.get(_sub_timeout))

    # logs = []
    # for i in range(nr_msg):
    #     try:
    #         logs.append(LOG_QUEUE.get(_sub_timeout))
    #     except multiprocessing.queues.Empty:
    #         continue

    if len(sub_times) < _sub_clients:
        failed_count = _sub_clients - len(sub_times)
        print("%s subscription workers failed" % failed_count)
    if len(pub_times) < _pub_clients:
        failed_count = _pub_clients - len(pub_times)
        print("%s publishing workers failed" % failed_count)

    # if LOG_QUEUE.qsize() < nr_msg:
    #     print('Something went wrong with logging. There are less messages logged than sent')

    # Writing the result to log file
    write(log_file, logs)

    # Benchmarking components
    sub_mean_duration = sub_std_duration = sub_avg_throughput = sub_total_thpt = 0
    pub_mean_duration = pub_std_duration = pub_avg_throughput = pub_total_thpt = 0

    # Check whether sub are present
    if _sub_count * _sub_clients > 0:
        sub_mean_duration = numpy.mean(sub_times)
        sub_std_duration = numpy.std(sub_times)
        sub_avg_throughput = float(_sub_count) / float(sub_mean_duration)
        sub_total_thpt = float(_sub_count * _sub_clients) / float(sub_mean_duration)

    if _pub_count * _pub_clients > 0:
        pub_mean_duration = numpy.mean(pub_times)
        pub_std_duration = numpy.std(pub_times)
        pub_avg_throughput = float(_pub_count) / float(pub_mean_duration)
        pub_total_thpt = float(
            _pub_count * _pub_clients) / float(pub_mean_duration)

    ### Explanation of the parameters:
    # pub_times is the overall publish time for each of the clients,
    # starting from the moment the client is connected to the broker
    # and ending when all the messages (pub_count) has been sent
    if _brief:
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
        _sub_clients,
        _pub_clients,
        sub_mean_duration,
        sub_std_duration,
        sub_avg_throughput,
        sub_total_thpt,
        pub_mean_duration,
        pub_std_duration,
        pub_avg_throughput,
        pub_total_thpt,
    ))


if __name__ == '__main__':
    # hostname = '172.20.0.2'
    hostname = None
    main(hostname=hostname)
