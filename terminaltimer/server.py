import daemon
import datetime
import json
import os
import re
import threading
import time
import uuid
import zmq


def dispatch(msg, timers):
    # TODO: possibly register with decorator instead
    # don't know what requirements are, probably best to just wait until more
    # functionally complete or just risk having to undo it
    if msg:
        cmd, *args = msg.split()
    else:
        cmd = ''
        args = []

    if cmd == 'add':
        return add_timer(args, timers)
    elif cmd == 'describe':
        return describe_timer(args, timers)
    elif cmd == 'remove':
        return remove_timer(args, timers)
    elif cmd == 'list':
        return list_timers(timers)
    elif cmd == '':
        return ''
    else:
        return f'{cmd}: unknown command'


def alarm(alarm_active):
    while True:
        alarm_active.wait()
        while alarm_active.isSet():
            # FIXME: this isn't very portable
            # paplay can play ogg directly, but it doesn't produce sound when
            # run from a daemon for whatever reason. ffmpeg is therefore used
            # as a transcoder from ogg to wav, and then fed to aplay, which,
            # unlike paplay, produces sound when run from a daemon
            # FIXME: send text output to /dev/null
            for _ in range(2):
                os.popen('ffmpeg'
                         '   -i /usr/share/sounds/freedesktop/stereo/bell.oga'
                         '   -f wav'
                         '   -'
                         '   2> /dev/null'
                         ' | aplay --quiet 2> /dev/null')
                time.sleep(0.2)
            time.sleep(2)


def check_expired(alarm_active, expired_timers):
    expired_summary = ''
    if expired_timers:
        expired_summary = '\n'.join((
            [t.finish_time.strftime('%F %T') +
             ' : ' + t.description
             for t in expired_timers])) + '\n'
        expired_summary += '---- end of expired timers summary ----'
        expired_timers.clear()
        alarm_active.clear()
    return expired_summary


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
            print('client>', incoming)
            if incoming in ['exit', 'bye', 'quit']:
                socket.send(b'bye.')
                alarm_active.clear()
                break
            if incoming == '':
                outgoing = check_expired(alarm_active, expired_timers)
            else:
                outgoing = dispatch(incoming, timers)
            print('server>', outgoing)

            # send reply
            socket.send(outgoing.encode())

        # regardless of whether there was a reply, check for expired timers
        expired_timers += check_timers(timers)
        if expired_timers:
            alarm_active.set()


def describe_timer(args, timers):
    if len(args) < 1:
        return 'expected at least 1 argument'
    description = ' '.join(args[1:])
    identity = args[0]
    if identity in timers:
        timers[identity].description = description
        return 'updated'
    return 'that timer doesn\'t exist.'


def remove_timer(args, timers):
    if len(args) != 1:
        return 'expected 1 argument'
    identity = args[0]
    if identity in timers:
        del timers[identity]
        return 'removed'
    return 'that timer doesn\'t exist.'


def list_timers(timers):
    result = []
    for identity, timer in timers.items():
        result.append([identity,
                       timer.description,
                       timer.finish_time.timestamp()])
    return json.dumps(result)


def parse_time_description(finish):
    time_units = {
        'w': datetime.timedelta(weeks=1),
        'd': datetime.timedelta(days=1),
        'h': datetime.timedelta(hours=1),
        'm': datetime.timedelta(minutes=1),
        's': datetime.timedelta(seconds=1),
    }
    if re.match(r'(?i)^(\d+(?:y|d|w|h|m|s))+$', finish):
        duration = datetime.timedelta(0)
        split_finish = re.findall(r'(?i)(\d+)(y|d|w|h|m|s)', finish)
        for amount, unit in split_finish:
            amount = int(amount)
            duration += amount * time_units[unit]
        finish_time = datetime.datetime.now() + duration
        return (duration, finish_time)
    # TODO: add absolute time i.e. 12:37
    return None


def add_timer(args, timers):
    if len(args) < 1:
        return f'expected at least one argument'
    finish, *description = args
    description = ' '.join(description)
    duration, finish_time = parse_time_description(finish)
    if finish_time is None:
        return 'bad time format'
    timer = Timer(description, finish_time)
    timers[timer.identity] = timer

    if description:
        description += '\n'
    return (
        f'{description}'
        f'duration: {duration}\n'
        f'finishes at: {finish_time}'
    )


class Timer:
    def __init__(self, description, finish_time):
        self.description = description
        self.finish_time = finish_time
        # uuid.uuid1 ensures that its timestamp is increased by at least 1 when
        # called by single thread/process
        self.identity = str(uuid.uuid1())


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


def spawn_daemon(URL):
    if os.fork() == 0:
        with daemon.DaemonContext():
            main(URL)
    os.wait()


if __name__ == '__main__':
    # FIXME get the url from somewhere other than a circular import
    from terminaltimer.client import URL
    main(URL)
