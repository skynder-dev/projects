"""Optional process-local network evidence: destinations only, never headers or bodies."""
import os
import sys
import time
from pathlib import Path
from .common import write_json


def install_audit(path):
    path = Path(path)
    records = []
    active = False
    def audit(event, args):
        nonlocal active
        if active or event not in {'socket.getaddrinfo', 'socket.connect'}:
            return
        active = True
        try:
            if event == 'socket.getaddrinfo':
                item = {'event': 'dns', 'host': str(args[0]), 'port': args[1]}
            else:
                address = args[1]
                item = {'event': 'connect', 'host': str(address[0]), 'port': address[1]} if isinstance(address, tuple) else {'event': 'local_socket'}
            item['at'] = round(time.time(), 3)
            records.append(item)
            write_json(path, {'scope': 'Python process socket audit only; not OS-wide packet capture',
                              'records': records[-500:], 'record_count': len(records)})
        finally:
            active = False
    sys.addaudithook(audit)
    write_json(path, {'scope': 'Python process socket audit only; not OS-wide packet capture', 'records': [], 'record_count': 0})
