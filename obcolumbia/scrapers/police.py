#!/usr/bin/env python
# encoding: utf-8

# http://www.gocolumbiamo.com/PSJC/Services/911/911dispatch/police_georss.php
#
# {'address': u'600 WALNUT ST E-CO',
#  'aptlot': u'',
#  'calldatetime': u'12/8/2010 9:30:12 AM',
#  'disp': u'2',
#  'extnaturedisplayname': u'REPORT WRITING',
#  'geo_lat': u'38.952500',
#  'geo_long': u'-92.330580',
#  'gridloc': u'28124R',
#  'innum': u'2010243823',
#  'latitude': u'38.952500',
#  'longitude': u'-92.330580',
#  'summary': u'12/8/2010 9:30:12 AM : 600 WALNUT ST E-CO',
#  'summary_detail': {'base': 'http://www.gocolumbiamo.com/PSJC/Services/911/911dispatch/police_georss.php',
#                     'language': None,
#                     'type': 'text/html',
#                     'value': u'12/8/2010 9:30:12 AM : 600 WALNUT ST E-CO'},
#  'timestamp': u'1291822212',
#  'title': u'REPORT WRITING',
#  'title_detail': {'base': 'http://www.gocolumbiamo.com/PSJC/Services/911/911dispatch/police_georss.php',
#                   'language': None,
#                   'type': 'text/plain',
#                   'value': u'REPORT WRITING'},
#  'updated': u'Wed, 08 Dec 2010 09:30:12 CST',
#  'updated_parsed': time.struct_time(tm_year=2010, tm_mon=12, tm_mday=8, tm_hour=15, tm_min=30, tm_sec=12, tm_wday=2, tm_yday=342, tm_isdst=0)}

from datetime import datetime
from django.contrib.gis.geos import Point
from ebpub.db.models import NewsItem, Schema, SchemaField, Lookup
import feedparser
import logging
import os.path
import sys
import traceback

# Note there's an undocumented assumption in ebdata that we want to
# unescape html before putting it in the db.
from ebdata.retrieval.utils import convert_entities

logger = logging.getLogger('eb.retrieval.mo.police')

# Some types of incidents are just not worth storing.
here = os.path.dirname(__file__)
SKIP_TYPES = open(os.path.join(here, 'police_types_to_skip.txt')).readlines()
SKIP_TYPES = [s.strip().upper() for s in SKIP_TYPES if s.strip()]

def get_element(entry, name, namespace="calldata"):
    """Workaround for horrible feedparser behavior where you sometimes
    get the xml namespace as part of the property name, and sometimes don't.
    """
    return getattr(entry, '%s_%s' % (namespace, name), None) or getattr(entry, name)



def update(url):
    logger.info("Scraping police reports")
    schema_slug = 'police'

    try:
        schema = Schema.objects.get(slug=schema_slug)
    except Schema.DoesNotExist:
        logger.error( "Schema (%s): DoesNotExist" % schema_slug)
        sys.exit(1)

    incident_type_field = SchemaField.objects.get(schema=schema, name='incident_type')

    f = feedparser.parse(url)
    addcount = updatecount = 0
    for entry in f.entries:
        title = convert_entities(entry.title).strip()
        # The title will be used as the incident type.
        if title in SKIP_TYPES:
            logger.info("Skipping entry of type %s" % title)
        description = convert_entities(entry.summary)
        try:
            item = NewsItem.objects.get(schema__id=schema.id,
                                        title=title,
                                        description=description)
            #url=item_url)
            status = 'updated'
        except NewsItem.DoesNotExist:
            item = NewsItem()
            status = 'added'
        except NewsItem.MultipleObjectsReturned:
            # Seen some where we get the same story with multiple URLs. Why?
            logger.warn("Multiple entries matched title %r and description %r. Expected unique!" % (title, description))
            continue
        try:
            item.title = title
            item.schema = schema
            item.description = description
            item.pub_date = datetime(*entry.updated_parsed[:6])
            item.location = Point((float(entry.geo_long), float(entry.geo_lat)))
            item.location_name = get_element(entry, 'address')

            # parse call time
            ct = datetime.strptime(get_element(entry, 'calldatetime'),
                                   r"%m/%d/%Y %I:%M:%S %p")
            #ct = datetime(ct.year, ct.month, ct.day, ct.hour, ct.minute, ct.second, tzinfo=tzlocal())
            #ct = ct.astimezone(tzutc())

            item.item_date = ct
            item.save()


            # extra attributes
            try:
                item.attributes['calldatetime'] = ct
            except: 
                pass

            try: 
                item.attributes['innum'] = int(get_element(entry, 'innum'))
            except: 
                pass
                
            for k in ['disp', 'aptlot', 'address']: 
                try: 
                    item.attributes[k] = get_element(entry, k)
                except: 
                    pass

            # create a lookup based on the title, this is the closest thing to 
            # a category that is available in the data.
            lu = Lookup.objects.get_or_create_lookup(incident_type_field, title, title, "", False)
            item.attributes['incident_type'] = lu.id


            if status == 'added':
                addcount += 1
            else:
                updatecount += 1
            logger.info("%s: %s" % (status, item.title))
        except:
            logger.error("Warning: couldn't save %r. Traceback: %s" % (item.title, traceback.format_exc()))
    logger.info("Finished scraping police reports: %d added, %d updated" % (addcount, updatecount))

def main(argv=None):
    argv = argv or sys.argv[1:]
    from optparse import OptionParser
    from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
    optparser = OptionParser()
    add_verbosity_options(optparser)
    opts, args = optparser.parse_args(argv)
    # This sets up the root logger & handlers as per other scrapers.
    import ebdata.retrieval.log
    setup_logging_from_opts(opts, logger=logger)
    if args:
        url = args[0]
    else:
        url = 'http://www.gocolumbiamo.com/PSJC/Services/911/911dispatch/police_georss.php'
    return update(url)

if __name__ == '__main__':
    sys.exit(main())




