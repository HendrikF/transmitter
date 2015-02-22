from transmitter.Endpoint import Endpoint

class Server(Endpoint):
    isServer = True

class Client(Endpoint):
    isClient = True
