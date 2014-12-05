import tempfile
import zipfile

from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse


def send_zipfile(request, files, zipfilename):
    """
    Create a ZIP file on disk and transmit it in chunks of 8KB,
    without loading the whole file into memory. A similar approach can
    be used for large dynamic PDF files.
    """
    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
    for filename, content in files:
        if hasattr(content, 'read'):
            content = content.read()
        elif not isinstance(content, str):
            content = content.encode('utf8')
        archive.writestr(filename, content)
    archive.close()
    length = temp.tell()
    print('Content-Length:', length)
    temp.seek(0)
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename={}'.format(zipfilename)
    response['Content-Length'] = length
    return response
