# -*- coding: utf-8 -*-
"""

http://www.latimes.com/local/lanow/la-me-ln-wildfire-yosemite-evacuation-orders-20140819-story.html

Notion of SHARELINES

"""
import scrapy
from ..items import LikeableItem


class LatimesSpider(scrapy.Spider):
    name = "latimes"
    allowed_domains = ["latimes.com"]
    start_urls = (
        'http://www.latimes.com/',
    )

    # http://www.latimes.com/local/lanow/la-me-ln-wildfire-yosemite-evacuation-orders-20140819-story.html

    def parse(self, response):
        item = LikeableItem()
        author = response.css('.trb_bylines_name_author::text').extract()[0].title()
        if author.startswith('By '):
            author = author[3:]
        item['author'] = author
        item['when'] = response.css('.trb_article_dateline_time::attr(datetime)').extract()[0]
        item['body_html'] = response.css('.trb_article_page')  # TODO: strip Follow, copyright from end of body
        # NOTE: body_html misses leading video
        item['headline'] = response.css('h1.trb_article_title_text::text')  # or 'h1[itemprop="headline"]'
        # NOTE: fb_title, og:title may be better headlines as far as this goes.
        # TODO: multimedia
        # Comments by first retrieving content_id from:
        # e.g. https://api.viafoura.com/v2/?callback=jQuery19107462634148541838_1408888826774&json={%22site%22:%22www.latimes.com%22,%22requests%22:{%223%22:{%22path%22:%22/nation/la-na-ferguson-theater-20140823-story.html%22,%22verb%22:%22post%22,%22route%22:%22/pages%22}},%22session%22:%22lmv3l3nikou40f206jui1udep5%22}
        # then comments from
        # e.g. https://api.viafoura.com/v2/?json={"site":"www.latimes.com","requests":{"5":{"limit":10,"sort":"newest","verb":"get","route":"/pages/<CONTENT_ID>/threads"}},"session":"https://api.viafoura.com/v2/?json={"site":"www.latimes.com","requests":{"5":{"limit":10,"sort":"newest","verb":"get","route":"/pages/4453500000467/threads"}},"session":"lmv3l3nikou40f206jui1udep5"}"}
