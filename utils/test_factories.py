# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

"""utils.test_factories.py -- Factory methods to create objects for testing
"""

import datetime
import itertools

from django.contrib.auth.hashers import make_password

from apps.auth.models import CustomUser as User
from apps.teams.models import (Project, Team, Task, TeamMember, TeamVideo,
                               TaskWorkflow)
from apps.videos.types import video_type_registrar
from apps.videos.models import Video, VideoUrl
from apps.videos.models import SubtitleVersion as OldSubtitleVersion
from apps.videos.models import SubtitleLanguage as OldSubtitleLanguage
from apps.subtitles.models import SubtitleLanguage
from apps.subtitles import pipeline
from apps.accountlinker.models import ThirdPartyAccount

create_user_counter = itertools.count()
def create_user(password=None, **kwargs):
    current_count = create_user_counter.next()
    defaults = {
        'username': 'test_user_%s' % current_count,
        'first_name': 'TestUser',
        'last_name': 'Number %s' % current_count,
        'email': 'test_user_%s@example.com' % current_count,
        'notify_by_email': True,
        'valid_email': True,
    }
    defaults.update(kwargs)
    if password is not None:
        defaults['password'] = make_password(password)
    else:
        defaults['password'] = make_password('password')
    return User.objects.create(**defaults)

create_video_counter = itertools.count()
def create_video(url=None, video_type='H', **kwargs):
    current_count = create_video_counter.next()
    defaults = {
        'title': 'Test Video %s' % current_count,
        'duration': 100,
        'allow_community_edits': False,
        'primary_audio_language_code': 'en',
    }
    defaults.update(kwargs)
    video =  Video.objects.create(**defaults)
    # make a video url for this video
    if url is None:
        url = 'http://example.com/videos/video-%s' % current_count
    video_url = VideoUrl.objects.create(url=url, type=video_type,
                                        primary=True, video=video)
    return video

create_team_counter = itertools.count()
def create_team(**kwargs):
    current_count = create_team_counter.next()
    defaults = {
        'name': 'Team %s' % current_count,
        'slug': 'team-%s' % current_count,
        'membership_policy': Team.OPEN,
    }
    defaults.update(kwargs)
    return Team.objects.create(**defaults)

def create_tasks_workflow(team, **kwargs):
    defaults = {
        'review_allowed': 30, # ADMIN_MUST_REVIEW
        'approve_allowed': 20 # ADMIN_MUST_APPROVE
    }
    defaults.update(kwargs)
    return TaskWorkflow.objects.create(team=team, **defaults)

def create_team_video(team=None, added_by=None, video=None, **kwargs):
    if team is None:
        team = create_team()
    if added_by is None:
        added_by = create_team_member(team).user
    if video is None:
        video = create_video(user=added_by)
    return TeamVideo.objects.create(team=team, video=video, added_by=added_by,
                                    **kwargs)

def create_team_member(team, user=None, **kwargs):
    if user is None:
        user = create_user()
    return TeamMember.objects.create(team=team, user=user, **kwargs)

def create_project(team, **kwargs):
    defaults = {
        'name':'Test Project',
    }
    defaults.update(kwargs)
    return Project.objects.create(team=team, **defaults)

def dxfp_sample(language_code):
    return ("""\
<tt xmlns="http://www.w3.org/ns/ttml" xml:lang="%s">
 <head>
 <metadata xmlns:ttm="http://www.w3.org/ns/ttml#metadata">
 <ttm:title/>
 <ttm:description/>
 <ttm:copyright/>
 </metadata>

 <styling xmlns:tts="http://www.w3.org/ns/ttml#styling">
 <style xml:id="amara-style" tts:color="white" tts:fontFamily="proportionalSansSerif" tts:fontSize="18px" tts:textAlign="center"/>
 </styling>

 <layout xmlns:tts="http://www.w3.org/ns/ttml#styling">
 <region xml:id="amara-subtitle-area" style="amara-style" tts:extent="560px 62px" tts:padding="5px 3px" tts:backgroundColor="black" tts:displayAlign="after"/>
 </layout>
 </head>
 <body region="amara-subtitle-area">
 <div><p begin="00:00:00,623" end="00:00:04,623">test subtitle</p>
 </div>
 </body>
</tt>""" % language_code)

def make_review_task(team_video, language_code, user, task_type='Translate',
                     sub_data=None):
    """Move a video through the tasks process to the review stage, then return
    that task.

    assumptions:
        - there are no Tasks or SubtitleVersions for this video+language
        - review is enabled for the team
    """
    team = team_video.team
    task = Task(team=team, team_video=team_video, assignee=None,
                language=language_code, type=Task.TYPE_IDS[task_type])
    task.save()
    v = pipeline.add_subtitles(team_video.video, language_code, sub_data,
                               complete=False, visibility='private')
    task.assignee = user
    task.new_subtitle_version = v
    return task.complete()

def make_approve_task(team_video, language_code, user, task_type='Translate',
                      subtitle_data=None):
    """Move a video through the tasks process to the approve stage, then return
    that task.

    assumptions:
        - there are no Tasks or SubtitleVersions for this video+language
        - approve is enabled for the team
    """
    team = team_video.team
    assert team.get_workflow().approve_allowed != 0
    task = Task(team=team, team_video=team_video, assignee=None,
         language=language_code, type=Task.TYPE_IDS[task_type])
    task.save()
    v = pipeline.add_subtitles(team_video.video, language_code, subtitle_data,
                               complete=False, visibility='private')
    task.assignee = user
    task.new_subtitle_version = v
    task = task.complete()
    if task.type == Task.TYPE_IDS['Review']:
        task.assignee = user
        task.approved = Task.APPROVED_IDS['Approved']
        return task.complete()
    else:
        # approve task
        return task

def create_third_party_account(vurl, **kwargs):
    defaults = {
        'oauth_access_token': '123', 
        'oauth_refresh_token': '',
        'username': vurl.owner_username,
        'type': vurl.type,
    }
    defaults.update(kwargs)
    return ThirdPartyAccount.objects.create(**defaults)

def create_old_subtitle_language(video, language_code='en', **kwargs):
    defaults = {
        'video': video,
        'is_original': True,
        'language': language_code,
        'created': datetime.datetime.now(),
    }
    defaults.update(kwargs)
    return OldSubtitleLanguage.objects.create(**defaults)

def create_old_subtitle_version(old_language, user, **kwargs):
    defaults = {
        'language': old_language,
        'datetime_started': datetime.datetime.now(),
        'user': user,
        'title': 'Title',
        'description': 'Description',
    }
    defaults.update(kwargs)
    return OldSubtitleVersion.objects.create(**defaults)

def bulk_subs(sub_data):
    """Create a bunch of videos/languages/versions

    sub_data is a dict of dicts containing the data to create the objects
    with:

    * sub_data maps video titles to language data
    * language data map language codes to a list of version data
    * version data is a dict containing kwargs to pass to
    pipeline.create_subtitles().

    returns a tuple of dicts:
    * a dict that maps video titles to videos
    * a dict that maps (title, language_code) to languages
    * a dict that maps (title, language_code, version_number) to versions
    """
    videos = {}
    langs = {}
    versions = {}
    for video_title, language_data in sub_data.items():
        video = create_video(title=video_title)
        videos[video_title] = video
        for language_code, version_data in language_data.items():
            lang = SubtitleLanguage.objects.create(
                video=video, language_code=language_code)
            langs[video_title, language_code] = lang
            for kwargs in version_data:
                v = pipeline.add_subtitles(video, language_code, None,
                                           **kwargs)
                versions[video_title, language_code, v.version_number] = v
    return videos, langs, versions
