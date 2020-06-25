import local_subscriber as sub
import local_publisher as pub
import subprocess
import time

if __name__ == '__main__':
    sub_json_config = '../broker-clients.json'
    pub_json_config = '../broker-clients-publishers.json'
    subs = sub.Subscribers(json_config=sub_json_config)
    pubs = pub.Publishers(json_config=pub_json_config)

    subs.start()
    time.sleep(10)
    while not subs.ready_to_receive_msgs:
        print('Subs are not yet ready to receive msgs')
        print(subs.ready_to_receive_msgs)
        time.sleep(2)
    pubs.start()
