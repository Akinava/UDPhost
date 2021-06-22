# -*- coding: utf-8 -*-
__author__ = 'Akinava'
__author_email__ = 'akinava@gmail.com'
__copyright__ = 'Copyright © 2019'
__license__ = 'MIT License'
__version__ = [0, 0]


import asyncio
import signal
import settings
from settings import logger
from connection import NetPool, Connection
import utilit


class UDPHost:
    def __init__(self, handler, protocol):
        logger.info('')
        self.handler = handler
        self.protocol = protocol
        self.net_pool = NetPool()
        self.__set_posix_handler()

    def __set_posix_handler(self):
        signal.signal(signal.SIGUSR1, self.__handle_posix_signal)
        signal.signal(signal.SIGTERM, self.__handle_posix_signal)

    def __handle_posix_signal(self, signum, frame):
        if signum == signal.SIGTERM:
            self.__exit()
        if signum == signal.SIGUSR1:
            self.__config_reload()

    async def create_endpoint(self, remote_addr=None, local_addr=None):
        logger.info('local_addr {}, remote_addr {}'.format(local_addr, remote_addr))
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: self.handler(self.protocol),
            local_addr=local_addr,
            remote_addr=remote_addr)
        connection = Connection(
            local_addr=local_addr,
            remote_addr=remote_addr,
            transport=transport)
        return connection

    async def ping(self):
        logger.info('')
        while self.listener.is_alive():
            self.__ping_connections()
            await asyncio.sleep(settings.peer_ping_time_seconds)

    def __ping_connections(self):
        for connection in self.net_pool.get_all_connections():
            if connection.last_sent_message_is_over_ping_time():
                logger.debug('send ping to {}'.format(connection))
                self.handler(connection=connection, protocol=self.protocol).swarm_ping()

    def __shutdown_connections(self):
        self.net_pool.shutdown()

    def __config_reload(self):
        logger.debug('')
        utilit.import_config()

    def __exit(self):
        logger.info('')
        self.listener.shutdown()
        self.__shutdown_connections()

    def __del__(self):
        logger.debug('')
