#!/usr/bin/env python
# encoding: utf-8

"""
U. of Missouri police scraper.

Warning, this file contains a couple years worth of police reports
in one big file!

It may take several hours to run if you specify --days=-1,
most of which is spent on database operations.
"""

# <xs:element name="CreateDatetime" type="xs:dateTime" minOccurs="0" />
# <xs:element name="IncidentNumber" type="xs:string" minOccurs="0" />
# <xs:element name="HouseNumber" type="xs:int" minOccurs="0" />
# <xs:element name="StreetPrefix" type="xs:string" minOccurs="0" />
# <xs:element name="StreetName" type="xs:string" minOccurs="0" />
# <xs:element name="StreetType" type="xs:string" minOccurs="0" />
# <xs:element name="StreetSuffix" type="xs:string" minOccurs="0" />
# <xs:element name="Lat" type="xs:decimal" minOccurs="0" />
# <xs:element name="Lon" type="xs:decimal" minOccurs="0" />
# <xs:element name="Description" type="xs:string" minOccurs="0" />

from django.conf import settings
from django.contrib.gis.geos import Point
from ebpub.db.models import NewsItem, Schema, SchemaField, Lookup
from ebpub.utils.geodjango import intersects_metro_bbox
import datetime
import logging
import lxml.etree
import pyrfc3339
import sys
import traceback

HOST = '128.206.113.11'
USER = 'mupdreport'
PASS = 'M123456='
PORT = 22
FILENAME = 'mupd.xml'


logger = logging.getLogger('eb.retrieval.mo.mupd')

def cleanup(text):
    # Normalized whitespace.
    text = text or ''
    return ' '.join(text.strip().split())

def fetch_xml():
    """
    SFTP web address: 128.206.113.11
    Account: mupdreport
    Password: M123456=
    Port: 22
    Filename: mupd.xml
    """
    # scp works too, simpler than sftp.
    # We need pexpect to pass it a password.
    #
    # I tried installing paramiko (Python SFTP / SCP
    # client), but it depends on recent version of pycrypto which I
    # cannot find a reliable way to install on ubuntu.
    logger.info("Starting file fetch...")
    from pexpect import run
    import os, tempfile
    import shutil
    import filecmp
    current_dir = os.getcwd()
    cmd = 'scp -q -C -P %s %s@%s:%s .' % (PORT, USER, HOST, FILENAME)
    logger.debug("Running: %s" % cmd)
    outdir = tempfile.mkdtemp()
    try:
        os.chdir(outdir)
        # Note pexpect requires a newline in the password.
        password = PASS.strip() + '\n'
        output = run(cmd,
                     events={'(?i)password': password,
                             'Are you sure': 'yes\n',
                            },
                    ).strip()
        tmp_name = os.path.join(outdir, FILENAME)
        if not os.path.exists(tmp_name):
            logger.error("Error saving file %s." % tmp_name)
            logger.error("Output from server was:\n%s" % output)
            sys.exit(1)
        new_name = os.path.join(settings.HTTP_CACHE, FILENAME)
        if not os.path.isdir(settings.HTTP_CACHE):
            os.makedirs(settings.HTTP_CACHE)
        if os.path.exists(new_name) and filecmp.cmp(tmp_name, new_name):
            logger.info("%s has not changed" % new_name)
        else:
            os.rename(tmp_name, new_name)
            logger.info("Moved output file to %s" % new_name)
        return new_name
    finally:
        shutil.rmtree(outdir)
        os.chdir(current_dir)


def update(xmlfile, options):
    logger.info("Scraping University of Missouri police reports")

    if options.days == -1:
        start_date = datetime.date(1970, 1, 1)
    else:
        start_date = datetime.date.today() - datetime.timedelta(days=options.days)

    schema_slug = 'mupd'
    try:
        schema = Schema.objects.get(slug=schema_slug)
    except Schema.DoesNotExist:
        logger.error( "Schema (%s): DoesNotExist" % schema_slug)
        sys.exit(1)

    # We use iterparse() to avoid keeping the whole xml tree in memory,
    # this is a pretty big file.
    # See http://effbot.org/zone/element-iterparse.htm
    context = iter(lxml.etree.iterparse(xmlfile, events=('start', 'end')))
    addcount = updatecount = 0
    event, root = context.next()
    for event, elem in context:
        if event == 'end' and elem.tag == 'Table':
            category = cleanup(elem.findtext('Description'))
            lat = cleanup(elem.findtext('Lat'))
            lon = cleanup(elem.findtext('Lon'))
            item_date = cleanup(elem.findtext('CreateDatetime'))
            house_number = cleanup(elem.findtext('HouseNumber'))
            prefix = cleanup(elem.findtext('StreetPrefix'))
            street = cleanup(elem.findtext('StreetName'))
            streettype = cleanup(elem.findtext('StreetType'))
            suffix = cleanup(elem.findtext('StreetSuffix'))
            incident_number = cleanup(elem.findtext('IncidentNumber'))
            # We're done with this <Table> tag; clear the root element
            # that iterparse is building to avoid bloating memory with
            # empty elements.
            root.clear()
        else:
            continue

        if item_date:
            item_date = pyrfc3339.parse(item_date)
            if item_date.date() < start_date:
                logger.debug("Date %s is older than start date, skipping." % item_date)
                continue
        else:
            logger.debug("No parsable date, skipping.")
            continue

        location_parts = [house_number, prefix, street, streettype, suffix]
        location_name = ' '.join([s for s in location_parts if s])
        if location_name:
            title = '%s: %s' % (location_name.title(), category.title())
        else:
            title = category.title()

        try:
            lon, lat = float(lon), float(lat)
            location = Point(lon, lat)
        except ValueError:
            location = None

        if location and not intersects_metro_bbox(location):
            logger.info("SKIP %s (at %s), not within our metro area"
                        % (title, (location.x, location.y)))
            continue

        cat_field = SchemaField.objects.get(schema=schema, name='category')
        cat_lookup = Lookup.objects.get_or_create_lookup(
            cat_field, category, category, "", False)

        attributes = {'incident_number': incident_number,
                      'category': cat_lookup.id}

        incident_number_field = SchemaField.objects.get(schema=schema,
                                                        name='incident_number')
        try:
            item = NewsItem.objects.filter(schema__id=schema.id).by_attribute(incident_number_field, incident_number)[0]
            status = 'updated'
        except IndexError:
            item = NewsItem(pub_date=datetime.datetime.now())
            status = 'added'
        except NewsItem.MultipleObjectsReturned:
            logger.warn("Multiple entries matched incident_number %s" % incident_number)
            continue
        logger.debug("%s %s" % (status, incident_number))
        try:
            item.title = title
            item.schema = schema
            item.item_date = item_date.date()
            item.description = title # We don't have anything more verbose!
            item.location = location
            item.location_name = location_name
            item.save()
            item.attributes = attributes
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
    optparser.add_option(
        '-d', '--days',
        help="How many days ago to start searching. Default is 30. -1 means load everything.",
        action="store", default=30, type="int",
        )
    add_verbosity_options(optparser)
    opts, args = optparser.parse_args(argv)
    # This sets up the root logger & handlers as per other scrapers.
    import ebdata.retrieval.log
    setup_logging_from_opts(opts, logger=logger)
    xmlpath = fetch_xml()
    xmlfile = open(xmlpath, 'r')
    return update(xmlfile, opts)

if __name__ == '__main__':
    sys.exit(main())


