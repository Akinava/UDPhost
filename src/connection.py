# -*- coding: utf-8 -*-
__author__ = 'Akinava'
__author_email__ = 'akinava@gmail.com'
__copyright__ = 'Copyright © 2019'
__license__ = 'MIT License'
__version__ = [0, 0]


import struct
from time import time
import random
import json
from crypt_tools import Tools as CryptTools
from utilit import Singleton, encode
import settings
from settings import logger


class Connection:
    def __init__(self, local_host=None, local_port=None, remote_host=None, remote_port=None, transport=None):
        if local_host: self.__set_local_host(local_host)
        if local_port: self.__set_local_port(local_port)
        if remote_host: self.__set_remote_host(remote_host)
        if remote_port: self.__set_remote_port(remote_port)
        if transport: self.__set_transport(transport)
        self.__set_last_response()

    def __eq__(self, connection):
        if self.__remote_host != connection.__remote_host:
            return False
        if self.__remote_port != connection.__remote_port:
            return False
        return True

    def is_alive(self):
        if self.transport.is_closing():
            return False
        return True

    def __last_send_made_over_peer_timeout_but_has_no_request(self):
        return time() - self.__last_response > settings.peer_timeout_seconds

    def last_request_is_time_out(self):
        if not hasattr(self, '__last_request'):
            if self.__last_send_made_over_peer_timeout_but_has_no_request():
                return True
            return None
        return time() - self.__last_request > settings.peer_timeout_seconds

    def last_response_is_over_ping_time(self):
        return time() - self.__last_response > settings.peer_ping_time_seconds

    def __set_last_response(self):
        self.__last_response = time()

    def __set_last_request(self):
        self.__last_request = time()

    def __set_transport(self, transport):
        self.transport = transport

    def set_type(self, connection_type):
        self.type = connection_type

    def __set_protocol(self, protocol):
        self.__protocol = protocol

    def __set_local_host(self, local_host):
        self.local_host = local_host

    def __set_local_port(self, local_port):
        self.local_port = local_port

    def __set_remote_host(self, remote_host):
        self.__remote_host = remote_host

    def get_remote_host(self):
        return self.__remote_host

    def __set_remote_port(self, remote_port):
        self.__remote_port = remote_port

    def get_remote_port(self):
        return self.__remote_port

    def __set_request(self, request):
        self.__request = request

    def get_request(self):
        return self.__request

    def update_request(self, connection):
        self.__request = connection.get_request()
        self.__set_last_request()

    def set_fingerprint(self, fingerprint):
        self.fingerprint = fingerprint

    def get_fingerprint(self):
        return self.fingerprint

    def dump_addr(self):
        return struct.pack('>BBBBH', *(map(int, self.__remote_host.split('.'))), self.__remote_port)

    @classmethod
    def loads_addr(self, addr):
        host_tuple = struct.unpack('>BBBB', addr[:4])
        host = '.'.join(map(str, host_tuple))
        port = struct.unpack('>H', addr[4:])[0]
        return host, port

    def datagram_received(self, request, remote_addr, transport):
        self.set_remote_addr(remote_addr)
        self.__set_request(request)
        self.__set_transport(transport)

    def set_remote_addr(self, addr):
        self.__set_remote_host(addr[0])
        self.__set_remote_port(addr[1])

    def __get_remote_addr(self):
        return (self.__remote_host, self.__remote_port)

    def send(self, response):
        logger.info('')
        logger.info('send %s to %s' % (encode(response), self.__get_remote_addr()))
        self.transport.sendto(encode(response), self.__get_remote_addr())
        self.__set_last_response()

    def shutdown(self):
        if self.transport.is_closing():
            return
        self.transport.close()


