import datetime
import os
import re
import sys
import threading
import time
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
    elif msg == 'hello':
        return ''
    elif msg == '':
        return ''
    else:
        return 'unknown command'


def alarm(alarm_active):
    while True:
        alarm_active.wait()
        while alarm_active.isSet():
            # FIXME: this isn't very portable
            # paplay can play ogg directly, but it doesn't produce sound when
            # run from a daemon for whatever reason. ffmpeg is therefore used
            # as a transcoder from ogg to wav, and then fed to aplay, which,
            # unlike paplay, produces sound when run from a daemon
            for _ in range(2):
                os.popen('ffmpeg'
                         '   -i /usr/share/sounds/freedesktop/stereo/bell.oga'
                         '   -f wav'
                         '   -'
                         ' | aplay --quiet')
                time.sleep(0.2)
            time.sleep(2)


def main(URL):
    # acquire socket or crash (thereby exiting) if already in use
    zmq_context = zmq.Context.instance()
    socket = zmq_context.socket(zmq.REP)
    socket.bind(URL)

    timers = {}
    expired_timers = []

    alarm_active = threading.Event()
    alarm_thread = threading.Thread(target=alarm,
                                    daemon=True,
                                    args=[alarm_active])
    alarm_thread.start()

    while True:
        # check for requests, pausing every 500ms to check running timers
        if socket.poll(timeout=500):
            # read and process requests
            incoming = socket.recv().decode()
            if incoming in ['exit', 'bye', 'quit']:
                socket.send(b'bye.')
                sys.exit()  # alarm thread seems to continue if using break
            outgoing = dispatch(incoming, timers)

            # prepare a summary of expired timers
            expired_summary = ''
            if expired_timers:
                expired_timers = (
                    [t.finish_time.strftime('%Y-%m-%d %H:%M:%S') +
                     ' | ' + t.description
                     for t in expired_timers])
                expired_summary = '\n'.join(expired_timers) + '\n'
                expired_summary += '---- end of expired timers summary ----\n'
                expired_timers.clear()
                alarm_active.clear()

            # send reply
            socket.send((expired_summary + outgoing).encode())

        # regardless of whether there was a reply, check for expired timers
        expired_timers += check_timers(timers)
        if expired_timers:
            alarm_active.set()


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


def check_timers(timers):
    now = datetime.datetime.now()
    expired = []
    for timer in list(timers.values()):
        if timer.finish_time < now:
            expired.append(timer)
            del timers[timer.identity]
    return expired


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
