# -*- coding: utf-8 -*-
"""

Huffpost: http://www.huffingtonpost.com/2014/08/17/mark-bustos-homeless-haircuts_n_5678454.html
Author:
- readability extracted but not clean
- a[rel="author"]

Date:
- extracted, normed; time removed
- $('.times > .posted > time').attr('datetime') inclues ISO time

Body:
- #mainentrycontent
- includes additional "follow us" postscripts
- many inline instagram iframes

Writeoff:
- seems to be automatic doc prefix in meta[name="description"]; first para would be better in this case.

More metadata in headers.

(I wonder if Facebook uses rel="alternate")

"""
import scrapy
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor

from ..items import LikeableItem


class HuffpostSpider(scrapy.Spider):
    name = "huffpost"
    allowed_domains = ["huffingtonpost.com"]
    start_urls = (
        'http://www.huffpost.com/',
    )

    # http://www.huffingtonpost.com/2014/08/17/mark-bustos-homeless-haircuts_n_5678454.html
    rules = [Rule(LinkExtractor(allow=[r'/\d{4}/\d{2}/\d{2}/.*\.html']),
                  'parse_article')]

    def parse(self, response):
        item = LikeableItem()
        item['url'] = response.url
        item['author'] = response.css('a[rel="author"]::text').extract()[0].strip()
        item['headline'] = response.css('.entry header h1 ::text').extract()[0].strip()
        item['when'] = response.css('.times > .posted > time ::attr(datetime)').extract()[0]
        item['body_html'] = response.css('#mainentrycontent').re('(?s)(?<=<!-- Entry Text -->).*')[0] # TODO: strip "Follow us" from end of body
        # TODO: multimedia/comments
        return item