class NetPool(Singleton):
    def __init__(self):
        self.__group = []

    def __clean_groups(self):
        alive_group_tmp = []
        for connection in self.__group:
            if connection.last_request_is_time_out() is True:
                connection.shutdown()
                continue
            self.__mark_connection_type(connection)
            alive_group_tmp.append(connection)
        self.__group = alive_group_tmp

    def swarm_status_stable(self):
        if hasattr(self, '__swarm_stable'):
            return True
        return False

    def __set_swarm_connection_status(self):
        if hasattr(self, '__swarm_stable'):
            return
        if self.has_enough_connections():
            self.__swarm_stable = True

    def has_enough_connections(self):
        return len(self.get_all_client_connections()) >= settings.peer_connections

    def __mark_connection_type(self, connection):
        if not hasattr(connection, 'type'):
            connection.type = 'client'

    def save_connection(self, new_connection):
        if not new_connection in self.__group:
            self.__group.append(new_connection)
            return
        connection_index = self.__group.index(new_connection)
        old_connection = self.__group[connection_index]
        old_connection.update_request(new_connection)
        self.__set_swarm_connection_status()

    def get_all_connections(self):
        self.__clean_groups()
        return self.__group

    def get_all_client_connections(self):
        return self.__filter_connection_by_type('client')

    def get_random_client_connection(self):
        group = self.__filter_connection_by_type('client')
        return random.choice(group) if group else None

    def get_server_connections(self):
        return self.__filter_connection_by_type('server')

    def has_client_connection(self):
        group = self.__filter_connection_by_type('client')
        return len(group) > 0

    def __filter_connection_by_type(self, my_type):
        self.__clean_groups()
        group = []
        for connection in self.__group:
            if not hasattr(connection, 'type'):
                continue
            if connection.type == my_type:
                group.append(connection)
        return group

    def shutdown(self):
        for connection in self.__group:
            connection.shutdown()
        self.__group = []


class Peers(Singleton):
    def __init__(self):
        self.__load()

    def get_random_server_from_file(self):
        servers = self.__filter_peers_by_type('server')
        if not servers:
            return None
        return random.choice(servers)

    def save_server_last_response_time(self, connection):
        server = self.__find_peer({
            'type': 'server',
            'fingerprint': connection.get_fingerprint(),
            'host': connection.get_remote_host(),
            'port': connection.get_remote_port()})
        if isinstance(server, dict):
            server['last_response'] = now()
            self.__save()

    def __find_peer(self, filter_kwargs):
        for peer in self.__peers:
            for key, val in filter_kwargs.items():
                if peer.get(key) != val:
                    continue
            return peer

    def get_servers_list(self):
        servers = self.__filter_peers_by_type('server')
        if not servers:
            return None
        servers = self.__filter_peers_by_last_response_field(servers=servers, days_delta=settings.servers_timeout_days)
        return servers[settings.peer_connections]

    def put_servers_list(self, servers_list):
        for server_data in servers_list:
            server = self.__find_peer({
                'protocol': server_data['protocol'],
                'type': 'server',
                'fingerprint': server_data['fingerprint'],
                'host': server_data['host'],
                'port': server_data['port']})
            if server is None:
                self.__peers.append(server_data)
        self.__save()

    def __filter_peers_by_last_response_field(self, servers, days_delta):
        filtered_list = []
        for peer in servers:
            datatime_string = peer.get('last_response')
            if datatime_string is None:
                continue
            if str_to_datetime(datatime_string) + timedelta(days=days_delta) < now():
                continue
            filtered_list.append(peer)
        return filtered_list

    def __load(self):
        peers = self.__read_file()
        self.__peers = self.__unpack_peers_fingerprint(peers)

    def __save(self):
        peers = self.__pack_peers_fingerprint(self.__peers)
        self.__save_file(peers)

    def __read_file(self):
        with open(settings.peers_file, 'r') as f:
            peers_list = json.loads(f.read())
        return peers_list

    def __save_file(self, data):
        with open(settings.peers_file, 'w') as f:
            f.write(json.dumps(data))

    def __unpack_peers_fingerprint(self, peers):
        return CryptTools().unpack_peers_fingerprint(peers)

    def __pack_peers_fingerprint(self, peers):
        return CryptTools().pack_peers_fingerprint(peers)

    def __filter_peers_by_type(self, filter):
        filtered_peers = []
        for peer in self.__peers:
            if peer['type'] != filter:
                continue
            filtered_peers.append(peer)
        return filtered_peers
