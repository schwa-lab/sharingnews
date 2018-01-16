import tempfile

from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse

from .export import build_zip


def send_zipfile(request, files, zipfilename):
    """
    Create a ZIP file on disk and transmit it in chunks of 8KB,
    without loading the whole file into memory. A similar approach can
    be used for large dynamic PDF files.
    """
    temp = tempfile.TemporaryFile()
    build_zip(temp, files)
    length = temp.tell()
    print('Content-Length:', length)
    temp.seek(0)
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename={}'.format(zipfilename)
    response['Content-Length'] = length
    return response
