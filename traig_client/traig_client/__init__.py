import os

from client import TraigClient, TraigStubClient


def get_client() -> TraigClient | TraigStubClient:
    if not hasattr(get_client, 'traig_client'):
        if os.getenv('TRAIG_SESSION', '0') == '1':
            get_client.traig_client = TraigClient()
        else:
            get_client.traig_client = TraigStubClient()

    return get_client.traig_client
