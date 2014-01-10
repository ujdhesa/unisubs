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
from datetime import datetime

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from factory import make_factory

from teams.models import (Collaboration, CollaborationLanguage,
                          CollaborationWorkflow)
from teams.permissions_const import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_CONTRIBUTOR,
)
from utils.factories import *
from utils.test_utils import reload_model, patch_for_test

# make Collaborator.ROLE values global for easier typing
SUBTITLER = Collaborator.SUBTITLER
REVIEWER = Collaborator.REVIEWER
APPROVER = Collaborator.APPROVER

class CollaborationTestCase(TestCase):
    def setUp(self):
        self.team = CollaborationTeamFactory()
        self.make_collaboration = make_factory(CollaborationFactory,
                                               team_video__team=self.team,
                                               language_code='en')
        self.make_member = make_factory(TeamMemberFactory, team=self.team)
        self.contributor = self.make_member(role=ROLE_CONTRIBUTOR)
        self.manager = self.make_member(role=ROLE_MANAGER)
        self.member1 = self.make_member(role=ROLE_ADMIN)
        self.member2 = self.make_member(role=ROLE_ADMIN)
        self.member3 = self.make_member(role=ROLE_ADMIN)

    def update_workflow(self, **attrs):
        for name, value in attrs.items():
            setattr(self.team.workflow, name, value)
        self.team.workflow.save()

class CollaborationLanguageTestCase(CollaborationTestCase):
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

class CollaborationStateTestCase(CollaborationTestCase):
    def setUp(self):
        CollaborationTestCase.setUp(self)
        self.collaboration = self.make_collaboration()

    def check_state(self, collaboration_state):
        self.assertEquals(self.collaboration.state, collaboration_state)

    def check_complete(self):
        self.assertEquals(self.collaboration.state, Collaboration.COMPLETE)
        for collaborator in self.collaboration.collaborators.all():
            self.assertEquals(collaborator.complete, True)

    def check_not_complete(self):
        self.assertNotEquals(self.collaboration.state, Collaboration.COMPLETE)
        for collaborator in self.collaboration.collaborators.all():
            self.assertEquals(collaborator.complete, False)

    def test_states_before_complete(self):
        self.check_state(Collaboration.NEEDS_SUBTITLER)

        self.collaboration.join(self.member1)
        self.check_state(Collaboration.BEING_SUBTITLED)

        self.collaboration.mark_endorsed(self.member1)
        self.check_state(Collaboration.NEEDS_REVIEWER)

        self.collaboration.join(self.member2)
        self.check_state(Collaboration.BEING_REVIEWED)

        self.collaboration.mark_endorsed(self.member2)
        self.check_state(Collaboration.NEEDS_APPROVER)

        self.collaboration.join(self.member3)
        self.check_state(Collaboration.BEING_APPROVED)

    def test_complete_anyone(self):
        self.update_workflow(
            completion_policy=CollaborationWorkflow.COMPLETION_ANYONE)
        self.check_not_complete()
        self.collaboration.join(self.member1)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.member1)
        self.check_complete()

    def test_complete_review(self):
        self.update_workflow(
            completion_policy=CollaborationWorkflow.COMPLETION_REVIEWER)
        self.collaboration.join(self.member1)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.member1)
        self.check_not_complete()
        self.collaboration.join(self.member2)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.member2)
        self.check_complete()

    def test_complete_approval(self):
        self.update_workflow(
            completion_policy=CollaborationWorkflow.COMPLETION_APPROVER)
        self.collaboration.join(self.member1)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.member1)
        self.check_not_complete()
        self.collaboration.join(self.member2)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.member2)
        self.check_not_complete()
        self.collaboration.join(self.member3)
        self.check_not_complete()
        self.collaboration.mark_endorsed(self.member3)
        self.check_complete()

