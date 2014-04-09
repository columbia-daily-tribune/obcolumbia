
"""
We do not have a data source yet so, currently this just loads one dummy data record.
"""
## A single violation from the Inspection_Queries.xls 'est insp viol
## view' sheet, formatted as a dict.
## The Exported_Est_Insp_Viol_View.xls data is identical.
#
# est_insp_viol_view = {
#  'Critical': '0',
#  'Est_Name': 'ASIAN FOOD AND GIFTS',
#  'Est_Type': 'GROCERY STORE',
#  'Insp_Date': '02-Mar-06',
#  'Insp_F_Nm': 'WILLIAM',
#  'Insp_L_Nm': 'JOHNSON',
#  'Insp_Num': '9441',
#  'Insp_Type': 'ROUTINE',
#  'Person_in_Charge': 'MARIDEN ALBRECHT',
#  'St_Dir': '',
#  'St_Name': 'VANDIVER',
#  'St_Number': '705',
#  'Title': 'Toilet Rooms, Enclosed.',
#  'Viol_Code': '6-202.14',
#  'dbo_Inspections_SS_View.Comments': ' ',
#  'dbo_Violations_SS_View.Comments': 'RESTROOM NEEDS SELF CLOSING DEVICE '
# }

## Same (?) from the Inspection_Queries.xls 'by date range' sheet.
## This is mostly a subset, plus 'Township'
#
# insp_queryies_by_date_range = {
#  'Critical': '0',
#  'Est_Name': 'ASIAN FOOD AND GIFTS',
#  'Insp_Date': '02-Mar-06',
#  'Insp_Type': 'ROUTINE',
#  'St_Dir': '',
#  'St_Name': 'VANDIVER',
#  'St_Number': '705',
#  'Title': 'Toilet Rooms, Enclosed.',
#  'Township': 'COLUMBIA',
#  'Viol_Code': '6-202.14'}

## Same one from Exported_Inspections_by_Date_Range_View.xls
# exported_by_date_range = {
#  'Critical': '0',
#  'Est_Name': 'ASIAN FOOD AND GIFTS',
#  'Insp_Date': '3/2/2006',
#  'Insp_Type': 'ROUTINE',
#  'St_Dir': '',
#  'St_Name': 'VANDIVER',
#  'St_Number': '705',
#  'Title': 'Toilet Rooms, Enclosed.',
#  'Township': 'COLUMBIA',
#  'Viol_Code': '6-202.14'}

# Inspections_Tables.xls

# 5 sheets, one per db table.

# 'Establishment_SS_View' adds some more info about the establishment:
# open date, close date, status (active/inactive), water supply (eg
# 'city'), sewage (eg 'public'), priority (?), city_cnty (either
# 'city' or 'county'), area code, phone, street number / dir / name/
# suffix (suffix is missing from the spreadsheets above), 
# street pre-qualifier (eg 'building 5'), street post-qualifier (eg 'STE'),
# apt number, township, zip code (zip is missing from the spreadsheets above).
#
# 'Establishment_Types' just provides the 'Est_Type' mentioned above.

# 'Inspections_SS_View'  provides the dbo_Inspections_SS_View_Comments field
# mentioned above.

# 'Violation_Codes' adds a 'Description' of each violation,
# eg for this one "A toilet room located on the premises shall be
# completely enclosed and provided with a tight-fitting and
# self-closing door except that this requirement does not apply to a
# toilet room that is located outside a food establishment and does
# not open di rectl" (sic)
# Also has a 'Swing' boolean, dunno what that means.

# 'Violations' only adds a 'Correct_By_Date' per violation.


