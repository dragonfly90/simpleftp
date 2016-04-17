#python GobackN_receiver.py 7735 testSave.txt 0.05

import socket
import pickle
import sys
from collections import namedtuple
import random
import time
import datetime


port = int(sys.argv[1])
filename = sys.argv[2]
prob_loss= sys.argv[3]

receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiver.bind(('', port))


def checkmessage(message):
    checksum = 0
    for i in range(0, (len(message) - len(message) % 2), 2):
        my_message = str(message)
        w = ord(my_message[i]) + (ord(my_message[i+1]) << 8)
        checksum = checksum + w
        checksum = (checksum & 0xffff) + (checksum >> 16)

    return (not checksum) & 0xfff

def rdt_recv(filename):
    expectedseqnum = 0
    while True:
        receiver.settimeout(30)
        try:
            data, addr = receiver.recvfrom(1000000)
            receiver.settimeout(30)
        except socket.timeout:
            print("Session Finish!")
            break

        data = pickle.loads(data)

        seq_num, checksum, data_type, message = data[0], data[1], data[2], data[3]
        rand_loss = random.random()
        if rand_loss <= float(prob_loss):
            if seq_num == expectedseqnum:
                print "Packet loss, sequence number = ", seq_num
        else:
            if checksum != checkmessage(message):
                print("DATA: ", data)
                print("Packet dropped, checksum doesn't match!")
            if seq_num == expectedseqnum:
                with open(filename, 'ab') as file:
                    file.write(message)

                #the 32-bit sequence number that is being ACKed
                #a 16-bit field that is all zeros
                #a 16-bit field that has the value 1010101010101010, indicating that this is an ACK packet
                ack_message = [seq_num, "0000000000000000", "1010101010101010"]

                receiver.sendto(pickle.dumps(ack_message), (addr))

                expectedseqnum += 1

if __name__ == "__main__":

    rdt_recv(filename)