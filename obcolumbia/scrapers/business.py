from datetime import datetime, timedelta
from ebpub.geocoder import SmartGeocoder
from ebpub.streets.models import Place, PlaceType
from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
from httplib2 import Http
from urlparse import urljoin
import json
import logging
import rfc822

log = logging.getLogger('eb.retrieval.mo.business')


class EverythingMidMoBusinessScraper(object):

    BASE_URL = 'http://www.everythingmidmo.com/marketplace/api/v1/business/business/?sort_by=-modified'
    BASE_LINK = 'http://www.everythingmidmo.com'
    
    def __init__(self, days_prior=30):
        self.days_prior = days_prior
        
    def update(self):
        seen = set()
        last_date = datetime.now() + timedelta(days=-self.days_prior) 
        count = 0
        total = 0
        done = False
        http = Http()
        cur_url = self.BASE_URL 
        while cur_url and not done: 
            count = 0
            log.info("Requesting %s" % cur_url)
            r, c = http.request(cur_url)
            if r.status != 200: 
                log.error("Error: status was %d for url %s" % (r.status, cur_url))

            data = json.loads(c)

            for listing in data.get('objects', []):
                update_date = _parse_midmo_date(listing['modified'])
                if update_date < last_date:
                    done = True
                    break
                    
                pid = listing.get('id')
                if pid in seen:
                    log.info("Skipping already updated listing (%s)" % listing.get('name')) 
                    continue
                seen.add(pid)
                self._update_place(listing)
                count += 1
                total += 1
                
            log.info("got %d listings (%d total)" % (count, total))
            cur_url = urljoin(self.BASE_URL, data.get('meta', {}).get('next', ''))
            

        log.info("done")
        
    def _update_place(self, listing):

        place_name = listing.get('name')
        location = listing.get('location')
        address = listing.get('address1')         
        
        if not location:
            if not address: 
                log.info("Skipping listing %s with no location" % place_name)
                return
            
            log.info("Geocoding address for place %s (%s)" % (place_name, address))
            try:
                result = SmartGeocoder().geocode(address)
                location = result['point']
            except:
                log.info('skipping listing %s with unknown address %s' % (place_name, address))
                return 
    
        # try to find or create the 'place type' for this place
        type_slug = listing.get('business_type', {}).get('codename')
        try: 
            place_type = PlaceType.objects.get(slug=type_slug)
        except PlaceType.DoesNotExist: 
            type_name = listing.get('business_type', {}).get('name')
            log.info("Creating new place type %s (%s)" % (type_slug, type_name))
            if type_name[0].lower() in ('a','e','i','o','u'): 
                article = 'an'
            else: 
                article = 'a'

            place_type = PlaceType(slug=type_slug, name=type_name, 
                                   plural_name=type_name,
                                   indefinite_article=article)
            place_type.save()

        url = listing.get('absolute_url')
        url = self.BASE_LINK + url
        try: 
            place = Place.objects.get(url=url)
            log.info("updating place %s" % listing.get('name'))
        except Place.DoesNotExist:
            log.info("creating place %s" % listing.get('name'))
            place = Place(url=url)

        place.place_type = place_type
        place.pretty_name = listing.get('name')
        place.location = location
        place.address = address
        place.save()


def _parse_midmo_date(datestring):
    """
    returns a local datetime corresponding to 
    the datestring given.
    """
    # these appear to be rfc822/2822, not documented.
    return datetime.fromtimestamp(rfc822.mktime_tz(rfc822.parsedate_tz(datestring)))


def main(argv=None):
    import sys
    argv = argv or sys.argv[1:]
    from optparse import OptionParser
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option(
        "--days-prior", help='how many days ago to start scraping', type="int",
        default=30
        )
    add_verbosity_options(parser)
    options, args = parser.parse_args(argv)
    # This sets up the root logger & handlers as per other scrapers.
    import ebdata.retrieval.log
    setup_logging_from_opts(options, logger=log)

    scraper = EverythingMidMoBusinessScraper(days_prior=options.days_prior)
    scraper.update()

if __name__ == '__main__':
    main()
