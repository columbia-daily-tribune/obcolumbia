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

EverythingMidMo coupons scraper.
http://www.everythingmidmo.com/

"""

from django.contrib.gis.geos import Point
from ebdata.retrieval.scrapers.list_detail import RssListDetailScraper
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebdata.textmining.treeutils import text_from_html
from ebpub.db.models import NewsItem
from ebpub.geocoder.base import GeocodingException
from ebpub.geocoder.parser.parsing import ParsingError
from ebpub.utils.dates import parse_date
import datetime
import lxml.html


class MidMoCouponsScraper(RssListDetailScraper, NewsItemListDetailScraper):

    schema_slugs = ('midmo-coupons',)
    has_detail = True
    logname = 'midmo_coupons'
    timeout = 45

    # Can't find a way to specify number of items, or dates.
    # Is this *everything* current?
    url = 'http://www.everythingmidmo.com/marketplace/feeds/ads-for-market/'

    def list_pages(self):
        yield self.fetch_data(self.url)

    def existing_record(self, record):
        url = record['link']
        qs = NewsItem.objects.filter(schema__id=self.schema.id, url=url)
        try:
            qs[0]
            self.logger.debug("Already have %s" % url)
            return qs[0]
        except IndexError:
            self.logger.debug("New %s" % url)
            return None

    def detail_required(self, list_record, old_record):
        """
        Given a cleaned list record and the old record (which might be None),
        returns True if the scraper should download the detail page for this
        record.

        If has_detail is True, subclasses must override this.
        """
        return True

    def parse_detail(self, page, list_record):
        record = list_record.copy()
        tree = lxml.html.fromstring(page)
        try:
            detail_section = tree.cssselect('.photo .image')[0]
            record['description'] = detail_section.cssselect('p')[0].text
        except IndexError:
            raise SkipRecord("detail page unparseable")

        date_text = detail_section.cssselect('p.date')[0].text
        # Quirky date format. Are there any other misspelled month abbreviations?
        date_text = date_text.replace('Sept. ', 'Sep. ')
        try:
            starts, expires = date_text.split('Expires ')
            expires = parse_date(expires.strip(), '%b. %d, %Y')
            starts = parse_date(starts.strip(), 'Starts %b. %d, %Y')
        except ValueError:
            starts = expires = None

        record['_attributes'] = {'expires': expires, 'starts': starts}

        business_name = tree.cssselect(
            'div.content h1.name a')[0].text.strip()

        business_name = self.get_or_create_lookup('business_name', business_name,
                                                  business_name)
        record['_attributes']['business_name'] = business_name.id

        address = tree.cssselect('h2.address')[0].text.strip()
        if not address:
            address = tree.cssselect('h2.address a')[0].tail.strip()
        record['location_name'] = address

        # Try to get the latitude / longitude out of the page.
        # Unfortunately it's only there in some javascript.
        import re
        lat_re = re.compile(r"latitude.*?(-?\d+\.\d+)")
        lon_re = re.compile(r"longitude.*?(-?\d+\.\d+)")

        lat, lon = None, None
        for script in tree.cssselect('script'):
            if not script.text:
                continue
            found = lat_re.search(script.text)
            if found:
                lat = float(found.group(1))
            found = lon_re.search(script.text)
            if found:
                lon = float(found.group(1))
                break
        if lat and lon:
            record['location'] = Point(lon, lat)
        else:
            try:
                record['location'] = self.geocode(address)['point']
            except (GeocodingException, ParsingError, TypeError):
                try:
                    # Some addresses have eg. a "Suite" that we can't use.
                    address = address.split(',')[0].strip()
                    record['location'] = self.geocode(address)['point']
                except (GeocodingException, ParsingError, TypeError):
                    raise SkipRecord("Couldn't geocode address %r" % address)

        return record

    def clean_detail_record(self, detail_record):
        detail_record = detail_record.copy()
        detail_record['description'] = text_from_html(detail_record['description'])
        detail_record['url'] = detail_record.pop('link')
        detail_record['item_date'] = datetime.date(*detail_record.pop('updated_parsed')[:3])
        for key in ('updated', 'title_detail', 'summary_detail', 'guidislink',
                    'summary', 'links', 'id'):
            del detail_record[key]

        return detail_record


    def save(self, old_record, list_record, detail_record):
        kwargs = detail_record.copy()
        self.logger.debug("SAVING %s" % kwargs['url'])
        attributes = kwargs.pop('_attributes')
        self.create_or_update(old_record, attributes, **kwargs)



def main(argv=None):
    import sys
    from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
    from optparse import OptionParser
    if argv is None:
        argv = sys.argv[1:]
    optparser = OptionParser()
    add_verbosity_options(optparser)
    scraper = MidMoCouponsScraper()
    opts, args = optparser.parse_args(argv)
    setup_logging_from_opts(opts, scraper.logger)
    scraper.update()
    # print scraper.num_skipped, scraper.num_changed, scraper.num_added

if __name__ == "__main__":
    main()
