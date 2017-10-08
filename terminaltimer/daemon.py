import zmq
from .settings import URL


def main():
    print('daemon:main says hi')
    ctx = zmq.Context.instance()
    s = ctx.socket(zmq.REP)
    try:
        s.bind(URL)
    except zmq.error.ZMQError:
        print(f'Socket {URL} seems to already be in use, '
              'not starting another daemon.')
        return 1

    count = 0
    while True:
        message = s.recv()
        count += 1
        s.send(f'Hello. Number of messages received: {count}'.encode())
