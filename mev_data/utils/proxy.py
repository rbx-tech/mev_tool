import random
import ipaddress
import secrets
import logging


class ProxyV6:
    def __init__(self):
        self.ip = '173.208.140.106'
        self.port = 22225
        self.password = 'xFkzihNm'
        self.prefix = '2604:4300:f38::'
        self.debug = {}
        self.logger = logging.getLogger()

    def generate_proxies(self):
        bot_id = int.from_bytes(secrets.token_bytes(8), byteorder='big')
        ip = self.gen_random_ip(bot_id)
        proxy = f'socks5h://inf-ip-{ip.replace(":", "%3A")}:{self.password}@{self.ip}:{self.port}'
        return {
            'http': proxy,
            'https': proxy
        }

    def gen_random_ip(self, bot_id, prefix_size=48, sub_prefix_size=64, to_str=True):
        sub_num = 2 ** (sub_prefix_size - prefix_size) - 1
        sub_step = 2 ** (128 - sub_prefix_size)

        random.seed(bot_id)
        idx = random.randint(0, sub_num)

        sub_id = idx
        sub_addr = random.randint(1, sub_step - 1)

        prefix_network = ipaddress.IPv6Network(self.prefix + '/{}'.format(prefix_size), strict=False)
        base_ip = int(prefix_network.network_address)
        new_ip_int = base_ip + sub_id * sub_step + sub_addr
        new_ip = ipaddress.IPv6Address(new_ip_int)
        return str(new_ip) if to_str else new_ip
