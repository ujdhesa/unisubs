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
from teams.models import (Collaboration, CollaborationLanguage,
                          CollaborationWorkflow)

# make Collaborator.ROLE values global for easier typing
SUBTITLER = Collaborator.SUBTITLER
REVIEWER = Collaborator.REVIEWER
APPROVER = Collaborator.APPROVER

class CollaborationLanguageTestCase(TestCase):
    def setUp(self):
        self.team = CollaborationTeamFactory.create()

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

class CollaborationStateTestCase(TestCase):
    def setUp(self):
        self.team = CollaborationTeamFactory.create()
        CollaborationWorkflowFactory.create(
            team=self.team,
            completion_policy=CollaborationWorkflow.COMPLETION_APPROVER)
        self.collaboration = CollaborationFactory.create(
            team=self.team)
        self.subtitler = TeamMemberFactory.create(team=self.team)
        self.reviewer = TeamMemberFactory.create(team=self.team)
        self.approver = TeamMemberFactory.create(team=self.team)

    def set_completion_policy(self, policy):
        self.team.workflow.completion_policy = policy
        self.team.workflow.save()

    def check_state(self, collaboration_state):
        self.assertEquals(self.collaboration.state, collaboration_state)

    def check_complete(self):
        self.assertEquals(self.collaboration.state, Collaboration.COMPLETE)

    def check_not_complete(self):
        self.assertNotEquals(self.collaboration.state, Collaboration.COMPLETE)

    def test_states_before_complete(self):
        self.check_state(Collaboration.NEEDS_SUBTITLER)

        self.collaboration.add_collaborator(self.subtitler, SUBTITLER)
        self.check_state(Collaboration.BEING_SUBTITLED)

        self.collaboration.mark_endorsed(self.subtitler)
        self.check_state(Collaboration.NEEDS_REVIEWER)

        self.collaboration.add_collaborator(self.reviewer, REVIEWER)
        self.check_state(Collaboration.BEING_REVIEWED)

        self.collaboration.mark_endorsed(self.reviewer)
        self.check_state(Collaboration.NEEDS_APPROVER)

        self.collaboration.add_collaborator(self.approver, APPROVER)
        self.check_state(Collaboration.BEING_APPROVED)

    def test_complete_anyone(self):
        self.set_completion_policy(CollaborationWorkflow.COMPLETION_ANYONE)
        self.check_not_complete()
        self.collaboration.add_collaborator(self.subtitler, SUBTITLER)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.subtitler)
        self.check_complete()

    def test_complete_review(self):
        self.set_completion_policy(CollaborationWorkflow.COMPLETION_REVIEWER)
        self.collaboration.add_collaborator(self.subtitler, SUBTITLER)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.subtitler)
        self.check_not_complete()
        self.collaboration.add_collaborator(self.reviewer, REVIEWER)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.reviewer)
        self.check_complete()

    def test_complete_approval(self):
        self.set_completion_policy(CollaborationWorkflow.COMPLETION_APPROVER)
        self.collaboration.add_collaborator(self.subtitler, SUBTITLER)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.subtitler)
        self.check_not_complete()
        self.collaboration.add_collaborator(self.reviewer, REVIEWER)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.reviewer)
        self.check_not_complete()
        self.collaboration.add_collaborator(self.approver, APPROVER)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.approver)
        self.check_complete()

class CollaborationTeamTestCase(TestCase):
    # Test the team-related fields of Collaboration.  This is a bit tricky
    # because the team that owns the team video may or may not actually be the
    # team that's working on the collaboration

    def setUp(self):
        self.team = CollaborationTeamFactory.create()
        self.collaboration = CollaborationFactory.create(
            team_video__team=self.team)

    def test_team_is_null_before_collaborators(self):
        self.assertEquals(self.collaboration.team, None)

    def test_owning_team_works_on_collaboration(self):
        member = TeamMemberFactory.create(team=self.team)
        self.collaboration.add_collaborator(member, SUBTITLER)
        self.assertEquals(self.collaboration.team, self.team)

    def test_other_team_works_on_collaboration(self):
        other_team = CollaborationTeamFactory.create()
        member = TeamMemberFactory.create(team=other_team)
        self.collaboration.add_collaborator(member, SUBTITLER)
        self.assertEquals(self.collaboration.team, other_team)

    def test_only_team_members_can_join(self):
        # test that only members of the team working on the collaboration can
        # join it.
        self.team.workflow.only_1_subtitler = False
        self.team.workflow.save()

        member = TeamMemberFactory.create(team=self.team)
        self.collaboration.add_collaborator(member, SUBTITLER)
        self.assertEquals(self.collaboration.team, self.team)

        # if a user from another team tries to join the collaboration, it
        # should fail.
        other_team = CollaborationTeamFactory.create()
        self.assertRaises(ValueError, self.collaboration.add_collaborator,
                          TeamMemberFactory.create(team=other_team),
                          SUBTITLER)

class CollaborationCreationTestCase(TestCase):
    def setUp(self):
        self.team = CollaborationTeamFactory.create()
        self.team_video = TeamVideoFactory.create(team=self.team)

    def check_collaboration_languages(self, team_video, correct_languages):
        collaborations = self.team_video.collaboration_set.all()
        self.assertEquals(set(c.language_code for c in collaborations),
                          set(correct_languages))

    def test_create_on_language_update(self):
        CollaborationLanguage.objects.update_for_team(self.team, ['en', 'es'])
        self.check_collaboration_languages(self.team_video, ['en', 'es'])

    def test_delete_on_language_update(self):
        CollaborationLanguage.objects.update_for_team(self.team, ['en', 'es'])
        self.check_collaboration_languages(self.team_video, ['en', 'es'])
        # when we change the language, we should delete collaborations
        CollaborationLanguage.objects.update_for_team(self.team, ['fr', 'de'])
        self.check_collaboration_languages(self.team_video, ['fr', 'de'])
        # but if collaborators have joined, we shouldn't delete them
        user = TeamMemberFactory.create(team=self.team)
        collaboration = self.team_video.collaboration_set.get(
            language_code='fr')
        collaboration.add_collaborator(user, Collaborator.SUBTITLER)
        CollaborationLanguage.objects.update_for_team(self.team, ['pt-br'])
        self.check_collaboration_languages(self.team_video, ['fr', 'pt-br'])

    def test_create_on_new_teamvideo(self):
        CollaborationLanguage.objects.update_for_team(self.team, ['en', 'es'])
        new_team_video = TeamVideoFactory.create(team=self.team)
        self.check_collaboration_languages(new_team_video, ['en', 'es'])
