#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Roger Light <roger@atchoo.org>
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Distribution License v1.0
# which accompanies this distribution.
#
# The Eclipse Distribution License is available at
#   http://www.eclipse.org/org/documents/edl-v10.php.
#
# Contributors:
#    Roger Light - initial implementation

# This shows an example of using the publish.single helper function.

# import context  # Ensures paho is in PYTHONPATH
import paho.mqtt.publish as publish
from datetime import datetime
import paho.mqtt.client as mqtt

import time
import os


# import docker

def on_connect(mqttc, obj, flags, rc):
    print('Client connected')
    print("rc: " + str(rc))
    mqttc.publish('test', payload=str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')))

def on_publish(client, userdata, mid):
    print('Message published')

def on_log(client, userdata, level, buf):
    print('Client has log data')

def prior_method():
    # hostname = "192.168.56.128"
    # hostname = server.local_bind_address[0]
    # mqtt_port = server.local_bind_address[1]
    _ports = [1883, 8883, 8080, 44053, 4369, 8888,
              9100, 9101, 9102, 9103, 9104, 9105, 9106,
              9107, 9108, 9109]
    _hostnames = ["172.20.0.2", "172.17.0.2", 'vernemq_2', 'VerneMQ@172.20.0.2', '172.20.0.1', '172.17.0.1',
                  'localhost']
    # _hostnames = ['172.17.0.1', '172.17.0.2', '172.17.0.3','172.17.0.4', '172.17.0.5', '172.17.0.6']
    _hostnames = ["172.20.0.2", "172.20.0.3"]  # , 'VerneMQ@172.20.0.2', '172.20.0.1', '172.17.0.1', '172.17.0.2'
    # "172.20.0.3","172.20.0.4","172.20.0.5","172.20.0.6", '127.0.0.1'
    # hostname = "172.20.0.2"
    # hostname= 'vernemq_2'
    mqtt_port = 1883

    topic = "test"
    msg = str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))

    # client.connect(broker_address)  # connect to broker
    # client.publish("house/main-light", "OFF")  # publish
    # print(datetime.utcnow())
    # publish.single("paho/test/single", "boo", hostname="mqtt.eclipse.org")
    # publish.single(topic=topic, payload=msg, hostname=hostname )

    client = mqtt.Client()  # create new instance
    # client.on_connect = on_connect
    # client.connect(hostname)  # connect to broker
    client.on_connect = on_connect

    for hostname in _hostnames:
        # for port in _ports:
        try:
            client.connect(hostname)  # , bind_address='172.17.0.2'
            time.sleep(10)
            client.publish(topic, payload=msg)
            # publish.single(topic=topic, payload=msg, hostname=hostname)
            # client.connect(hostname, port=port, keepalive=60) #, bind_address="172.20.0.2"
            # client.publish(topic=topic, payload=msg) # , hostname=hostname
        except:
            print('Hostname ', hostname, ' and port ', 1883, ' is not to be used.')
            continue
        print("Finished the publish")

    # exit(1)


if __name__ == '__main__':
    # Printing the environmental variables
    _hostname = os.getenv('MQTT_HOSTNAME')
    print('The passed environmental variable is %s' % _hostname)

    _test_non_existing = os.getenv('MQTT_HOS')
    print('The passed environmental variable is %s' % _test_non_existing)

    hostname = "172.20.0.2"
    topic = "test"
    msg = str(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))
    # print('The message transmitted is: %s'.format(msg))
    # sys.stdout.write('The message transmitted is: %s'.format(msg))
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_log = on_log
    client.connect(hostname)
    client.loop_start()
    # client.loop_forever(timeout=1.0, max_packets=1, retry_first_connection=False)
    # time.sleep(10)
    # client.publish(topic, payload=msg)
    time.sleep(5)
    client.loop_stop()