'''
Methods to translate current time into seconds from EPOCH
'''

import datetime


def utc_to_seconds():
    date_string = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    date_object = datetime.datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S%z')
    return int(date_object.timestamp())


def seconds_to_utc(seconds: int):
    date_object = datetime.datetime.utcfromtimestamp(seconds)
    return date_object.isoformat()


def utc_timestamp():
    return seconds_to_utc(utc_to_seconds())