class CollaborationProjectTestCase(CollaborationTestCase):
    def setUp(self):
        CollaborationTestCase.setUp(self)
        self.project = ProjectFactory(team=self.team)
        self.project2 = ProjectFactory(team=self.team)

    def test_set_project(self):
        tv = TeamVideoFactory.create(team=self.team, project=self.project)
        collaboration = CollaborationFactory(team_video=tv)
        self.assertEquals(collaboration.project, self.project)

    def test_update_project(self):
        tv = TeamVideoFactory.create(team=self.team, project=self.project)
        collaboration = CollaborationFactory(team_video=tv)
        tv.project = self.project2
        tv.save()
        collaboration = reload_model(collaboration)
        self.assertEquals(collaboration.project, self.project2)

class CollaborationTeamTestCase(CollaborationTestCase):
    # Test the team-related fields of Collaboration.  This is a bit tricky
    # because the team that owns the team video may or may not actually be the
    # team that's working on the collaboration
    def setUp(self):
        CollaborationTestCase.setUp(self)
        self.collaboration = self.make_collaboration()

    def test_team_is_null_before_collaborators(self):
        self.assertEquals(self.collaboration.team, None)

    def test_owning_team_works_on_collaboration(self):
        member = TeamMemberFactory.create(team=self.team)
        self.collaboration.join(member)
        self.assertEquals(self.collaboration.team, self.team)

    def test_other_team_works_on_collaboration(self):
        other_team = CollaborationTeamFactory.create()
        self.collaboration.team_video.project.shared_teams.add(other_team)
        member = TeamMemberFactory.create(team=other_team)
        self.collaboration.join(member)
        self.assertEquals(self.collaboration.team, other_team)

    def test_only_team_members_can_join(self):
        # test that only members of the team working on the collaboration can
        # join it.
        self.update_workflow(only_1_subtitler=False)

        member = TeamMemberFactory.create(team=self.team)
        self.collaboration.join(member)
        self.assertEquals(self.collaboration.team, self.team)

        # if a user from another team tries to join the collaboration, it
        # should fail.
        other_team = CollaborationTeamFactory.create()
        self.assertRaises(ValueError, self.collaboration.join,
                          TeamMemberFactory.create(team=other_team))

class CollaborationCreationTestCase(CollaborationTestCase):
    def setUp(self):
        CollaborationTestCase.setUp(self)
        self.team_video = TeamVideoFactory.create(team=self.team)

    def check_collaboration_languages(self, team_video, correct_languages):
        collaborations = team_video.collaboration_set.all()
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
        collaboration.join(user)
        CollaborationLanguage.objects.update_for_team(self.team, ['pt-br'])
        self.check_collaboration_languages(self.team_video, ['fr', 'pt-br'])

    def test_create_on_new_teamvideo(self):
        CollaborationLanguage.objects.update_for_team(self.team, ['en', 'es'])
        new_team_video = TeamVideoFactory.create(team=self.team)
        self.check_collaboration_languages(new_team_video, ['en', 'es'])

