import os
import time
import itertools
import operator
from webdriver_testing.webdriver_base import WebdriverTestCase
from webdriver_testing.data_factories import UserFactory
from webdriver_testing.data_factories import TeamMemberFactory

from webdriver_testing.data_factories import TeamVideoFactory
from webdriver_testing import data_helpers
from webdriver_testing.pages.site_pages.teams_dir_page import TeamsDirPage

class TestCaseTeamsResource(WebdriverTestCase):
    """TestSuite for getting and modifying video urls via api_v2.  """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseTeamsResource, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.user = UserFactory.create(is_partner=True)
        cls.private_user = UserFactory.create(username = 'IdaRed')
        
        cls.logger.info('setup: creating team data')
        #create 3 open teams
        for x in range(3):
            TeamMemberFactory.create(
                team__name='my team ' + str(x),
                team__slug='my-team-' + str(x),
                user__username='generic_team_owner' + str(x),
                )

        #create an open team with description text and 2 members
        cls.open_team = TeamMemberFactory.create(
            team__name="A1 Waay Cool team",
            team__slug='a1-waay-cool-team',
            team__description='this is the coolest, most creative team ever',
            user__username='open_team_owner',
            ).team

        TeamMemberFactory.create(team=cls.open_team, user=cls.user)
        TeamVideoFactory.create(team=cls.open_team, added_by=cls.user)

        #create an application team with 3 members and 5 videos
        app_team = TeamMemberFactory.create(
            team__name='the application-only team',
            team__slug='the-application-only-team',
            team__membership_policy=1,
            user__username='application_team_owner',
            ).team
        TeamMemberFactory.create(team=app_team, user=UserFactory.create())
        TeamMemberFactory.create(team=app_team, user=cls.user)
        for x in range(5):
            TeamVideoFactory.create(team=app_team, added_by=cls.user)

        #create 1 private team
        cls.priv_team = TeamMemberFactory.create(
            team__name='my own private idaho',
            team__slug='private-idaho',
            team__membership_policy=1,
            team__is_visible=False,
            user = cls.private_user).team

        #Open to the teams page so you can see what's there.
        cls.teams_dir_pg = TeamsDirPage(cls)
        cls.teams_dir_pg.open_teams_page()

    def test_list(self):
        """List off the existing teams.

        GET /api2/partners/teams/
        """
        expected_teams = ['A1 Waay Cool team', 
                          'my team 0', 
                          'my team 1', 
                          'my team 2',
                          'the application-only team']
        url_part = 'teams/'
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json
        team_objects =  response['objects']
        teams_list = []
        for k, v in itertools.groupby(team_objects, operator.itemgetter('name')):
            teams_list.append(k)
        self.assertEqual(expected_teams, teams_list)

    def test_list_private(self):
        """Private teams are displayed when the requestor is a member of the team.

        """
        expected_teams = ['A1 Waay Cool team', 
                          'my own private idaho', 
                          'my team 0', 
                          'my team 1', 
                          'my team 2',
                          'the application-only team']

        TeamMemberFactory.create(team=self.priv_team, user=self.user)
        url_part = 'teams/'
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json
        team_objects =  response['objects']
        teams_list = []
        for k, v in itertools.groupby(team_objects, operator.itemgetter('name')):
            teams_list.append(k)
        self.assertEqual(expected_teams, teams_list)

    def test_details(self):
        """Get the details about a specific team.

        GET /api2/partners/teams/[team-slug]/
        """

        expected_details = {
            'is_visible': True, 
            'translate_policy': 'Anyone', 
            'projects_enabled': False, 
            'description': 'this is the coolest, most creative team ever',
            'subtitle_policy': 'Anyone', 
            'deleted': False, 
            'task_assign_policy': 'Any team member', 
            'task_expiration': None, 
            'header_html_text': '', 
            'membership_policy': 'Open', 
            'video_policy': 'Any team member', 
            'is_moderated': False, 
            'logo': None, 
            'resource_uri': '/api2/partners/teams/a1-waay-cool-team/', 
            'slug': 'a1-waay-cool-team', 
            'max_tasks_per_member': None, 
            'name': 'A1 Waay Cool team', 
            'workflow_style': 'D',
            } 

        url_part = 'teams/%s/' %self.open_team.slug
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json
        for k, v in expected_details.iteritems():
            self.assertEqual(v, response[k])

    def test_update(self):
        """Get the details about a specific team.

        PUT /api2/partners/teams/[team-slug]/
        """
        url_part = 'teams/%s/' %self.open_team.slug
        expected_details = {
            'description': 'this a lazy team!',
            'subtitle_policy': 'Anyone', 
            'membership_policy': 'Invitation by any team member', 
            'video_policy': 'Any team member', 
            } 
        self.data_utils.make_request(self.user, 'put', url_part, **expected_details)

        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        self.teams_dir_pg.open_page('teams/%s/settings/permissions/' % self.open_team.slug)
        self.teams_dir_pg.log_in('open_team_owner', 'password')
        for k, v in expected_details.iteritems():
            self.assertEqual(v, response[k])

    def test_team__create(self):
        """Verify video urls for a particular video are listed.

          POST /api2/partners/teams/
        """
        partner_user = UserFactory.create(username = 'team_creator', is_partner = True)
        
        self.user = partner_user
        expected_details = {
            'name': 'API V2 TEAM',
            'description': 'new team created via the api',
            'slug': 'api-created-team' 
            } 

        url_part = 'teams/'
        r = self.data_utils.make_request(self.user, 'post', url_part, **expected_details)
        response = r.json
        
        for k, v in expected_details.iteritems():
            self.assertEqual(v, response[k])
        self.teams_dir_pg.open_page('teams/api-created-team/settings/permissions/')
        self.teams_dir_pg.log_in(self.user.username, 'password')


    def test_delete(self):
        """Team is deleted by the owner.

           DELETE /api2/partners/teams/[team-slug]/
        """
        url_part = 'teams/%s/' %self.open_team.slug
        self.data_utils.make_request(self.user, 'delete', url_part)
        r = self.data_utils.make_request(self.user, 'get', 'teams/')
        response = r.json
        team_objects =  response['objects']
        teams_list = []
        for k, v in itertools.groupby(team_objects, operator.itemgetter('name')):
            teams_list.append(k)
        self.assertNotIn(self.open_team.name, teams_list)

    def test_delete__nonmember(self):
        """Non-members can not delete the team.

           DELETE /api2/partners/teams/[team-slug]/
        """
        url_part = 'teams/%s/' % self.priv_team.slug
        url_part2 = 'teams/%s/' % 'my-team-2'
        r = self.data_utils.make_request(self.user, 'delete', url_part)
        self.assertEqual(r.status_code, 403)

    def test_delete__contributor(self):
        """A Contributor can not delete the team.

           DELETE /api2/partners/teams/[team-slug]/
        """
        TeamMemberFactory.create(role="ROLE_CONTRIBUTOR", team=self.priv_team, user=self.user)
        url_part = 'teams/%s/' % self.priv_team.slug
        r = self.data_utils.make_request(self.user, 'delete', url_part)
        self.assertEqual(r.status_code, 403)

        
        
        
