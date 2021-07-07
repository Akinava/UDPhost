# -*- coding: utf-8 -*-
__author__ = 'Akinava'
__author_email__ = 'akinava@gmail.com'
__copyright__ = 'Copyright © 2019'
__license__ = 'MIT License'
__version__ = [0, 0]


import json
import random
from cryptotool import *
from utilit import Singleton
from settings import logger
import settings


class Peers(Singleton):
    def __init__(self):
        logger.info('Peers')
        self.__load()

    def get_random_server_from_file(self):
        logger.info('')
        servers = self.__filter_peers_by_type('server')
        if not servers:
            return None
        return random.choice(servers)

    def __find_peer(self, filter_kwargs):
        logger.info('')
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
        self.__peers = self.__read_file()
        self.__unpack_peers_property()

    def __save(self):
        self.__pack_peers_property()
        self.__save_file()

    def __read_file(self):
        with open(settings.peers_file, 'r') as f:
            peers_list = json.loads(f.read())
        return peers_list

    def __save_file(self):
        with open(settings.peers_file, 'w') as f:
            f.write(json.dumps(self.__peers, indent=4))

    def __unpack_peers_property(self):
        logger.info('')
        for peer in self.__peers:
            peer['pub_key'] = B58().unpack(peer['pub_key'])

    def __pack_peers_property(self):
        logger.info('')
        for peer in self.__peers:
            peer['pub_key'] = B58().pack(peer['pub_key'])

    def __filter_peers_by_type(self, peers_filter):
        logger.info('')
        filtered_peers = []
        for peer in self.__peers:
            if peer['type'] != peers_filter:
                continue
            filtered_peers.append(peer)
        return filtered_peers