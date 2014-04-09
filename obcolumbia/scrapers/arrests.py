from ebdata.scrapers.general.spreadsheet.retrieval import SpreadsheetScraper
from ebdata.scrapers.general.spreadsheet.retrieval import open_url
from ebpub.db.models import Lookup
import copy

fields_mapping_csv = [
    ['', 'NAME', 'ADDRESS', 'SEX', 'BIRTHDAY', 'ARRESTING AGENCY',
     'BAIL AMT', 'RELEASE REASON', 'ARREST DATE', 'CHARGE', 'WARRANT', 'CASE NO',
     'DISPOSITION COMMENT'],
    ['image_url', 'title', 'location_name', 'sex', 'birthday', 'arresting_agency',
     'bail_amt', 'release_reason', 'item_date', 'charge', 'warrant', 'case_no',
     'disposition_comment']
]


class ArrestScraper(SpreadsheetScraper):

    unique_fields = []   # Use defaults.
    get_location_name_from_all_fields = False

    def __init__(self, items_sheet_file, *args, **kwargs):
        self.items_sheet_file = items_sheet_file
        self.schema_slugs = [kwargs.pop('schema_slug', None)]
        self.items_sheet, self.items_type = open_url(items_sheet_file)
        self.items_sheet = self.items_sheet.read()
        # To map input columns to output fields, it's easiest,
        # if a bit odd, to simulate a "mapping" spreadsheet
        # as used by the base scraper.
        self.map_sheet = '\n'.join(
            [','.join(row) for row in fields_mapping_csv]
        )
        self.map_type = 'text/csv'

        # A place to stash most recently seen records, since the spreadsheet
        # omits various fields when repeating the same arrestee several
        # times in a row.
        self.previous_record = {'attributes': {}}

        # Note we deliberately call super() on our superclass,
        # because we want to do *its* parent class __init__
        # but not its own __init__ because we already took care
        # of that stuff differently above.
        super(SpreadsheetScraper, self).__init__(*args, **kwargs)

    def clean_list_record(self, list_record):
        cleaned_record = copy.deepcopy(list_record)
        # If some fields are empty, notably the title, then try to get
        # them from the previously seen record, and then stash the current
        # one for the next loop.
        _missing = object()
        if 'charge' in cleaned_record:
            # The CSV parser gives us a float, which we don't really want.
            cleaned_record['charge'] = str(cleaned_record['charge'])
        we_are_updating = self.previous_record.get('title') and not cleaned_record.get('title')
        if we_are_updating:
            for key in ('title', 'location', 'location_name'):
                if cleaned_record.get(key) in (None, u'', '') and key in self.previous_record:
                    cleaned_record[key] = self.previous_record[key]

            for key in ('sex', 'birthday', 'release_reason', 'case_no',
                        'warrant', 'arresting_agency'):
                if cleaned_record.get(key, _missing) in (None, u'', '') and key in self.previous_record['attributes']:
                    cleaned_record[key] = self.previous_record['attributes'][key]
            # Bail differs between each, and we don't have a good way
            # to display separate bail; so, add them.

            bail = cleaned_record.get('bail_amt', '0.0')
            bail = bail.replace(',', '').replace('$', '')
            bail = float(bail)
            old_bail = self.previous_record['attributes'].get('bail_amt', '0.0').replace('$', '').replace(',', '')
            old_bail = float(old_bail)
            cleaned_record['bail_amt'] = '$%.2f' % (bail + old_bail)

            # Concatenate the disposition comments.
            comments = [cleaned_record.get('disposition_comment', '')]
            comments.append(self.previous_record['attributes'].get('disposition_comment', ''))
            comments = ', '.join([c.strip() for c in comments if len(c.strip())])
            cleaned_record['disposition_comment'] = comments

            # Many-to-many for the 'charge' field.
            # Previous record has a string of comma-separated ids;
            # unfortunately we need a list of names to make the
            # superclass happy. This dance does that.
            charges = self.previous_record['attributes'].get('charge', '').split(',')
            charges = set([c.name for c in Lookup.objects.filter(id__in=charges)])
            charges = charges or set()
            charge = cleaned_record.get('charge', None)
            if charge is not None:
                charges.add(str(charge))
                charges = list(charges)
            cleaned_record['charge'] = list(charges)
            print "CHARGES: %s" % charges

        #cleaned_record['location_name'] = cleaned_record.get('location_name') or 'TODO MISSING'
        cleaned_record = super(ArrestScraper, self).clean_list_record(cleaned_record)
        self.previous_record = copy.deepcopy(cleaned_record)
        return cleaned_record


def main(argv=None):
    import sys
    if argv is None:
        argv = sys.argv[1:]
    from optparse import OptionParser
    usage = "usage: %prog [options] <spreadsheet>"
    usage += "\n\nSpreadsheet argument can be local files or URLs."
    parser = OptionParser(usage=usage)

    parser.add_option(
        "--schema", help="slug of news item type to create when scraping",
        default="arrests"
    )

    from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
    add_verbosity_options(parser)

    options, args = parser.parse_args(argv)
    try:
        items_sheet = args[0]
    except IndexError:
        parser.print_usage()
        sys.exit(0)

    scraper = ArrestScraper(items_sheet, schema_slug=options.schema)
    setup_logging_from_opts(options, scraper.logger)
    scraper.update()


if __name__ == '__main__':
    main()
