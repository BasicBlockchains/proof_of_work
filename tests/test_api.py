'''
Testing the api
'''

from .context import Node, create_app, run_app
import threading


def test_ping():
    n = Node()
    api_thread = threading.Thread(target=run_app, daemon=True, args=(n,))
    api_thread.start()
    n2 = Node()
    local_ip = n.get_local_ip()
    assert n2.ping_node((local_ip, n.assigned_port))
