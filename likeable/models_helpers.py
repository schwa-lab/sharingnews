
from __future__ import print_function
import sys
import base64
import numpy as np

from django.db import models
from django.utils.six import with_metaclass


class IntArrayField(with_metaclass(models.SubfieldBase, models.Field)):
    def db_type(self, connection=None):
        return 'TEXT';

    def to_python(self, value):
        if hasattr(value, '__array__'):
            return value
        if value is None:
            return None
        try:
            out = np.fromstring(base64.decodestring(value), dtype='>u4')
        except Exception:
            print('!!!!!', repr(value), file=sys.stderr)
            raise
        return out

    def get_prep_value(self, value):
        if hasattr(value, 'tostring'):
            return base64.encodestring(value.tostring())
        else:
            return value
