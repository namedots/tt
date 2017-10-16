from . import server
import datetime
import functools
import inspect
import json
import sys
import zmq

# importing directly modifies input() to behave like a shell's input with
# emacs/vi bindings etc for editing and history
import readline  # NOQA

URL = 'ipc://@TerminalTimer'
COMMANDS = {}


def command(command_name):
    def decorator(f):
        num_args = len(inspect.getargspec(f).args) - 1
        has_varargs = inspect.getargspec(f).varargs is not None

        @functools.wraps(f)
        def wrapper(socket, *args):
            if not has_varargs and len(args) != num_args:
                print(f'{command_name} expects {num_args} arguments.')
                return
            f(socket, *args)

        COMMANDS[command_name] = wrapper
        return wrapper
    return decorator


@command('help')
@command('?')
def show_help(socket):
    output = """
    list
    add 3d6h5m2s description of timer goes here
    del <TIMERNUMBER>
    describe <TIMERNUMBER> new description goes here
    quit
    """
    output = '\n'.join(map(str.strip, output.strip().split('\n')))
    print(output)


@command('list')
@command('ls')
@command('show')
def list_timers(socket):
    socket.send(b'list')
    response = socket.recv()
    data = json.loads(response)
    output = []
    list_timers.remember = remember = {}
    for n, [identity, description, finish_time] in enumerate(data, start=1):
        finish_time = datetime.datetime.fromtimestamp(finish_time)
        finish_str = finish_time.strftime('%F %T')
        duration = finish_time - datetime.datetime.now()
        duration_str = str(duration)
        remember[str(n)] = identity
        output.append(f'{n}) {description}\n'
                      f'{finish_str}   remaining: {duration_str}')
    if output:
        print('\n\n'.join(output))


@command('describe')
@command('desc')
def describe(socket, which_timer, *description):
    description = ' '.join(description)
    identity = get_identity(which_timer)
    if not identity:
        return
    socket.send(f'describe {identity} {description}'.encode())
    response = socket.recv().decode()
    print(response)


@command('del')
@command('remove')
def remove_timer(socket, which_timer):
    identity = get_identity(which_timer)
    if not identity:
        return
    socket.send(f'remove {identity}'.encode())
    response = socket.recv().decode()
    print(response)


def get_identity(which_timer):
    if not hasattr(list_timers, 'remember'):
        print('I don\'t know of any timers yet, use the list command first.')
        return None
    remember = list_timers.remember
    if which_timer not in remember:
        print('I\'m not aware of that timer.')
        return None
    return remember[which_timer]


def main():
    server.spawn_daemon(URL)

    # connect to daemon
    ctx = zmq.Context.instance()
    socket = ctx.socket(zmq.REQ)
    socket.connect(URL)

    # one-off commands through arguments
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        socket.send(' '.join(args).encode())
        take_response(socket)
        sys.exit()

    # poke the daemon to see if it has something to say or do before the user
    # types anything in the interactive loop
    socket.send(b'')
    take_response(socket)

    # interactive loop
    while True:
        try:
            msg = input("> ")
        except EOFError:
            break

        if msg:
            cmd, *args = msg.split()
        else:
            cmd = ''
            args = []
        if cmd in COMMANDS:
            args = msg.split()[1:]
            handler = COMMANDS[cmd]
            handler(socket, *args)
        else:
            socket.send(msg.encode())
            take_response(socket)


def take_response(s):
    response = s.recv()
    response = response.decode()
    if response != '':
        print(response)
        if response == 'bye.':
            sys.exit()
