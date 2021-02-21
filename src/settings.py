# -*- coding: utf-8 -*-
__author__ = 'Akinava'
__author_email__ = 'akinava@gmail.com'
__copyright__ = 'Copyright © 2019'
__license__ = 'MIT License'
__version__ = [0, 0]


import logging
import utilit


config_file = 'config.json'
logging_level = logging.INFO
logging_format = '%(asctime)s : %(levelname)s : %(module)s : %(threadName)s : %(funcName)s : %(message)s'

# host settings
host_min_user_port = 0x400  #  1024
host_max_user_port = 0xbfff # 49151
host_max_port      = 0xffff # 65535

host_min_udp_mtu = 508
host_max_udp_mtu = 1432

socket_buffer_size = 1024

time_check_host_is_alive = 0.1

utilit.setup_settings()
