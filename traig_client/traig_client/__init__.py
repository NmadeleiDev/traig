from client import _TraigClient


def get_client() -> _TraigClient:
    if not hasattr(get_client, 'traig_client'):
        get_client.traig_client = _TraigClient()
    return get_client.traig_client
