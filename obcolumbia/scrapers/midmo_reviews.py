#   Copyright 2011 OpenPlans and contributors
#
#   This file is part of OpenBlock
#
#   OpenBlock is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   OpenBlock is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with OpenBlock.  If not, see <http://www.gnu.org/licenses/>.
#

"""

EverythingMidMo reviews scraper.
http://www.everythingmidmo.com/

"""

from django.contrib.gis.geos import Point
from ebdata.retrieval.retrievers import PageNotFoundError
from ebdata.retrieval.scrapers.list_detail import SkipRecord, StopScraping
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebdata.textmining.treeutils import text_from_html
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import datetime

class MidMoReviewsScraper(NewsItemListDetailScraper):

    schema_slugs = ('midmo-reviews',)
    has_detail = True
    logname = 'midmo_reviews'

    url = 'http://www.everythingmidmo.com/marketplace/reviews/'

    base_url = 'http://www.everythingmidmo.com'

    def __init__(self, options):
        super(MidMoReviewsScraper, self).__init__()
        if options.days == -1:
            start_date = datetime.date(1970, 1, 1)
        else:
            start_date = datetime.date.today() - datetime.timedelta(days=options.days)
        self.start_date = start_date

    def list_pages(self):
        for page in xrange(1, 999):
            url = '%s?page=%s' % (self.url, page)
            try:
                yield self.fetch_data(url)
            except PageNotFoundError:
                break

    def existing_record(self, record):
        url = record['url']
        qs = NewsItem.objects.filter(schema__id=self.schema.id, url=url)
        try:
            return qs[0]
        except IndexError:
            return None

    def parse_list(self, page):
        """
        yields a dictionary of data for each record on the page.
        See list_detail.py.
        """
        tree = self.parse_html(page)
        for review in tree.findall("//*[@typeof='v:Review']"):
            url = review.find(".//a[@class='permalink']").attrib['href']
            if url.startswith('/'):
                url = self.base_url + url
            rating = review.find(".//*[@property='v:rating']").text
            rating = rating.split(':')[-1].strip()
            reviewer = review.find(".//*[@property='v:reviewer']").text
            reviewed = review.find(".//*[@property='v:itemreviewed']").text
            description = review.find(".//*[@property='v:description']/p")
            description = getattr(description, 'text', '')
            if description:
                description = text_from_html(description)
            else:
                self.logger.info("Blank description, skipping...")
                continue
            date = review.find(".//*[@property='v:dtreviewed']").text
            date = parse_date(date, '%B %d, %Y')
            if date < self.start_date:
                raise StopScraping("Reached cutoff date %s" % self.start_date)
            data = {
                'url': url,
                'title': reviewed,
                'description': description,
                'item_date': date,
                '_attributes': {
                    'rating': rating,
                    'reviewer': reviewer,
                    'business_name': reviewed,
                    },
                }
            yield data

    def detail_required(self, list_record, old_record):
        """
        Given a cleaned list record and the old record (which might be None),
        returns True if the scraper should download the detail page for this
        record.

        If has_detail is True, subclasses must override this.
        """
        if old_record is None:
            return True
        return False

    def get_detail(self, list_record):
        url = list_record['url']
        return self.fetch_data(url)

    def parse_detail(self, page, list_record):
        record = list_record.copy()
        tree = self.parse_html(page)
        footer = tree.find(".//*[@class='review_footer']")
        for link in footer.findall(".//a"):
            if link.text.lower().count('comments'):
                record['_attributes']['comment_count'] = link.text.lower().split('comments')[0].strip()
                break

        # Address is on this page, but not lat/lon, and address is maybe a bit too raw.
        # There's a separate page for the reviewed business.
        item_link = footer.find(".//*[@class='reviewed_item']//a").attrib['href']
        if item_link.startswith('/'):
            item_link = self.base_url + item_link
        item_html = self.fetch_data(item_link)
        item_tree = self.parse_html(item_html)
        lat = item_tree.find(".//*[@property='og:latitude']")
        lat = lat.attrib['content'] if (lat is not None) else None
        lon = item_tree.find(".//*[@property='og:longitude']")
        lon = lon.attrib['content'] if (lon is not None) else None
        try:
            record['location'] = Point(float(lon), float(lat))
        except:
            raise SkipRecord("Invalid coordinates %s, %s" % (lat, lon))

        address = item_tree.find(".//*[@property='og:street-address']").attrib['content']
        record['location_name'] = address
        business_type = item_tree.find(".//*[@property='og:type']").attrib['content']
        record['_attributes']['business_type'] = business_type
        business_type = item_tree.find(".//*[@property='og:type']").attrib['content']
        return record

    def clean_detail_record(self, record):
        attr = record['_attributes']
        attr['business_type'] = self.get_or_create_lookup(
            'business_type', attr['business_type'], attr['business_type']).id
        attr['rating'] = self.get_or_create_lookup(
            'rating', attr['rating'], attr['rating']).id
        return record

    def save(self, old_record, list_record, detail_record):
        if detail_record is None:
            self.logger.info("Skipping %s, not bothering to update without detail" % list_record['url'])
            return
        kwargs = detail_record.copy()
        attributes = kwargs.pop('_attributes')
        self.create_or_update(old_record, attributes, **kwargs)


def main(argv=None):
    import sys
    from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
    from optparse import OptionParser
    if argv is None:
        argv = sys.argv[1:]
    optparser = OptionParser()
    optparser.add_option(
        '-d', '--days',
        help="How many days ago to start searching. Default is 10. -1 means load everything.",
        action="store", default=10, type="int",
        )
    add_verbosity_options(optparser)
    opts, args = optparser.parse_args(argv)
    scraper = MidMoReviewsScraper(options=opts)
    setup_logging_from_opts(opts, scraper.logger)
    scraper.update()

if __name__ == "__main__":
    main()
