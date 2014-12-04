# Utilities for AMQP queues taking article IDs
from __future__ import print_function, absolute_import, division
import sys
import os
import socket
import argparse
import logging
import json
import traceback

import pika
import django
from django.db import reset_queries
from likeable.models import utcnow

django.setup()
logger = None


def json_log(**data):
    data['timestamp'] = utcnow().isoformat()
    logger.info(json.dumps(data))


def enqueue(channel, queue, f):
    i = 0
    for l in f:
        i += 1
        channel.basic_publish(exchange='',
                              routing_key=queue,
                              body=str(int(l)),
                              properties=pika.BasicProperties(
                                  delivery_mode=2,  # make message persistent
                              ))
    json_log(enqueued=i)


def worker(channel, queue, process_cb, args):
    def worker_callback(channel, method, properties, body):
        try:
            process_cb(args, body)
        except Exception:
            json_log(body=body, traceback=traceback.format_exc())
        else:
            channel.basic_ack(delivery_tag=method.delivery_tag)
        reset_queries()  # avoid memory leak

    channel.basic_qos(prefetch_count=10)
    channel.basic_consume(worker_callback, queue=queue)
    print('Waiting for IDs to fetch. To exit press CTRL+C', file=sys.stderr)
    channel.start_consuming()


def main(name, process_cb, argparse_cb=None):
    global logger
    default_log_prefix = os.path.expanduser('~likeable/logs/{0}/'
                                            '{0}-{1}-{2}.log.bz2'
                                            ''.format(name,
                                                      socket.gethostname(),
                                                      os.getpid()))
    ap = argparse.ArgumentParser()
    ap.add_argument('-H', '--host', default='localhost')
    ap.add_argument('--port', default=None)
    ap.add_argument('--queue', default='likeable-id-{}'.format(name))
    ap.add_argument('--log-path', default=default_log_prefix)

    subs = ap.add_subparsers()
    enqueue_ap = subs.add_parser('enqueue')
    enqueue_ap.set_defaults(app='enqueue')
    enqueue_ap.add_argument('-f', '--infile',
                            type=argparse.FileType('r'), default=sys.stdin,
                            help='Path where IDs are listed (default: STDIN)')
    worker_ap = subs.add_parser('worker')
    worker_ap.set_defaults(app='worker')
    count_ap = subs.add_parser('count')
    count_ap.set_defaults(app='count')

    if argparse_cb is not None:
        argparse_cb(ap)
    args = ap.parse_args()

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.TimedRotatingFileHandler(args.log_path,
                                                        when='D',
                                                        encoding='bz2',
                                                        delay=True)
    print('Logging to', args.log_path + '*', file=sys.stderr)
    logger.addHandler(handler)

    conn_params = pika.ConnectionParameters(host=args.host, port=args.port)
    connection = pika.BlockingConnection(conn_params)
    channel = connection.channel()
    queue = channel.queue_declare(queue=args.queue, durable=True, passive=args.app == 'count')
    if args.app == 'worker':
        worker(channel, args.queue, process_cb, args)
    elif args.app == 'enqueue':
        enqueue(channel, args.queue, args.infile)
    elif args.app == 'count':
        print(queue.method.message_count)
    connection.close()
