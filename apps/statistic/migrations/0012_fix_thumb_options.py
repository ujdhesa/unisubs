# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        pass
    
    
    def backwards(self, orm):
        pass
    
    
    models = {
        'accountlinker.thirdpartyaccount': {
            'Meta': {'unique_together': "(('type', 'username'),)", 'object_name': 'ThirdPartyAccount'},
            'full_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'oauth_access_token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'oauth_refresh_token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'})
        },
        'auth.customuser': {
            'Meta': {'object_name': 'CustomUser', '_ormbases': ['auth.User']},
            'autoplay_preferences': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'award_points': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'biography': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'can_send_messages': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'full_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '63', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'is_partner': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'notify_by_email': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'notify_by_message': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'partner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['teams.Partner']", 'null': 'True', 'blank': 'True'}),
            'pay_rate_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '3', 'blank': 'True'}),
            'picture': ('utils.amazon.fields.S3EnabledImageField', [], {'max_length': '100', 'blank': 'True'}),
            'preferred_language': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'third_party_accounts': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'users'", 'symmetrical': 'False', 'to': "orm['accountlinker.ThirdPartyAccount']"}),
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'valid_email': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['videos.Video']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 11, 15, 15, 59, 11, 68160)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 11, 15, 15, 59, 11, 68082)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'statistic.emailsharestatistic': {
            'Meta': {'object_name': 'EmailShareStatistic'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.CustomUser']", 'null': 'True', 'blank': 'True'})
        },
        'statistic.fbsharestatistic': {
            'Meta': {'object_name': 'FBShareStatistic'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.CustomUser']", 'null': 'True', 'blank': 'True'})
        },
        'statistic.lasthitcountmigration': {
            'Meta': {'object_name': 'LastHitCountMigration'},
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '1', 'primary_key': 'True'})
        },
        'statistic.subtitleview': {
            'Meta': {'object_name': 'SubtitleView'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subtitle_language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subtitles.SubtitleLanguage']"})
        },
        'statistic.subtitleviewsperday': {
            'Meta': {'unique_together': "(('subtitle_language', 'date'),)", 'object_name': 'SubtitleViewsPerDay'},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subtitle_language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subtitles.SubtitleLanguage']"})
        },
        'statistic.subtitleviewspermonth': {
            'Meta': {'unique_together': "(('subtitle_language', 'date'),)", 'object_name': 'SubtitleViewsPerMonth'},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subtitle_language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subtitles.SubtitleLanguage']"})
        },
        'statistic.tweetersharestatistic': {
            'Meta': {'object_name': 'TweeterShareStatistic'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.CustomUser']", 'null': 'True', 'blank': 'True'})
        },
        'statistic.videohit': {
            'Meta': {'object_name': 'VideoHit'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videos.Video']"})
        },
        'statistic.videohitsperday': {
            'Meta': {'unique_together': "(('video', 'date'),)", 'object_name': 'VideoHitsPerDay'},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videos.Video']"})
        },
        'statistic.videohitspermonth': {
            'Meta': {'unique_together': "(('video', 'date'),)", 'object_name': 'VideoHitsPerMonth'},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['videos.Video']"})
        },
        'subtitles.subtitlelanguage': {
            'Meta': {'unique_together': "[('video', 'language_code')]", 'object_name': 'SubtitleLanguage'},
            'created': ('django.db.models.fields.DateTimeField', [], {}),
            'followers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'new_followed_languages'", 'blank': 'True', 'to': "orm['auth.CustomUser']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_forked': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'language_code': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'official_signoff_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'pending_signoff_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'pending_signoff_expired_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'pending_signoff_unexpired_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'subtitles_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'unofficial_signoff_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'newsubtitlelanguage_set'", 'to': "orm['videos.Video']"}),
            'writelock_owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'writelocked_newlanguages'", 'null': 'True', 'to': "orm['auth.CustomUser']"}),
            'writelock_session_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'writelock_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        'teams.application': {
            'Meta': {'unique_together': "(('team', 'user', 'status'),)", 'object_name': 'Application'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'history': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'applications'", 'to': "orm['teams.Team']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'team_applications'", 'to': "orm['auth.CustomUser']"})
        },
        'teams.partner': {
            'Meta': {'object_name': 'Partner'},
            'admins': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'managed_partners'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.CustomUser']"}),
            'can_request_paid_captions': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '250'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'teams.project': {
            'Meta': {'unique_together': "(('team', 'name'), ('team', 'slug'))", 'object_name': 'Project'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'null': 'True', 'blank': 'True'}),
            'guidelines': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'slug': ('django.db.models.fields.SlugField', [], {'db_index': 'True', 'max_length': '50', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['teams.Team']"}),
            'workflow_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'teams.team': {
            'Meta': {'object_name': 'Team'},
            'applicants': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'applicated_teams'", 'symmetrical': 'False', 'through': "orm['teams.Application']", 'to': "orm['auth.CustomUser']"}),
            'application_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'auth_provider_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '24', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'header_html_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'highlight': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_moderated': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_visible': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'last_notification_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'logo': ('utils.amazon.fields.S3EnabledImageField', [], {'max_length': '100', 'blank': 'True'}),
            'max_tasks_per_member': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'membership_policy': ('django.db.models.fields.IntegerField', [], {'default': '4'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '250'}),
            'notify_interval': ('django.db.models.fields.CharField', [], {'default': "'D'", 'max_length': '1'}),
            'page_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'partner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'teams'", 'null': 'True', 'to': "orm['teams.Partner']"}),
            'points': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'projects_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'subtitle_policy': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'task_assign_policy': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'task_expiration': ('django.db.models.fields.PositiveIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'third_party_accounts': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'teams'", 'symmetrical': 'False', 'to': "orm['accountlinker.ThirdPartyAccount']"}),
            'translate_policy': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'teams'", 'symmetrical': 'False', 'through': "orm['teams.TeamMember']", 'to': "orm['auth.CustomUser']"}),
            'video': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'intro_for_teams'", 'null': 'True', 'to': "orm['videos.Video']"}),
            'video_policy': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['videos.Video']", 'through': "orm['teams.TeamVideo']", 'symmetrical': 'False'}),
            'workflow_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'teams.teammember': {
            'Meta': {'unique_together': "(('team', 'user'),)", 'object_name': 'TeamMember'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'default': "'contributor'", 'max_length': '16', 'db_index': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'members'", 'to': "orm['teams.Team']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'team_members'", 'to': "orm['auth.CustomUser']"})
        },
        'teams.teamvideo': {
            'Meta': {'unique_together': "(('team', 'video'),)", 'object_name': 'TeamVideo'},
            'added_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.CustomUser']"}),
            'all_languages': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'partner_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['teams.Project']"}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['teams.Team']"}),
            'thumbnail': ('utils.amazon.fields.S3EnabledImageField', [], {'max_length': '100', 'null': 'True', 'thumb_sizes': '((288, 162), (120, 90))', 'blank': 'True'}),
            'video': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['videos.Video']", 'unique': 'True'})
        },
        'videos.video': {
            'Meta': {'object_name': 'Video'},
            'allow_community_edits': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'allow_video_urls_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'complete_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'edited': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'featured': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'followers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'followed_videos'", 'blank': 'True', 'to': "orm['auth.CustomUser']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_subtitled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'languages_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'meta_1_content': ('videos.metadata.MetadataContentField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'meta_1_type': ('videos.metadata.MetadataTypeField', [], {'null': 'True', 'blank': 'True'}),
            'meta_2_content': ('videos.metadata.MetadataContentField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'meta_2_type': ('videos.metadata.MetadataTypeField', [], {'null': 'True', 'blank': 'True'}),
            'meta_3_content': ('videos.metadata.MetadataContentField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'meta_3_type': ('videos.metadata.MetadataTypeField', [], {'null': 'True', 'blank': 'True'}),
            'moderated_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'moderating'", 'null': 'True', 'to': "orm['teams.Team']"}),
            'primary_audio_language_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '16', 'blank': 'True'}),
            's3_thumbnail': ('utils.amazon.fields.S3EnabledImageField', [], {'max_length': '100', 'thumb_sizes': '((288, 162), (120, 90))', 'blank': 'True'}),
            'small_thumbnail': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'thumbnail': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.CustomUser']", 'null': 'True', 'blank': 'True'}),
            'video_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'view_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'was_subtitled': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'writelock_owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'writelock_owners'", 'null': 'True', 'to': "orm['auth.CustomUser']"}),
            'writelock_session_key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'writelock_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        }
    }
    
    complete_apps = ['statistic']
