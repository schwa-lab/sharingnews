#!/usr/bin/env python

import sys
import argparse

from unidecode import unidecode  # may be too aggressive; can use unicodedata.normalise('NFKD'
import django

from likeable.export import gen_export_folders, build_zip
from likeable.models import Article

django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('--id-file', default=sys.stdin, type=argparse.FileType('r'))
ap.add_argument('--zip-file', default=sys.stdout, type=argparse.FileType('wb'))
ap.add_argument('--ascii', action='store_true', default=False)
# TODO: handle non-existent
args = ap.parse_args()

if args.ascii:
    encode = unidecode
else:
    def encode(s):
        return s.encode('utf-8')


file_gen = gen_export_folders([((int(l),) for l in args.id_file)], Article.objects.all(), measure_names=[])
build_zip(args.zip_file, file_gen)
