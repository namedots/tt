"""
Launch daemon (daemon exits if already running) and open a message channel.
This is a dumb front-end to provide access to the daemon.
"""

import daemon
import os
import sys
import zmq

# importing directly modifies input() to behave like a shell's input with
# emacs/vi bindings etc for editing and history
import readline  # NOQA

URL = 'ipc://@TerminalTimer'


def main():
    spawn_daemon()

    # connect to daemon
    ctx = zmq.Context.instance()
    s = ctx.socket(zmq.REQ)
    s.connect(URL)

    # one-off commands through arguments
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        s.send(' '.join(args).encode())
        take_response(s)
        sys.exit()

    # poke the daemon to see if it has something to say or do before the user
    # types anything in the interactive loop
    s.send(b'hello')
    take_response(s)

    # interactive loop
    while True:
        try:
            msg = input("> ").encode()
        except EOFError:
            break
        s.send(msg)
        take_response(s)


def take_response(s):
    response = s.recv()
    response = response.decode()
    if response != '':
        print(response)
        if response == 'bye.':
            sys.exit()


def spawn_daemon():
    # fork and daemonise the child which will run the daemon code
    if os.fork() == 0:
        with daemon.DaemonContext():
            from terminaltimer.daemon import main as daemon_main
            daemon_main(URL)
    os.wait()
