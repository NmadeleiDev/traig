from client import TraigClient


def get_client():
    if not hasattr(get_client, 'traig_client'):
        get_client.traig_client = TraigClient()
    return get_client.traig_client
