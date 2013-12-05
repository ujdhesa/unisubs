# -*- coding: utf-8 -*-
# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.
import simplejson as json
from django.contrib.auth.decorators import login_required

from videos.models import Video
from teams.models import Task
from subtitles import shims
from subtitles.models import SubtitleLanguage, SubtitleVersion
from subtitles.templatetags.new_subtitles_tags import visibility_display

from django.http import HttpResponse
from django.db.models import Count
from django.contrib import messages
from django.template import RequestContext
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.shortcuts import render_to_response, get_object_or_404, redirect


from teams.permissions import can_add_version, can_assign_task


def _version_data(version):
    '''
    Creates a dict with version info, suitable for encoding
    into json and bootstrapping the editor.
    '''
    return {
        'metadata': version.get_metadata(),
        'subtitles': version.get_subtitles().to_xml(),
        'title': version.title,
        'description': version.description,
    }

def _language_data(language, editing_version, translated_from_version,
                   base_language):
    '''
    Creates a dict with language info, suitable for encoding
    into json and bootstrapping the editor. Includes
    the version data for the version being edited and the
    original translation source, if any.
    '''
    versions_data = []

    versions = list(language.subtitleversion_set.full())
    for i, version in enumerate(versions):
        version_data = {
            'version_no':version.version_number,
            'visibility': visibility_display(version),
        }
        if editing_version == version:
            version_data.update(_version_data(version))
        elif translated_from_version == version:
            version_data.update(_version_data(version))
        elif (language.language_code == base_language and
              i == len(versions) - 1):
            version_data.update(_version_data(version))

        versions_data.append(version_data)


    subtitle_language = editing_version.subtitle_language if editing_version else ''

    return {
        'translatedFrom': translated_from_version and {
            'language_code': translated_from_version.subtitle_language.language_code,
            'version_number': translated_from_version.version_number,
        },
        'editingLanguage': language == subtitle_language,
        'language_code': language.language_code,
        'name': language.get_language_code_display(),
        'pk': language.pk,
        'numVersions': language.num_versions,
        'versions': versions_data,
        'subtitles_complete': language.subtitles_complete,
        'is_rtl': language.is_rtl(),
        'is_original': language.is_primary_audio_language()
    }

def regain_lock(request, video_id, language_code):
    video = get_object_or_404(Video, video_id=video_id)
    language = video.subtitle_language(language_code)

    if not language.can_writelock(request.browser_id):
        return HttpResponse(json.dumps({'ok': False}))

    language.writelock(request.user, request.browser_id, save=True)
    return HttpResponse(json.dumps({'ok': True}))

@login_required
@require_POST
def release_lock(request, video_id, language_code):
    video = get_object_or_404(Video, video_id=video_id)
    language = video.subtitle_language(language_code)

    if language.can_writelock(request.browser_id):
        language.release_writelock()

    return HttpResponse(json.dumps({'url': reverse('videos:video', args=(video_id,))}))

def assign_task_for_editor(video, language_code, user):
    team_video = video.get_team_video()
    if team_video is None:
        return None
    task_set = team_video.task_set.incomplete().filter(language=language_code)
    tasks = list(task_set[:1])
    if tasks:
        task = tasks[0]
        if task.assignee is None and can_assign_task(task, user):
            task.assignee = user
            task.save()

        if task.assignee != user:
            return _("Another user is currently performing "
                     "the %s task for these subtitles" %
                     task.get_type_display())


def get_task_for_editor(video, language_code):
    team_video = video.get_team_video()
    if team_video is None:
        return None
    task_set = team_video.task_set.incomplete().filter(language=language_code)
    # 2533: We can get 2 review tasks if we include translate/transcribe tasks
    # in the results.  This is because when we have a task id and the user
    # clicks endorse, we do the following:
    #    - save the subtitles
    #    - save the task, setting subtitle_version to the version that we just
    #    saved
    #
    # However, the task code creates a task on both of those steps.  I'm not
    # sure exactly what the old editor does to make this not happen, but it's
    # safest to just not send task_id in that case
    task_set = task_set.filter(type__in=(Task.TYPE_IDS['Review'],
                                         Task.TYPE_IDS['Approve']))
    # This assumes there is only 1 incomplete tasks at once, hopefully that's
    # a good enough assumption to hold until we dump tasks for the collae
    # model.
    tasks = list(task_set[:1])
    if tasks:
        return tasks[0]
    else:
        return None

