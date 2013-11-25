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

from django.contrib.auth.hashers import make_password
from django.template.defaultfilters import slugify
import factory

from auth.models import CustomUser, UserLanguage
from teams.models import (Team, TeamMember, TeamVideo, CollaborationWorkflow,
                          Collaboration, Collaborator)
from teams import workflow
from videos.models import VideoUrl, Video, VIDEO_TYPE_HTML5

class UserFactory(factory.DjangoModelFactory):
    FACTORY_FOR = CustomUser

    username = factory.Sequence(lambda n: 'testuser_%s' % n)
    first_name = 'Test'
    last_name = 'User'
    email = factory.LazyAttribute(lambda u: '%s@example.com' % u.username)
    notify_by_email = True
    valid_email = True
    password = make_password('password')

    @factory.post_generation
    def languages(self, create, extracted, **kwargs):
        if extracted:
            assert create
            for language_code in extracted:
                UserLanguage.objects.create(user=self, language=language_code)

class VideoUrlFactory(factory.DjangoModelFactory):
    FACTORY_FOR = VideoUrl

    type = VIDEO_TYPE_HTML5
    primary = True
    url = factory.Sequence(
        lambda n: 'http://example.com/videos/video-%s' % n)

class VideoFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Video
    title = factory.Sequence(lambda n: 'Test Video %s' % n)
    duration = 100
    allow_community_edits = False
    primary_audio_language_code = 'en'

    primary_video_url = factory.RelatedFactory(VideoUrlFactory, 'video')

class TeamFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Team

    name = factory.Sequence(lambda n: 'Team %s' % n)
    slug = factory.LazyAttribute(lambda t: slugify(t.name))
    membership_policy = Team.OPEN

    @classmethod
    def _generate(cls, create, attrs):
        team = super(TeamFactory, cls)._generate(create, attrs)
        if create:
            # this forces the default project to be created
            team.default_project
        return team

class CollaborationTeamFactory(TeamFactory):
    workflow_style = workflow.WORKFLOW_COLLABORATION

class TeamMemberFactory(factory.DjangoModelFactory):
    FACTORY_FOR = TeamMember

    role = TeamMember.ROLE_OWNER
    user = factory.SubFactory(UserFactory)

class TeamVideoFactory(factory.DjangoModelFactory):
    FACTORY_FOR = TeamVideo

    video = factory.SubFactory(VideoFactory)

    @factory.lazy_attribute
    def added_by(tv):
        member = TeamMemberFactory.create(team=tv.team)
        return member.user

class CollaborationWorkflowFactory(factory.DjangoModelFactory):
    FACTORY_FOR = CollaborationWorkflow

class CollaborationFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Collaboration

    team_video = factory.SubFactory(TeamVideoFactory,
                                    team=factory.SelfAttribute("..team"))

class CollaboratorFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Collaborator
