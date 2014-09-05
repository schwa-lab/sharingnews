
from django.db import models


class OpenGraphObject(models.Model):
    # From Facebook's URL lookup
    id = models.PositiveIntegerField(null=False, primary_key=True,
                                     help="Facebook's numeric ID")
    url = models.UrlField(max_length=256)
    fb_updated = models.DateTimeField()
    type = models.CharField(max_length=10)
    title = models.TextField(null=True)
    description = models.TextField(null=True)

    ### From FB id lookup
    fb_created = models.DatetTimeField(null=True)
    # fields include: site_name, image, video, admins, application, data
    # site_name = models.CharField(max_length=30)  # or use foreignkey enum

    # image and video is a bit tricky. could store image information, but may
    # be more focused if we get it from our own scrape. video may be more selective.

    # data includes author, publisher, published_time, modified_time, and
    # section metadata, but is rarely available so should possibly be relegated
    # to a separate Model.

    # fb_author_id = models...
    # fb_author = models.TextField(null=True)

    ### From our extraction
    # scrape_when = models.DateTimeField(help_text='When we last scraped this content')
    #    # do we need another field to indicate our scraping method?
    # headline = models.TextField(null=True)
    # author = models.TextField(null=True)
    # body_html = models.TextField(null=True)  # should this be stored?
    # body_text = models.TextField(null=True)
    # media = models.ManyToMany(MediaItem)
    # comments_data = models.OneToOne(CommentsData)

    # is_error_page = models.BooleanField(null=True)  # from extraction or inference

    ### From readability ??


class FacebookStat(object):
    when = models.DateTimeField()
    # likes = models.PositiveIntegerField()
    # comments = models.PositiveIntegerField()
    share_total = models.PositiveIntegerField()
    page_comments = models.PositiveIntegerField(null=True)


class SpideredUrl(models.Model):
    parent = models.ForeignKey('SpideredUrl', null=True)
    url = models.UrlField(max_length=256)
    ogo = models.ForeignKey(OpenGraphObject)
    when = models.DateTimeField(null=True, help_text='spider time')
