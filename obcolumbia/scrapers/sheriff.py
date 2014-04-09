#!/usr/bin/env python
# encoding: utf-8

# http://report.boonecountymo.org/mrcjava/mrcclasses/SH01_MP/cadlogs.xml
#
# {'address': u'11391 HECHT RD N-BC',
#  'extnaturedisplayname': u'2011146823',
#  'geo_lat': u'39.083450',
#  'geo_long': u'-92.211350',
#  'innum': u'2011146823',
#  'latitude': u'39.083450',
#  'longitude': u'-92.211350',
#  'summary': u'08/09/2011 09:39:51 : 11391 HECHT RD N-BC',
#  'summary_detail': {'base': 'http://report.boonecountymo.org/mrcjava/mrcclasses/SH01_MP/cadlogs.xml',
#                     'language': None,
#                     'type': 'text/html',
#                     'value': u'08/09/2011 09:39:51 : 11391 HECHT RD N-BC'},
#  'title': u'ASSIST OFFICER',
#  'title_detail': {'base': 'http://report.boonecountymo.org/mrcjava/mrcclasses/SH01_MP/cadlogs.xml',
#                   'language': None,
#                   'type': 'text/plain',
#                   'value': u'ASSIST OFFICER'},
#  'updated': u'08/09/2011 09:39:51',
#  'updated_parsed': None}


from datetime import datetime
from django.contrib.gis.geos import Point
from ebpub.db.models import NewsItem, Schema, SchemaField, Lookup
import feedparser
import logging
import sys
import traceback


# Note there's an undocumented assumption in ebdata that we want to
# unescape html before putting it in the db.
from ebdata.retrieval.utils import convert_entities

logger = logging.getLogger('eb.retrieval.mo.sheriff')

def get_element(entry, name, namespace="calldata"):
    """Workaround for horrible feedparser behavior where you sometimes
    get the xml namespace as part of the property name, and sometimes don't.
    """
    return getattr(entry, '%s_%s' % (namespace, name), None) or getattr(entry, name)

def update(url):
    schema_slug = 'sheriff'
    try:
        schema = Schema.objects.get(slug=schema_slug)
    except Schema.DoesNotExist:
        logger.error( "Schema (%s): DoesNotExist" % schema_slug)
        sys.exit(1)

    incident_type_field = SchemaField.objects.get(schema=schema, name='incident_type')


    try: 
        innum_field = SchemaField.objects.get(schema=schema, name='innum')
    except SchemaField.DoesNotExist: 
        logger.error( "SchemaField innum Does Not Exist for %s" % schema_slug)
        sys.exit(1)

    logger.info("Scraping %s" % schema.name)


    f = feedparser.parse(url)
    addcount = updatecount = 0
    for entry in f.entries:
        
        innum = int(get_element(entry, 'innum'))
        title = convert_entities(entry.title)
        description = convert_entities(entry.summary)

        try:
            item = NewsItem.objects.filter(schema=schema).by_attribute(innum_field, innum)[0]
            #url=item_url)
            status = 'updated'
        except IndexError:
            item = NewsItem()
            status = 'added'

        try:
            item.title = title
            item.schema = schema
            item.description = description

            try: 
                item.location = Point((float(entry.geo_long), float(entry.geo_lat)))
            except: 
                logger.info("Skipping item %s with no location information" % innum)

            item.location_name = get_element(entry, 'address')


            # this feed uses an invalidly formatted pubDate which 
            # appears to be intended to express the time of the 
            # incident, used for publication time as well.
            # 24 hour time. 
            ct = datetime.strptime(entry.updated, r"%m/%d/%Y %H:%M:%S")
            #ct = datetime(ct.year, ct.month, ct.day, ct.hour, ct.minute, ct.second, tzinfo=tzlocal())
            #ct = ct.astimezone(tzutc())

            item.item_date = ct
            item.pub_date = ct.date()
            item.save()

            # extra attributes
            item.attributes['innum'] = innum

            for k in ['address']: 
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

    
    logger.info("Finished scraping %s: %d added, %d updated" % (schema.name, addcount, updatecount))

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
        url = 'http://report.boonecountymo.org/mrcjava/mrcclasses/SH01_MP/cadlogs.xml'
    return update(url)

if __name__ == '__main__':
    sys.exit(main())