merged = {
 'Critical': '0',
 'Est_Name': 'ASIAN FOOD AND GIFTS', # item.title, item.description
 'Est_Type': 'GROCERY STORE',  # item.attributes['establishment_type'] - LOOKUP
 'Insp_Date': '02-Mar-06',  # item.item_date
 'Insp_F_Nm': 'WILLIAM',  # item.attributes['inspector']  - LOOKUP
 'Insp_L_Nm': 'JOHNSON',  # item.attributes['inspector']  - LOOKUP
 'Insp_Num': '9441',    # item.attributes['inspection_id']
 'Insp_Type': 'ROUTINE',   # item.attributes['inspection_type'] - LOOKUP
 'Person_in_Charge': 'MARIDEN ALBRECHT',  # item.attributes['person_in_charge'] - SEARCHABLE
 'St_Dir': '',    # item.location_name, also for geocoding
 'St_Name': 'VANDIVER',  # item.location_name, also for geocoding
 'St_Number': '705',  # item.location_name, also for geocoding
 'Title': 'Toilet Rooms, Enclosed.',  # item.attributes['violations'] # M2M LOOKUP
 'Viol_Code': '6-202.14',   # item.attributes['violations'] - use this for the 'code'
 'dbo_Inspections_SS_View.Comments': ' ',  # item.attributes['comments']
 'dbo_Violations_SS_View.Comments': 'RESTROOM NEEDS SELF CLOSING DEVICE ', # item.attributes['comments']
 'Township': 'COLUMBIA'}  # use for geocoding?


from ebpub.db.models import Schema, SchemaField, NewsItem, Lookup
from ebdata.retrieval.scrapers.base import BaseScraper
import dateutil.parser
import logging
import sys

logger = logging.getLogger()

class ColumbiaRestaurantInspScraper(BaseScraper):

    def __init__(self, *args, **kwargs):
        super(ColumbiaRestaurantInspScraper, self).__init__(*args, **kwargs)
        self.schema = Schema.objects.get(slug='restaurants')
        self.insp_id_field = SchemaField.objects.get(schema=self.schema, name='inspection_id')

        self.violation_field = SchemaField.objects.get(schema=self.schema, name='violations')
        self.inspector_field = SchemaField.objects.get(schema=self.schema, name='inspector')
        self.est_field = SchemaField.objects.get(schema=self.schema, name='establishment_type')
        self.type_field = SchemaField.objects.get(schema=self.schema, name='inspection_type')


    def make_one(self, data):
        insp_id = int(data['insp_num'])
        insp_type = data['insp_type'].title()
        title='%s - %s, %s' % (data['est_name'].title(), insp_type, data['insp_date'])
        description = title
        location_name = '%(st_number)s %(st_dir)s %(st_name)s' % data
        location_name = location_name.strip()
        item_date=dateutil.parser.parse(data['insp_date']).date()
        location = self.geocode(location_name)['point']

        attributes = {
            'inspection_id': insp_id,
            'person_in_charge': data['person_in_charge'].title(),
	}
        # attributes['inspection_type'] = XXXlookup
        # attributes['establishment_type'] = XXXlookup
        # attributes['inspector'] = XXXlookup
        violation = Lookup.objects.get_or_create_lookup(
            self.violation_field, name=data['title'], code=data['viol_code'],
            make_text_slug=False)

        try:
            # insp_num is the unique identifier.
            ni = NewsItem.objects.filter(schema=self.schema).by_attribute(
                self.insp_id_field, insp_id).all()[0]
        except IndexError:
            ni = None
        ni = self.create_or_update(
            ni, attributes,
            title=title,
            description=description,
            item_date=item_date,
            location=location,
            location_name=location_name,
        )
        # It is really annoying that many-to-many lookups aren't abstracted better.
        # See #25
        violation_list = list((ni.attributes.get('violations') or '').split(','))
        if str(violation.id) not in violation_list:
            violation_list.append(str(violation.id))
            ni.attributes['violations'] = ','.join(violation_list)

    def parse_one(self, data):
        newdata = {}
        for key, val in data.items():
            # normalize funky keys to lowercase
            newdata[key.lower()] = val
        return newdata

    def update(self):
        for i, data in enumerate([merged]):
            data = self.parse_one(data)
            self.make_one(data)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    from optparse import OptionParser
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option(
        "--days-prior", help='how many days ago to start scraping', type="int",
        default=90
        )
    from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts
    add_verbosity_options(parser)

    options, args = parser.parse_args(argv)
    setup_logging_from_opts(options, logger)

    scraper = ColumbiaRestaurantInspScraper()
    scraper.update()
    return 0

if __name__ == '__main__':
    sys.exit(main())


