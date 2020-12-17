# `tt` - terminal timer

works for me AKA it's a non-portable house of cards

```
$ date
Thu Dec 17 01:03:08 AM CET 2020
$ tt add 15m water the dog
water the dog
duration: 0:15:00
finishes at: 2020-12-17 01:18:08
$ tt ls
1) water the dog
2020-12-17 01:18:08   (0:14:07.043797)
$ tt
1) water the dog
2020-12-17 01:18:08   (0:13:55.848844)
> rm 1
removed
```

I have no clue how to play sounds from a terminal. It does this:
<br>(actually, not even a terminal, because it runs as a daemon)
```
$ ffmpeg \
    -i /usr/share/sounds/freedesktop/stereo/bell.oga \
    -f wav \
    - \
    2> /dev/null \
    | aplay -f cd --quiet 2> /dev/null
```

rough overview:

a client script (`tt`) is invoked from the terminal
<br>the client starts a daemon if it is not already running
<br>the client sends the command to the daemon
<br>the client exits
<br>the daemon sounds the alarm when a timer reaches 0
<br>running the client while an alarm is sounding turns the alarm off

the client and daemon talk through zmq (tbh http probably makes more sense)

there is no persistence, alarms are held in memory by the daemon so if it
exits for any reason they're lost
