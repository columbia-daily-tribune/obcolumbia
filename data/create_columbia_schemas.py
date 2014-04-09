from ebpub.db.models import Schema
from obcolumbia.models import create_fire_schema, create_police_schema

if __name__ == '__main__': 
    try:
        Schema.objects.get(slug='fire')
    except: 
        create_fire_schema()
        
    try:
        Schema.objects.get(slug='police')
    except: 
        create_police_schema()