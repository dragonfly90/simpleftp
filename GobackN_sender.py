#python GobackN_sender.py localhost 7735 test_file.txt 3 500

import socket
import sys
from collections import namedtuple
import pickle
import threading
import inspect
import time
import signal
import errno



data_pkt = namedtuple('data_pkt', 'seq_num checksum data_type data')

server_host = sys.argv[1]
port = int(sys.argv[2])
filename = sys.argv[3]
N = sys.argv[4]
MSS = sys.argv[5]
MAXTIMEINTERVAL = 5 #Time out interval
base = 0  #sequence number of the oldest unacknowledged packet
nextseqnum = 0  #the smallest unsend sequence number
allpackets = []

sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sender_port = 62223
sender.bind(('', sender_port))


def checkmessage(message):
    checksum = 0
    for i in range(0, (len(message) - len(message) % 2), 2):
        my_message = str(message)
        w = ord(my_message[i]) + (ord(my_message[i+1]) << 8)
        checksum = checksum + w
        checksum = (checksum & 0xffff) + (checksum >> 16)

    return (not checksum) & 0xfff

def pack_data(message, seq_num):
    # a 32-bit sequence number
    # a 16-bit checksum of the data part, computed in the same way as the UDP checksum
    # a 16-bit field that has the value 0101010101010101, indicating that this is a data packet
    pkt = data_pkt(seq_num, checkmessage(message), 0b101010101010101, message)
    my_list = [pkt.seq_num, pkt.checksum, pkt.data_type, pkt.data]
    packed_pkt = pickle.dumps(my_list)
    return packed_pkt

def packagesfromeFile(file_content):
    pkts_to_send = []
    seq_num = 0
    for item in file_content:   # Every MSS bytes should be packaged into segment Foo
        pkts_to_send.append(pack_data(item, seq_num))
        seq_num += 1
    return pkts_to_send

def timer(s,f):
    global base
    global nextseqnum
    global host
    global port
    global sender
    global allpackets

    signal.setitimer(signal.ITIMER_REAL, MAXTIMEINTERVAL)

    print "Timeout, sequence number =", base
    for i in range(base, nextseqnum):
        sender.sendto(allpackets[i],(host, port))


def rdt_send(filename, rcv_host):
    global sender
    global host
    global port
    global allpackets
    global base
    global nextseqnum

    host = rcv_host

    signal.signal(signal.SIGALRM, timer)
    try:
        file_content = []
        with open(filename, 'rb') as f:

            while True:
                chunk = f.read(int(MSS))
                if chunk:
                    file_content.append(chunk)

                else:
                    break
    except FileNotFoundError:
        sys.exit("Failed to open file!")
    


    allpackets = packagesfromeFile(file_content)
    total_pkts = len(file_content)


    while base < total_pkts:
        while nextseqnum < min(base + int(N), total_pkts):

            sender.sendto(allpackets[nextseqnum],(rcv_host, port))
            if base == nextseqnum:
                signal.setitimer(signal.ITIMER_REAL, MAXTIMEINTERVAL)

            nextseqnum += 1

        try:
            data, addr = sender.recvfrom(256)
            data = pickle.loads(data)
            if data[2]=="1010101010101010":  # To ensure it is an ACK
                base = data[0] + 1
                if base == nextseqnum:
                    signal.alarm(0)
                else:
                    signal.setitimer(signal.ITIMER_REAL, MAXTIMEINTERVAL)
        except socket.error as e:
            if e.errno != errno.EINTR:
                raise
            else:
                continue
    base = 0
    nextseqnum = 0
    allpackets = []
    print("Done!")

if __name__ == "__main__":
    rdt_send(filename, server_host)