from api import create_app
from node import Node

node = Node()
app = create_app(node)
