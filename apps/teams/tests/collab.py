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

from __future__ import absolute_import

from django.test import TestCase

from utils.factories import *
from teams.models import CollaborationLanguage, CollaborationWorkflow

class CollaborationLanguageTestCase(TestCase):
    def setUp(self):
        self.team = TeamFactory.create()

    def check_languages(self, correct_languages):
        collab_langs = CollaborationLanguage.objects.for_team(self.team)
        self.assertEquals(set([cl.language_code for cl in collab_langs]),
                          set(correct_languages))
        for cl in collab_langs:
            self.assertEquals(cl.team_id, self.team.id)
            self.assertEquals(cl.project_id, None)

    def check_languages_for_member(self, member, correct_languages):
        self.assertEquals(
            set(CollaborationLanguage.objects.languages_for_member(member)),
            set(correct_languages))

    def update_languages(self, languages):
        CollaborationLanguage.objects.update_for_team(self.team, languages)

    def test_languages_for_team(self):
        self.check_languages([])
        self.update_languages(['en', 'fr', 'de'])
        self.check_languages(['en', 'fr', 'de'])
        self.update_languages(['en', 'pt-br'])
        self.check_languages(['en', 'pt-br'])

    def test_languages_for_user(self):
        user = UserFactory.create(languages=['en', 'fr', 'pt-br'])
        member = TeamMemberFactory.create(team=self.team, user=user)
        # when no languages are defined for the team, languages_for_member()
        # should return all languages for the user
        self.check_languages_for_member(member, ['en', 'fr', 'pt-br'])
        # when languages are defined for the team, languages_for_member()
        # should return the intersection of the team's languages and the
        # user's language
        self.update_languages(['en', 'fr'])
        self.check_languages_for_member(member, ['en', 'fr'])


class CollaborationStateLabelTestCase(TestCase):
    def setUp(self):
        self.team = TeamFactory.create(workflow_style="C")
        CollaborationWorkflowFactory.create(
            team=self.team,
            completion_policy=CollaborationWorkflow.COMPLETION_APPROVER)
        self.collaboration = CollaborationFactory.create(
            team=self.team)
        self.subtitler = TeamMemberFactory.create(team=self.team).user
        self.reviewer = TeamMemberFactory.create(team=self.team).user
        self.approver = TeamMemberFactory.create(team=self.team).user

    def make_collaborator(self, user, role):
        return CollaboratorFactory.create(collaboration=self.collaboration,
                                          user=user, role=role)

    def set_completion_policy(self, policy):
        self.team.workflow.completion_policy = policy
        self.team.workflow.save()

    def check_state_label(self, state_label):
        self.collaboration.clear_cached_collaborators()
        self.assertEquals(unicode(self.collaboration.state_label()),
                          state_label)

    def check_complete(self):
        self.check_state_label('complete')

    def check_not_complete(self):
        self.collaboration.clear_cached_collaborators()
        self.assertNotEquals(unicode(self.collaboration.state_label()),
                             'complete')

    def test_labels_before_complete(self):
        self.check_state_label('needs subtitler')

        subtitle_collaborator = self.make_collaborator(self.subtitler, 'S')
        self.check_state_label('being subtitled')

        subtitle_collaborator.mark_endorsed()
        self.check_state_label('needs reviewer')

        review_collaborator = self.make_collaborator(self.reviewer, 'R')
        self.check_state_label('being reviewed')

        review_collaborator.mark_endorsed()
        self.check_state_label('needs approver')

        approve_collaborator = self.make_collaborator(self.approver, 'A')
        self.check_state_label('being approved')

    def test_complete_anyone(self):
        self.set_completion_policy(CollaborationWorkflow.COMPLETION_ANYONE)
        self.check_not_complete()
        subtitle_collaborator = self.make_collaborator(self.subtitler, 'S')
        self.check_not_complete()
        subtitle_collaborator.mark_endorsed()
        self.check_complete()

    def test_complete_review(self):
        self.set_completion_policy(CollaborationWorkflow.COMPLETION_REVIEWER)
        subtitle_collaborator = self.make_collaborator(self.subtitler, 'S')
        self.check_not_complete()
        subtitle_collaborator.mark_endorsed()
        self.check_not_complete()
        review_collaborator = self.make_collaborator(self.reviewer, 'R')
        self.check_not_complete()
        review_collaborator.mark_endorsed()
        self.check_complete()

    def test_complete_approval(self):
        self.set_completion_policy(CollaborationWorkflow.COMPLETION_APPROVER)
        subtitle_collaborator = self.make_collaborator(self.subtitler, 'S')
        self.check_not_complete()
        subtitle_collaborator.mark_endorsed()
        self.check_not_complete()
        review_collaborator = self.make_collaborator(self.reviewer, 'R')
        self.check_not_complete()
        review_collaborator.mark_endorsed()
        self.check_not_complete()
        approve_collaborator = self.make_collaborator(self.approver, 'A')
        self.check_not_complete()
        approve_collaborator.mark_endorsed()
        self.check_complete()
