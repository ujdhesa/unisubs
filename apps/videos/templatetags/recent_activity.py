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

from django import template
from videos.models import Action
from django.conf import settings
from datetime import date
from django.utils.dateformat import format as date_format

register = template.Library()

LIMIT = settings.RECENT_ACTIVITIES_ONPAGE

@register.inclusion_tag('videos/_recent_activity.html')
def recent_activity(user):
    qs = Action.objects.for_user(user=user)

    return {
        'events': qs[:LIMIT],
        'user_info': user
    }

@register.inclusion_tag('videos/_video_activity.html')
def video_activity(video):
    qs = Action.objects.for_video(video)

    return {
        'events': qs[:LIMIT],
        'video': video
    }