class JoinCollaborationTest(CollaborationTestCase):
    def check_anyone_can_join(self, collaboration):
        self.assertEquals(collaboration.can_join(self.contributor), True)
        self.assertEquals(collaboration.can_join(self.manager), True)

    def check_manager_can_join(self, collaboration):
        self.assertEquals(collaboration.can_join(self.contributor), False)
        self.assertEquals(collaboration.can_join(self.manager), True)

    def check_no_one_can_join(self, collaboration):
        self.assertEquals(collaboration.can_join(self.contributor), False)
        self.assertEquals(collaboration.can_join(self.manager), False)

    def test_can_join(self):
        # initially anyone can join as a subtitler
        collaboration = self.make_collaboration()
        self.check_anyone_can_join(collaboration)
        # after there's a subtitler, anyone can join, but only if
        # only_1_subtitler is False
        collaboration.join(self.member1)
        self.check_no_one_can_join(collaboration)
        self.update_workflow(only_1_subtitler=False)
        self.check_anyone_can_join(collaboration)
        # after the subtitler endorses, anyone can join as a reviewer.
        collaboration.mark_endorsed(self.member1)
        self.check_anyone_can_join(collaboration)
        # after there's a reviewer, anyone can join but only if
        # only_1_reviewer is False
        collaboration.join(self.member2)
        self.check_no_one_can_join(collaboration)
        self.update_workflow(only_1_reviewer=False)
        self.check_anyone_can_join(collaboration)
        # after the reviewer endorses, only managers can join as an approver
        collaboration.mark_endorsed(self.member2)
        self.check_manager_can_join(collaboration)
        # after a there's an approver, managers can join if only_1_approver is
        # False
        collaboration.join(self.member3)
        self.check_no_one_can_join(collaboration)
        self.update_workflow(only_1_approver=False)
        self.check_manager_can_join(collaboration)
        # after the approver endorses, the collaboration is complete and no
        # one can join.
        collaboration.mark_endorsed(self.member3)
        self.check_no_one_can_join(collaboration)

    def test_existing_collaborators_cant_join(self):
        collaboration = self.make_collaboration(
            endorsed_subtitler=self.member1,
            endorsed_reviewer=self.member2,
            approver=self.member3)
        self.assertEquals(collaboration.can_join(self.member1), False)
        self.assertEquals(collaboration.can_join(self.member2), False)
        self.assertEquals(collaboration.can_join(self.member3), False)

    def test_can_join_for_non_members(self):
        # normally other members can't join
        other_team = CollaborationTeamFactory()
        other_team_member = TeamMemberFactory(team=other_team)
        collaboration = self.make_collaboration()
        self.assertEquals(collaboration.can_join(other_team_member), False)
        # but they can if the team video is part of a shared project
        collaboration.team_video.project.shared_teams.add(other_team)
        self.assertEquals(collaboration.can_join(other_team_member), True)
        # but only if the collaboration hasn't been started by another team
        collaboration.join(self.member1)
        self.assertEquals(collaboration.can_join(other_team_member), False)

    @patch_for_test('teams.models.Collaboration.can_join')
    def test_join_calls_can_join(self, mock_can_join):
        mock_can_join.return_value = False
        collaboration = self.make_collaboration()
        self.assertRaises(ValueError, collaboration.join, self.member1)
        mock_can_join.assert_called_with(self.member1)

class EndorseCollaborationTest(CollaborationTestCase):
    def test_mark_endorsed(self):
        collaboration = self.make_collaboration()
        collaboration.join(self.member1)
        collaboration.mark_endorsed(self.member1)
        self.assertEquals(collaboration.state, Collaboration.NEEDS_REVIEWER)

    def test_mark_endorsed_by_non_collaborator(self):
        collaboration = self.make_collaboration()
        collaboration.join(self.member1)
        self.assertRaises(PermissionDenied, collaboration.mark_endorsed,
                          self.member2)

    def test_mark_endorsed_can_accept_user_object(self):
        collaboration = self.make_collaboration()
        collaboration.join(self.member1)
        collaboration.mark_endorsed(self.member1.user)
        self.assertEquals(collaboration.state, Collaboration.NEEDS_REVIEWER)

    def test_remove_endorsement(self):
        collaboration = self.make_collaboration()
        collaborator = collaboration.join(self.member1)
        collaboration.mark_endorsed(self.member1)
        # test a member removing their endorsement
        collaboration.remove_endorsement(self.member1)
        self.assertEquals(collaborator.endorsed, False)
        self.assertEquals(collaboration.state, Collaboration.BEING_SUBTITLED)
        # member1 should be able to re-endorse at this point
        collaboration.mark_endorsed(self.member1)
        self.assertEquals(reload_model(collaborator).endorsed, True)
        self.assertEquals(collaboration.state, Collaboration.NEEDS_REVIEWER)
        # if the reviewer remove their endorsement, then it should remove all
        # other endorsements as well
        collaboration.join(self.member2)
        collaboration.mark_endorsed(self.member2)
        self.assertEquals(collaboration.state, Collaboration.NEEDS_APPROVER)
        collaboration.remove_endorsement(self.member2)
        self.assertEquals(collaboration.state, Collaboration.BEING_SUBTITLED)
        # users who aren't part of the collaboration shouldn't be able to
        # remove the endorsements
        self.assertRaises(PermissionDenied, collaboration.remove_endorsement,
                          self.member3)

