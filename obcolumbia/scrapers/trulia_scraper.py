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

Trulia real estate scraper.
Possibly requires some sort of agreement with Trulia?
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.list_detail import RssListDetailScraper
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebdata.textmining.treeutils import text_from_html
from ebpub.db.models import NewsItem
from ebpub.geocoder import SmartGeocoder
from ebpub.geocoder.base import GeocodingException
from ebpub.geocoder.parser.parsing import ParsingError

import datetime
import re

class TruliaRealEstateScraper(RssListDetailScraper, NewsItemListDetailScraper):

    # Why not RSS? Because: There are RSS feeds if you can figure out
    # how to get one for just your area (I haven't dug into it but I'm
    # guessing it saves your recent website searches in a session or
    # cookie and uses that for the RSS parameters), but even then, it
    # has very little info, just links to HTML pages for the real
    # info.  The HTML listing, by contrast, has everything we need.

    schema_slugs = ('real-estate-listings',)
    has_detail = False
    logname = 'mo.trulia'

    #url = 'http://www.trulia.com/MO/Columbia/'
    url = 'http://www.trulia.com/rss2/MO/Columbia/'

    def list_pages(self):
        yield self.fetch_data(self.url)

    ## Old parse_list method using scraped HTML, which trulia
    ## does not want us to do.
    # def parse_list(self, page):
    #     import lxml.html
    #     tree = lxml.html.fromstring(page)
    #     for row in tree.cssselect('div.srp_row'):
    #         record = {}
    #         property_id = row.attrib['data-propertyid'].strip()

    #         price = row.cssselect('span#price_%s' % property_id)[0].text

    #         record['location_name'] = row.cssselect('.address_section a')[0].text.strip()

    #         url = row.cssselect('.address_section a')[0].attrib['href']
    #         record['url'] = 'http://www.trulia.com/%s' % url

    #         broker_name = row.cssselect('.broker_name')[0].text.strip()

    #         record['_attributes'] = {
    #             'property_id': property_id.strip(),
    #             'price': price.strip(),
    #             'broker': broker_name.strip(),
    #             }

    #         details = ' '.join(
    #             [p.text.strip() for p in row.cssselect('.prop_details p') if p.text])

    #         descr = ' '.join(text_from_html(details).split())
    #         # TODO: capture partial bathrooms? For now we only count full.
    #         bed_bath_re = re.compile(r'([\d\.]+)\s+br\s+/\s+([\d\.]+)\s+(?:full,\s+\d+\s+partial\s+)?ba\s+')
    #         matched = bed_bath_re.search(descr)
    #         if matched:
    #             record['_attributes']['bedrooms'] = float(matched.group(1))
    #             record['_attributes']['bathrooms'] = float(matched.group(2))
    #         else:
    #             self.logger.info("Couldn't parse bathrooms from %r" % descr)
    #         sqft_re = re.compile(r'([\d,]+)\s+sqft')
    #         matched = sqft_re.search(descr)
    #         if matched:
    #             record['_attributes']['sqft'] = int(matched.group(1).strip().replace(',', ''))
    #         record['item_date'] = datetime.date.today()

    #         details_row = tree.cssselect('div#expanding_row_%s' % property_id)[0]
    #         # Ugh, this is fairly unstructured html.
    #         maybe_info = [p.text_content().strip() for p in details_row.cssselect('p')]
    #         # That munges it into a list of colon-separated things like 'ZIP: 65202'.
    #         for info in maybe_info:
    #             try:
    #                 key, value = info.split(':', 1)
    #             except ValueError:
    #                 continue
    #             key, value = key.strip().lower(), value.strip()
    #             if not key and value:
    #                 continue
    #             if key == 'zip':
    #                 record['location_name'] = '%s %s' % (record['location_name'], value)
    #             elif key in ('listing type', 'year built'):
    #                 key = key.replace(' ', '_')
    #                 record['_attributes'][key] = value

    #             # Doesn't look like Columbia listings include 'neighborhood.'
    #         record['description'] = details_row.cssselect('.description')[0].text_content()
    #         yield record



    def clean_list_record(self, record):
        cleaned = {}
        title = cleaned['title'] = record['title'].strip()
        description = cleaned['description'] = record['summary'].strip()

        property_id = record['id'].split('/')[-1]
        property_id = property_id.split('-')[0].strip()

        attrs = cleaned['_attributes'] = {
            'property_id': property_id,
            }

        cleaned['item_date'] = datetime.date(*record.updated_parsed[:3])

        cleaned['url'] = record['link'].replace(
            'www.trulia.com/property/',
            'columbiatribune.trulia.com/property/'
            )

        # Most of what we want is smushed into the title or description...

        sqft_re = re.compile(r'([\d,]+)\s+sqft')
        matched = sqft_re.search(description)
        if matched:
            cleaned['_attributes']['sqft'] = int(matched.group(1).strip().replace(',', ''))

        #  price
        price_re = re.compile(r'\$([\d,]+)')

        price = price_re.search(title)
        if price_re:
            cleaned['_attributes']['price'] = price.group(1).replace(',', '').strip()
        else:
            self.logger.info("Couldn't parse price from %r" % title)

        # Bedrooms.
        bed_re = re.compile(r'([\d\.]+)\s+bed(?:s?)\s*,*')
        matched = bed_re.search(description)
        if matched:
            bedrooms = float((matched.group(1).rstrip('. ')))
            # Convert that to a Lookup so we can search on it.
            if int(bedrooms) == bedrooms:
                bedrooms = str(int(bedrooms))
            else:
                bedrooms = '%.1f' % bedrooms
            bedrs = self.get_or_create_lookup('bedrooms', bedrooms, bedrooms)
            attrs['bedrooms'] = bedrs.id

        else:
            self.logger.info("Couldn't parse bedrooms from %r" % title)

        # Bathrooms.
        bath_re = re.compile(r'([\d\.]+)\s+bath(?:s?)\s*,*')
        matched = bath_re.search(description)
        if matched:
            bathrooms = float(matched.group(1).rstrip('. '))
            # Now convert baths into lookups, so users can search on those.
            if int(bathrooms) == float(bathrooms):
                bathrooms = str(int(bathrooms))
            else:
                bathrooms = '%.1f' % bathrooms
            bathrs = self.get_or_create_lookup('bathrooms', bathrooms, bathrooms)
            attrs['bathrooms'] = bathrs.id
        else:
            self.logger.info("Couldn't parse bathrooms from %r" % title)

        # Location.
        cleaned['location_name'] = cleaned['title'].split('$')[0].rstrip(' ,')
        try:
            cleaned['location'] = SmartGeocoder().geocode(cleaned['location_name'])['point']
        except (GeocodingException, ParsingError):
            raise SkipRecord("Couldn't geocode address %r" % cleaned['location_name'])

        ## Year built. Not included in RSS.
        #attrs['year_built'] = attrs['year_built'] and int(attrs['year_built']) or None

        # Listing type, eg. 'resale' or 'new construction'.
        listing_type = ''  # Not included in RSS.
        if listing_type:
            listing_type = self.get_or_create_lookup('listing_type',
                                                     listing_type, listing_type)
            attrs['listing_type'] = listing_type.id

        # Property type, eg. 'Condo' or 'Single-family Home'
        property_type_re = re.compile(r',\s+([-\w\s]+?) in [\w\s]+,\s+')
        matched = property_type_re.search(description)
        if matched:
            property_type = matched.group(1).strip().title()
            property_type = self.get_or_create_lookup('property_type',
                                                      property_type, property_type)
            attrs['property_type'] = property_type.id

        # Broker.
        broker = ''  # Not included in RSS.
        if broker:
            broker_name = attrs['broker']
            broker = self.get_or_create_lookup('broker', broker_name, broker_name)
            attrs['broker'] = broker.id


        # Thumbnail image.
        thumbnail = self.ns_get(record, 'media:thumbnail')
        if thumbnail:
            attrs['thumbnail'] = thumbnail[0]['url']

        # Only include the address in the title?
        cleaned['title'] = cleaned['location_name']
        return cleaned


    def existing_record(self, record):
        url = record['url']
        qs = NewsItem.objects.filter(schema__id=self.schema.id, url=url)
        try:
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        kwargs = list_record.copy()
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
    scraper = TruliaRealEstateScraper()
    opts, args = optparser.parse_args(argv)
    setup_logging_from_opts(opts, scraper.logger)
    scraper.update()

if __name__ == "__main__":
    main()
