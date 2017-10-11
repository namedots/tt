"""
Launch daemon (daemon exits if already running) and open a message channel.
This is a dumb front-end to provide access to the daemon.
"""

from terminaltimer.settings import URL
import daemon
import os
import readline  # NOQA importing directly modifies input()
import zmq


def main():
    spawn_daemon()

    ctx = zmq.Context.instance()
    s = ctx.socket(zmq.REQ)
    s.connect(URL)
    s.send('status'.encode())

    while True:
        response = s.recv()
        print(response.decode())
        try:
            msg = input("> ").encode()
        except EOFError:
            break
        s.send(msg)


def spawn_daemon():
    if os.fork() == 0:
        with daemon.DaemonContext():
            from terminaltimer.daemon import main as daemon_main
            daemon_main()
    os.wait()