def get_collaborator_for_editor(request, video, language_code):
    """Get a Collaborator object to for the subtitle editor

    :raises PermissionDenied: user can't edit the collaboration
    :returns: Collaboration or None
    """
    if 'collaboration_id' not in request.GET:
        return None
    try:
        collaboration = video.get_team_video().collaboration_set.get(
            language_code=language_code)
    except ObjectDoesNotExist:
        return None

    try:
        collaborator = collaboration.collaborators.get(user=request.user)
    except ObjectDoesNotExist:
        raise PermissionDenied("You can't edit the collaboration")

    # set collaboration so that we don't have to query it again
    collaborator.collaboration = collaboration
    return collaborator

def old_editor(request, video_id, language_code):
    video = get_object_or_404(Video, video_id=video_id)
    language = get_object_or_404(SubtitleLanguage, video=video,
                                 language_code=language_code)
    return redirect(shims.get_widget_url(language,
                                         request.GET.get('mode'),
                                         request.GET.get('task_id')))

@login_required
def subtitle_editor(request, video_id, language_code):
    '''
    Renders the subtitle-editor page, with all data neeeded for the UI
    as a json object on the html document.
    If the language does not exist, it will create one and lock it.
    Also decides what source version should be shown initially (if
    it is a translation).
    '''
    # FIXME: permissions
    video = get_object_or_404(Video, video_id=video_id)
    base_language = request.GET.get('base-language')

    try:
        editing_language = video.newsubtitlelanguage_set.get(language_code=language_code)
    except SubtitleLanguage.DoesNotExist:
        editing_language = SubtitleLanguage(video=video,language_code=language_code)

    if not editing_language.can_writelock(request.browser_id):
        messages.error(request, _("You can't edit this subtitle because it's locked"))
        return redirect(video)

    collaborator = task = None
    try:
        collaborator = get_collaborator_for_editor(request, video,
                                                   language_code)
    except PermissionDenied, e:
        messages.error(request, e.msg)
        return redirect(video)

    if collaborator is None:
        error_message = assign_task_for_editor(video, language_code, request.user)
        if error_message:
            messages.error(request, error_message)
            return redirect(video)
        task = get_task_for_editor(video, language_code)

    check_result = can_add_version(request.user, video, language_code)
    if not check_result:
        messages.error(request, check_result.message)
        return redirect(video)

    editing_language.writelock(request.user, request.browser_id, save=True)

    # if this language is a translation, show both
    editing_version = editing_language.get_tip(public=False)
    # we ignore forking because even if it *is* a fork, we still want to show
    # the user the rererence languages:
    translated_from_version = editing_language.\
        get_translation_source_version(ignore_forking=True)

    languages = video.newsubtitlelanguage_set.annotate(
        num_versions=Count('subtitleversion'))

    video_urls = []
    for v in video.get_video_urls():
        video_urls.append(v.url)

    editor_data = {
        'canSync': bool(request.GET.get('canSync', True)),
        'canAddAndRemove': bool(request.GET.get('canAddAndRemove', True)),
        # front end needs this to be able to set the correct
        # api headers for saving subs
        'authHeaders': {
            'x-api-username': request.user.username,
            'x-apikey': request.user.get_api_key()
        },
        'video': {
            'id': video.video_id,
            'title': video.title,
            'description': video.description,
            'primaryVideoURL': video.get_video_url(),
            'videoURLs': video_urls,
            'metadata': video.get_metadata(),
        },
        'editingVersion': {
            'languageCode': editing_language.language_code,
            'versionNumber': (editing_version.version_number
                              if editing_version else None),
        },
        'baseLanguage': base_language,
        'languages': [_language_data(lang, editing_version,
                                     translated_from_version, base_language)
                      for lang in languages],
        'languageCode': request.LANGUAGE_CODE,
        'oldEditorURL': editing_language.get_widget_url(),
        'savedNotes': request.GET.get('saved-notes', '')
    }


    if task:
        editor_data['task_id'] = task.id
        if not editor_data['savedNotes']:
            editor_data['savedNotes'] = task.body
        editor_data['task_needs_pane'] = task.get_type_display() in ('Review', 'Approve')
        editor_data['team_slug'] = task.team.slug

    if collaborator:
        editor_data['collaboration_id'] = collaborator.collaboration_id

    return render_to_response("subtitles/subtitle-editor.html", {
        'video': video,
        'language': editing_language,
        'other_languages': languages,
        'version': editing_version,
        'translated_from_version': translated_from_version,
        'task': task,
        'editor_data': json.dumps(editor_data, indent=4)
    }, context_instance=RequestContext(request))

