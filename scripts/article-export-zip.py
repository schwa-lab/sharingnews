#!/usr/bin/env python

import sys
import argparse

import django

from likeable.export import gen_export_folders, build_zip
from likeable.models import Article

django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('--id-file', default=sys.stdin, type=argparse.FileType('r'))
ap.add_argument('--zip-file', default=sys.stdout, type=argparse.FileType('wb'))
ap.add_argument('--ascii', action='store_true', default=False)
ap.add_argument('--include-id', action='store_true', default=False, help='Include Facebook ID in filename')
# TODO: handle non-existent
args = ap.parse_args()


file_gen = gen_export_folders([((int(l),) for l in args.id_file)], Article.objects.all(), measure_names=[],
                              include_id=args.include_id, ascii=args.ascii)
build_zip(args.zip_file, file_gen)
