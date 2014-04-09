#!/usr/bin/env python
# encoding: utf-8

from datetime import datetime
from django.contrib.gis.geos import Point
from ebpub.db.models import NewsItem, Schema, SchemaField, Lookup
from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
import feedparser
import logging
import sys
import traceback

# Note there's an undocumented assumption in ebdata that we want to
# unescape html before putting it in the db.
from ebdata.retrieval.utils import convert_entities

logger = logging.getLogger('eb.retrieval.mo.fire')

# 'address': u'1600 BROADWAY E-CO',
#  'agencies': u'Boone Hospital Center Ambulance',
#  'calldatetime': u'12/8/2010 12:19:35 PM',
#  'extnaturedisplayname': u'Long Distance Transport',
#  'fdids': u'19054',
#  'geo_lat': u'38.94981118',
#  'geo_long': u'-92.31585499',
#  'innum': u'201022877',
#  'latitude': u'38.94981118',
#  'longitude': u'-92.31585499',
#  'summary': u'12/8/2010 12:19:35 PM : 1600 BROADWAY E-CO : Boone Hospital Center Ambulance',
#  'summary_detail': {'base': 'http://www.gocolumbiamo.com/PSJC/Services/911/911dispatch/fire_georss.php',
#                     'language': None,
#                     'type': 'text/html',
#                     'value': u'12/8/2010 12:19:35 PM : 1600 BROADWAY E-CO : Boone Hospital Center Ambulance'},
#  'timestamp': u'1291832375',
#  'title': u'Long Distance Transport',
#  'title_detail': {'base': 'http://www.gocolumbiamo.com/PSJC/Services/911/911dispatch/fire_georss.php',
#                   'language': None,
#                   'type': 'text/plain',
#                   'value': u'Long Distance Transport'},
#  'trucks': u'M151',
#  'updated': u'Wed, 08 Dec 2010 12:19:35 CST',
#  'updated_parsed': time.struct_time(tm_year=2010, tm_mon=12, tm_mday=8, tm_hour=18, tm_min=19, tm_sec=35, tm_wday=2, tm_yday=342, tm_isdst=0)}

def get_element(entry, name, namespace="calldata"):
    """Workaround for horrible feedparser behavior where you sometimes
    get the xml namespace as part of the property name, and sometimes don't.
    """
    return getattr(entry, '%s_%s' % (namespace, name), None) or getattr(entry, name)


def update(url):
    logger.info("Scraping fire reports")
    schema_slug = 'fire'

    try:
        schema = Schema.objects.get(slug=schema_slug)
    except Schema.DoesNotExist:
        logger.error( "Schema (%s): DoesNotExist" % schema_slug)
        sys.exit(1)

    incident_type_field = SchemaField.objects.get(schema=schema, name='incident_type')
    f = feedparser.parse(url)
    addcount = updatecount = 0
    for entry in f.entries:
        title = convert_entities(entry.title)
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

            for k in ['trucks', 'fdids', 'agencies', 'address']: 
                try:
                    item.attributes[k] = get_element(entry, entry[k])
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
    logger.info("Finished scraping fire reports: %d added, %d updated" % (addcount, updatecount))

def main(argv=None):
    import sys
    argv = argv or sys.argv[1:]
    from optparse import OptionParser
    optparser = OptionParser()
    add_verbosity_options(optparser)
    opts, args = optparser.parse_args(argv)
    # This sets up the root logger & handlers as per other scrapers.
    import ebdata.retrieval.log
    setup_logging_from_opts(opts, logger=logger)
    if args:
        url = args[0]
    else:
        url = 'http://www.gocolumbiamo.com/PSJC/Services/911/911dispatch/fire_georss.php'
    update(url)


if __name__ == '__main__':
    sys.exit(main())
