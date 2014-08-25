# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class LikeableItem(scrapy.Item):
    url = scrapy.Field()
    headline = scrapy.Field()
    author = scrapy.Field()
    when = scrapy.Field()  # ISO
    writeoff = scrapy.Field()
    body_html = scrapy.Field()
    multimedia = scrapy.Field()
