# OBCOLUMBIA CONTEXT PROCESSORS
# Originally written by Peter, rewritten by Brice
# 3/26/14

from ebpub.utils.view_utils import get_schema_manager
from ebpub.db.models import LocationType, Location
from ebpub.db.models import NewsItem
from ebpub.neighbornews.models import NewsItemCreator
from ebpub.accounts.models import User
from ebpub.streets.models import Block
from ebpub.streets.models import Street
import time
import datetime
 
def allowed_schemas(request):
    allowed_schemas = get_schema_manager(request).all()
    return {'allowed_schemas': allowed_schemas}
    
def allowed_location_types(request):
	allowed_locations = LocationType.objects.filter(is_significant=True).order_by('slug').extra(select={'count': 'select count(*) from db_location where is_public=True and location_type_id=db_locationtype.id'})
	return {'allowed_location_types': allowed_locations}
    
def street_count(request):
	street_count = Street.objects.count()
	return {'street_count': street_count}
    
def todays_date(request):
	return {'todays_date': datetime.date.today()}
    
def allowed_locations(request):
	loc_list = Location.objects.filter(is_public=True)
	return {'allowed_locations': loc_list}