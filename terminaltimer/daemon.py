import datetime
import uuid
import zmq


def dispatch(msg, timers):
    if msg == 'add':
        finish = datetime.datetime.now() + datetime.timedelta(hours=1)
        add_timer('dummy timer', finish, timers)
        return 'added'
    elif msg[:3] == 'del':
        remove_timer(msg[4:], timers)
        return 'removed'
    elif msg == 'list':
        return list_timers(timers)
    else:
        return 'unknown command'


def main(URL):
    # acquire socket or crash if already in use
    ctx = zmq.Context.instance()
    s = ctx.socket(zmq.REP)
    s.bind(URL)

    timers = {}

    # main loop
    #   - Check incoming messages on socket
    #   - Check running alarms
    while True:
        if s.poll(timeout=500):
            incoming = s.recv().decode()
            outgoing = dispatch(incoming, timers)
            s.send(outgoing.encode())
        check_timers()


def remove_timer(identity, timers):
    del timers[identity]


def list_timers(timers):
    result = []
    for identity, timer in timers.items():
        result.append([identity, timer.description, timer.finish_time])
    return str(result)


def add_timer(description, finish_time, timers):
    timer = Timer(description, finish_time)
    timers[timer.identity] = timer


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
