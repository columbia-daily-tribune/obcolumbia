from django.contrib.admin.sites import NotRegistered
from django.contrib.gis import admin
from ebpub.db.admin import SchemaAdmin
from ebpub.db.models import Schema
from obcolumbia.models import SchemaRestriction

class SchemaRestrictionInline(admin.TabularInline):
    model = SchemaRestriction.schemas.through
    extra = 1
    #fk_name = ""

class SchemaRestrictionAdmin(admin.ModelAdmin):
    filter_horizontal = ['schemas',]

class SchemaAdminPremium(SchemaAdmin):
    inlines = (SchemaAdmin.inlines or []) + [SchemaRestrictionInline]

try:
    admin.site.unregister(Schema)
except NotRegistered:
    pass # don't care

admin.site.register(Schema, SchemaAdminPremium)
admin.site.register(SchemaRestriction, SchemaRestrictionAdmin)