class CollaborationManagerDashboardTestCase(CollaborationTestCase):
    def setUp(self):
        CollaborationTestCase.setUp(self)
        self.dashboard_viewer = TeamMemberFactory(
            team=self.team, user__languages=['en', 'es', 'fr'])
        # make another team that member.user is also a member of.  We
        # shouldn't return collaborations for this team, even though the user
        # may match.
        self.other_team = CollaborationTeamFactory()
        self.other_team_member = TeamMemberFactory(
            team=self.other_team, user=self.dashboard_viewer.user)
        # make a project that's shared with a third team.  We should return
        # collaborations for this project if they haven't been started yet.
        self.shared_project = ProjectFactory.create(shared_teams=[self.team])

    def check_joined(self, correct_collaborations):
        collaborations_and_collaborators = [
            (c, c.collaborators.get(user=self.dashboard_viewer.user))
            for c in correct_collaborations
        ]
        for_dashboard = Collaboration.objects.for_dashboard(
            self.dashboard_viewer)
        self.assertEquals(set(for_dashboard['joined']),
                          set(collaborations_and_collaborators))

    def check_can_join(self, correct_collaborations):
        for_dashboard = Collaboration.objects.for_dashboard(
            self.dashboard_viewer)
        self.assertEquals(set(for_dashboard['can_join']),
                          set(correct_collaborations))
        self.check_can_join_order(for_dashboard['can_join'])

    def check_can_join_order(self, collaborations):
        if not collaborations:
            return
        # check that the collaborations are ordered by state
        state_order = [
            Collaboration.NEEDS_SUBTITLER,
            Collaboration.BEING_SUBTITLED,
            Collaboration.NEEDS_REVIEWER,
            Collaboration.BEING_REVIEWED,
            Collaboration.NEEDS_APPROVER,
            Collaboration.BEING_APPROVED,
        ]
        last_index = state_order.index(collaborations[0].state)
        for i, collaboration in enumerate(collaborations[1:]):
            if (state_order.index(collaboration.state) < last_index):
                raise AssertionError(
                    "Collabortions out of order (%s followed by %s)" % (
                        collaboration[i-1].get_state_display(),
                        collaboration[i].get_state_display()))

    def test_joined(self):
        # we should return these because dashboard_viewer is part of the
        # collaboration
        joined = [
            self.make_collaboration(subtitler=self.dashboard_viewer),
            self.make_collaboration(endorsed_subtitler=self.member1,
                                    reviewer=self.dashboard_viewer),
            self.make_collaboration(endorsed_subtitler=self.member1,
                                    endorsed_reviewer=self.member2,
                                    approver=self.dashboard_viewer)
        ]
        # we shouldn't return these because dashboard_viewer is not part of
        # the collaboration
        self.make_collaboration(subtitler=self.member1)
        self.make_collaboration(endorsed_subtitler=self.member1,
                                endorsed_reviewer=self.member2)
        # We shouldn't return this one because the collaboration is complete
        self.make_collaboration(endorsed_subtitler=self.dashboard_viewer,
                                endorsed_reviewer=self.member1,
                                endorsed_approver=self.member2)
        # We shouldn't return this one because it's for another team
        self.make_collaboration(team_video__team=self.other_team,
                                endorsed_subtitler=self.other_team_member)
        self.check_joined(joined)

    def test_can_join(self):
        # Collaborations that the user can start subtitling
        needs_subtitler = [
            self.make_collaboration(),
            self.make_collaboration(language_code='es'),
            self.make_collaboration(language_code='fr'),
            self.make_collaboration(
                team_video__team=self.shared_project.team,
                team_video__project=self.shared_project,
                language_code='en')
        ]
        # Collaborations that the user can join
        needs_reviewer = [
            self.make_collaboration(endorsed_subtitler=self.member1),
            self.make_collaboration(language_code='es',
                                    endorsed_subtitler=self.member1),
        ]

        needs_approver = [
            self.make_collaboration(endorsed_subtitler=self.member1,
                                    endorsed_reviewer=self.member2),
            self.make_collaboration(language_code='fr',
                                    endorsed_subtitler=self.member1,
                                    endorsed_reviewer=self.member2),
        ]
        # Collaborations the user can join depending on the value of the
        # only_1_subtitler/only_1_reviewer/only_1_approver
        can_join_if_not_only_1 = [
            self.make_collaboration(subtitler=self.member1),
            self.make_collaboration(endorsed_subtitler=self.member1,
                                    reviewer=self.member2),
            self.make_collaboration(endorsed_subtitler=self.member1,
                                    endorsed_reviewer=self.member2,
                                    approver=self.member3),
        ]
        # can't join this one because it's owned by a different team
        self.make_collaboration(team_video__team=self.other_team)
        # can't join it's not for a preferred language
        self.make_collaboration(language_code='de')
        self.make_collaboration(language_code='pt-br',
                                endorsed_subtitler=self.member1)
        # can't join because dashboard_viewer has already joined
        self.make_collaboration(endorsed_subtitler=self.dashboard_viewer)
        # can't joint because it's complete
        self.make_collaboration(endorsed_subtitler=self.member1,
                                endorsed_reviewer=self.member2,
                                endorsed_approver=self.member3)
        # okay, let's check the collaborations returned
        self.check_can_join(needs_subtitler + needs_reviewer + needs_approver)
        # non-managers can only join as a reviewer, not an approver
        self.dashboard_viewer.role = ROLE_CONTRIBUTOR
        self.dashboard_viewer.save()
        self.check_can_join(needs_subtitler + needs_reviewer)
        # test change only_1_subtitler and friends
        self.dashboard_viewer.role = ROLE_MANAGER
        self.dashboard_viewer.save()
        self.update_workflow(only_1_subtitler=False,
                             only_1_reviewer=False,
                             only_1_approver=False)
        self.check_can_join(needs_subtitler + needs_reviewer +
                            needs_approver + can_join_if_not_only_1)

    def test_limits(self):
        for i in xrange(10):
            # make of collaborations that the user can join, these should be
            # limited by the limit we pass to for_dashboard()
            self.make_collaboration()
            self.make_collaboration(endorsed_subtitler=self.member1)
            self.make_collaboration(endorsed_subtitler=self.member1,
                                    endorsed_reviewer=self.member2)
            # make collaborations that the user has joined.  We shouldn't
            # limit these
            self.make_collaboration(subtitler=self.dashboard_viewer)
        for_dashboard = Collaboration.objects.for_dashboard(
            self.dashboard_viewer, can_join_limit=5)
        self.assertEquals(len(for_dashboard['can_join']), 15)
        self.assertEquals(len(for_dashboard['joined']), 10)

    def test_default_to_english_if_no_languages_set(self):
        self.dashboard_viewer.user.userlanguage_set.all().delete()
        can_join = self.make_collaboration(language_code='en')
        self.check_can_join([can_join])

class CollaborationNoteTest(CollaborationTestCase):
    @patch_for_test('teams.models.CollaborationNote.now')
    def test_add_notes(self, mock_now):
        collaboration = self.make_collaboration()
        collaboration.join(self.member1)
        self.assertEquals(collaboration.notes.count(), 0)
        notes_to_add = [
            (self.member1, 'note1', datetime(2012, 1, 1)),
            (self.member2, 'note2', datetime(2012, 2, 1)),
            (self.member3, 'note2', datetime(2012, 2, 1, 10, 30)),
        ]
        for member, text, note_date in notes_to_add:
            mock_now.return_value = note_date
            collaboration.add_note(member, text)

        correct_note_data = [
            (member.user, text, note_date)
            for member, text, note_date in notes_to_add
        ]
        self.assertEquals(
            [(c.user, c.text, c.datetime) for c in collaboration.notes.all()],
            correct_note_data)

    def test_member_must_be_part_of_team(self):
        collaboration = self.make_collaboration()
        other_member = TeamMemberFactory.create()
        self.assertRaises(ValueError, collaboration.add_note,
                          other_member, 'note text')
