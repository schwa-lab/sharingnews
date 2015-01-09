
import base64
import array

from django.db import models


class IntArrayField(models.Field):
    typecode = 'i'

    def to_python(self, value):
        if value is None:
            return None
        out = array.array(self.typecode)
        out.fromstring(base64.decodestring(value))
        return out

    def get_prep_value(self, value):
        if value is None:
            return None
        return base64.encodestring(value.tostring())
