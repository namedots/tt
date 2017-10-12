import datetime
import re
import uuid
import zmq


def dispatch(msg, timers):
    # TODO: possibly register with decorator instead
    # don't know what requirements are, probably best to just wait until more
    # functionally complete or just risk having to undo it
    if msg[:3] == 'add':
        return add_timer(msg, timers)
    elif msg[:3] == 'del':
        return remove_timer(msg, timers)
    elif msg == 'list':
        return list_timers(timers)
    else:
        return 'unknown command'


def main(URL):
    # acquire socket or crash if already in use
    zmq_context = zmq.Context.instance()
    socket = zmq_context.socket(zmq.REP)
    socket.bind(URL)

    timers = {}

    # main loop
    #   - Check incoming messages on socket
    #   - Check running alarms
    while True:
        if socket.poll(timeout=500):
            incoming = socket.recv().decode()
            outgoing = dispatch(incoming, timers)
            socket.send(outgoing.encode())
        check_timers()


def remove_timer(msg, timers):
    args = msg.split(' ')
    if len(args) != 2:
        return f'bad command (this is a bug):\n{msg}'
    command, identity = args
    if identity in timers:
        del timers[identity]
        return 'removed'
    return 'that timer doesn\'t exist.'


def list_timers(timers):
    result = []
    for identity, timer in timers.items():
        result.append([identity, timer.description, timer.finish_time])
    return str(result)


def parse_time_description(finish):
    time_units = {
        'w': datetime.timedelta(weeks=1),
        'd': datetime.timedelta(days=1),
        'h': datetime.timedelta(hours=1),
        'm': datetime.timedelta(minutes=1),
        's': datetime.timedelta(seconds=1),
    }
    if re.match(r'(?i)^(\d+(?:y|d|w|h|m|s))+$', finish):
        result = datetime.datetime.now()
        split_finish = re.findall(r'(?i)(\d+)(y|d|w|h|m|s)', finish)
        for amount, unit in split_finish:
            amount = int(amount)
            print(f'{amount!r}   {time_units[unit]!r}')
            result += amount * time_units[unit]
        return result
    # TODO: add absolute time i.e. 12:37
    return None


def add_timer(msg, timers):
    # todo parse duration/finish
    args = msg.split(' ')
    if len(args) < 2:
        return f'expected at least two arguments'
    command, finish, *description = args
    description = ' '.join(description)
    finish_time = parse_time_description(finish)
    if finish_time is None:
        return 'bad time format'
    timer = Timer(description, finish_time)
    timers[timer.identity] = timer
    return 'added'


def identity_dispenser():
    # uuid1 doesn't guarantee no collisions when multiple are generated at the
    # same time on the same machine, and while uuid1 supports 100ns time
    # resolution steps, the time used might not be as fine-grained.
    # therefore, wait until the time has changed before generating next one.
    # obviously this still isn't multithread/multiprocess safe.
    if not hasattr(identity_dispenser, 'previous'):
        identity_dispenser.previous = None
    while datetime.datetime.now() == identity_dispenser.previous:
        pass
    identity = str(uuid.uuid1())
    identity_dispenser.previous = datetime.datetime.now()
    return identity


class Timer:
    # other threads shouldn't interact with this, they just need to be able to
    # add/list/remove
    def __init__(self, description, finish_time):
        self.description = description
        self.finish_time = finish_time
        self.identity = identity_dispenser()


def check_timers():
    print('check_timers() invoked')
    # raise NotImplementedError()


def load():
    # run on startup
    raise NotImplementedError()


def save():
    # run on each change
    raise NotImplementedError()


if __name__ == '__main__':
    # FIXME get the url from somewhere other than a circular import
    from terminaltimer.commandline import URL
    main(URL)
