from . import server
import datetime
import functools
import inspect
import json
import sys
import zmq

# importing directly modifies input() to behave like a shell's input with
# emacs/vi bindings etc for editing and history
# TODO: it may be possible to have tab-completion for commands
import readline  # NOQA

URL = 'ipc://@TerminalTimer'
if hasattr(sys, 'real_prefix'):
    URL = 'ipc://@TerminalTimerVEnv'

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


@command('?')
@command('help')
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
    # sort by finish time, with earliest finish time showing up at the bottom
    data.sort(key=lambda x: x[2], reverse=True)
    output = []
    list_timers.remember = remember = {}
    for n, [identity, description, finish_time] in enumerate(data, start=1):
        remember[str(n)] = identity
        finish_time = datetime.datetime.fromtimestamp(finish_time)
        finish_str = finish_time.strftime('%F %T')
        duration = finish_time - datetime.datetime.now()
        duration_str = str(duration)
        output.append(f'{n}) {description}\n'
                      f'{finish_str}   ({duration_str})')
    if output:
        print('\n'.join(output))


@command('desc')
@command('describe')
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
@command('rm')
def remove_timer(socket, which_timer):
    # TODO: strategy for removing multiple timers at once
    # by enumerated number? by description? by ranges? by expiry?
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
    # TODO option for starting daemon and exiting
    # or just run it as: echo | terminaltimer
    # (feed it empty input, causing it to exit at EOF)

    # connect to daemon
    ctx = zmq.Context.instance()
    socket = ctx.socket(zmq.REQ)
    socket.connect(URL)

    # poke the daemon to see if it has something to say or do before the user
    # types anything in the interactive loop
    socket.send(b'')
    take_response(socket)

    # interactive loop
    keep_running = True
    while keep_running:
        # one-off commands through arguments
        if len(sys.argv) > 1:
            user_input = ' '.join(sys.argv[1:])
            keep_running = False
        else:
            try:
                user_input = input("> ")
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print('^C')
                continue

        if user_input:
            cmd, *args = user_input.split()
        else:
            cmd = ''
            args = []
        if cmd in COMMANDS:
            args = user_input.split()[1:]
            handler = COMMANDS[cmd]
            handler(socket, *args)
        else:
            socket.send(user_input.encode())
            take_response(socket)


def take_response(s):
    response = s.recv()
    response = response.decode()
    if response == 'bye.':
        print('daemon is exiting (alarms will not go off)')
        sys.exit()
    elif response != '':
        print(response)
