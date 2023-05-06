"""
Author: github: @itchenfei
"""
from urllib.request import Request, urlopen
import logging
import json
import sys
import socket
import configparser
from contextlib import closing
import time
import os

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DDNS')


class CloudflareDDNS:
    """
    Simple cloudflare ddns
    """
    def __init__(self, config_file='config.ini'):
        # if config file not exist, try to find it in the same folder as the script
        real_path = os.path.dirname(sys.executable)
        config_file_full_path = os.path.join(real_path, config_file)  # config file path
        logger.info("Config file path: %s", config_file_full_path)
        if os.path.exists(config_file_full_path) is False:
            logger.info("Config file not found in %s", config_file_full_path)
            script_path = os.path.dirname(os.path.realpath(__file__))
            config_file_full_path = os.path.join(script_path, config_file)
            logger.info("Try new config file path: %s", config_file_full_path)

        # Read config
        config = configparser.ConfigParser()
        config.read(config_file_full_path)
        self.host_name = config.get('Cloudflare', 'host_name')
        self.dns_type = config.get('Cloudflare', 'dns_type')
        self.zone_id = config.get('Cloudflare', 'zone_id')
        self.api_key = 'Bearer ' + config.get('Cloudflare', 'api_key')
        self.url = config.get('Cloudflare', 'url')

    @staticmethod
    def get_latest_ipv6_addr():
        """
        Get the shortest IPv6 address of current machine.
        """
        ipv6_addresses = []
        for family, _, _, _, socket_addr in socket.getaddrinfo(socket.gethostname(), None):
            if family == socket.AF_INET6 and socket_addr[0].startswith('24'):
                ipv6_addresses.append(socket_addr[0])
        if ipv6_addresses:
            shortest_ipv6 = min(ipv6_addresses, key=len)
            logger.info("Current ip is: %s", shortest_ipv6)
            return shortest_ipv6
        logging.error("Fail to get IPv6 address, please check your network connection")
        sys.exit(1)

    def get_domain_ipv6_address(self, timeout=5):
        """
        Get domain IPv6 address use socket, try 10 times if fail.
        """
        logger.info("Get IPv6 address for %s", self.host_name)
        for i in range(1, 11):
            with closing(socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)) as sock:
                sock.settimeout(timeout)
                try:
                    addr_info = socket.getaddrinfo(self.host_name, None, socket.AF_INET6)
                    ipv6_address = addr_info[0][4][0]
                    logger.info("IPv6 address for %s is %s", self.host_name, ipv6_address)
                    return ipv6_address
                except (socket.gaierror, socket.timeout):
                    logger.error("Fail to get IPv6 address for %s, retry %s", self.host_name, i)
                    time.sleep(1)
        logger.error("Fail to get IPv6 address for %s", self.host_name)
        sys.exit(1)

    @staticmethod
    def build_request(url, headers, method='GET', data=None):
        """
        Build request object for urlopen
        """
        req = Request(
            url,
            headers=headers,
            method=method,
            data=data
        )
        return req

    def make_request(self, url, headers, method='GET', data=None):
        """
        Make request to cloudflare API using urllib. Return json data.
        """
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        elif data is not None:
            raise TypeError("Data must be a dict")
        req = self.build_request(url, headers, method, data)
        content = urlopen(req, timeout=3000).read().decode()
        return json.loads(content)

    def get_dns_id_and_ip(self):
        """
        Get DNS ID and IP from cloudflare API.
        """
        # Build API
        list_dns_api = f"{self.url}/{self.zone_id}/dns_records?type={self.dns_type}&name={self.host_name}"
        logger.info("List DNS API: %s", list_dns_api)

        # Build request
        auth_headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        json_data = self.make_request(list_dns_api, auth_headers, method='GET')

        # Get DNS ID
        logger.info(json_data)
        result = json_data['result'][0]
        dns_id = result.get('id')
        dns_content = result.get('content')
        logger.info("DNS ID: %s, DNS IP: %s", dns_id, dns_content)
        if not dns_id:
            logger.error("Fail to get DNS ID")
            sys.exit(1)
        return dns_id, dns_content

    def update_dns(self, current_ip, dns_id):
        """
        Update DNS record using cloudflare API if IP is changed.
        """
        update_dns_api = f"{self.url}/{self.zone_id}/dns_records/{dns_id}"
        auth_headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        data = {
            'type': self.dns_type,
            'name': self.host_name,
            'content': current_ip,
            'proxy': 'false'
        }
        logger.info("Update DNS API: %s", update_dns_api)
        logger.info("Update DNS data: %s", data)
        json_data = self.make_request(update_dns_api, auth_headers, method='PUT', data=data)

        result = json_data['result']
        logger.info("result: %s", result)
        dns_name = result.get('name')
        dns_ip = result.get('content')
        if current_ip != dns_ip:
            logger.error("Fail to update DNS")
            sys.exit(1)
        logger.info("dns updated: %s: %s", dns_name, dns_ip)

    def run(self):
        """
        All in one
        """
        # Get current ip and domain ip
        current_ip = self.get_latest_ipv6_addr()

        # Get DNS ID
        dns_id, dns_ip = self.get_dns_id_and_ip()

        if dns_ip == current_ip:
            logger.info("IP is not changed, no need to update")
            sys.exit(0)

        # Update DNS
        self.update_dns(current_ip, dns_id)


if __name__ == "__main__":
    CONFIG_FILE = "config.ini"
    cf_ddns = CloudflareDDNS(CONFIG_FILE)
    cf_ddns.run()
