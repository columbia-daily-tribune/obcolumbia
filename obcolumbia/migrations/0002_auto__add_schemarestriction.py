# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SchemaRestriction'
        db.create_table('obcolumbia_schemarestriction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(default='Active subscription required', max_length=256)),
            ('subscriber_status', self.gf('django.db.models.fields.CharField')(default='is_active', max_length=256, db_index=True)),
        ))
        db.send_create_signal('obcolumbia', ['SchemaRestriction'])

        # Adding M2M table for field schemas on 'SchemaRestriction'
        db.create_table('obcolumbia_schemarestriction_schemas', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('schemarestriction', models.ForeignKey(orm['obcolumbia.schemarestriction'], null=False)),
            ('schema', models.ForeignKey(orm['db.schema'], null=False))
        ))
        db.create_unique('obcolumbia_schemarestriction_schemas', ['schemarestriction_id', 'schema_id'])


    def backwards(self, orm):
        
        # Deleting model 'SchemaRestriction'
        db.delete_table('obcolumbia_schemarestriction')

        # Removing M2M table for field schemas on 'SchemaRestriction'
        db.delete_table('obcolumbia_schemarestriction_schemas')


    models = {
        'db.schema': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Schema'},
            'allow_charting': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'allow_comments': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'can_collapse': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_name': ('django.db.models.fields.CharField', [], {'default': "'Date'", 'max_length': '32'}),
            'date_name_plural': ('django.db.models.fields.CharField', [], {'default': "'Dates'", 'max_length': '32'}),
            'grab_bag': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'grab_bag_headline': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128', 'blank': 'True'}),
            'has_newsitem_detail': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'indefinite_article': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'intro': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'is_event': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'is_special_report': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_updated': ('django.db.models.fields.DateField', [], {}),
            'map_color': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'map_icon_url': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'min_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date(1970, 1, 1)'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'number_in_overview': ('django.db.models.fields.SmallIntegerField', [], {'default': '5'}),
            'plural_name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'short_description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'short_source': ('django.db.models.fields.CharField', [], {'default': "'One-line description of where this information came from.'", 'max_length': '128', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '32', 'db_index': 'True'}),
            'source': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'update_frequency': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64', 'blank': 'True'}),
            'uses_attributes_in_list': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'obcolumbia.schemarestriction': {
            'Meta': {'object_name': 'SchemaRestriction'},
            'description': ('django.db.models.fields.CharField', [], {'default': "'Active subscription required'", 'max_length': '256'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'schemas': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['db.Schema']", 'symmetrical': 'False'}),
            'subscriber_status': ('django.db.models.fields.CharField', [], {'default': "'is_active'", 'max_length': '256', 'db_index': 'True'})
        }
    }

    complete_apps = ['obcolumbia']
