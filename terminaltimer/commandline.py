"""
Launch daemon (daemon exits if already running) and open a message channel.
This is a dumb front-end to provide access to the daemon.
"""

import daemon
import os
import zmq

# importing directly modifies input() to behave like a shell's input with
# emacs/vi bindings etc for editing and history
import readline  # NOQA

URL = 'ipc://@TerminalTimer'


def main():
    spawn_daemon()

    ctx = zmq.Context.instance()
    s = ctx.socket(zmq.REQ)
    s.connect(URL)

    msg = ''
    s.send(b'hello')  # it's only polite.

    while True:
        response = s.recv()
        response = response.decode()
        if response != '':
            print(response)
        if response == 'bye.':
            break

        try:
            msg = input("> ").encode()
        except EOFError:
            break
        s.send(msg)

def spawn_daemon():
    if os.fork() == 0:
        with daemon.DaemonContext():
            from terminaltimer.daemon import main as daemon_main
            daemon_main(URL)
    os.wait()
