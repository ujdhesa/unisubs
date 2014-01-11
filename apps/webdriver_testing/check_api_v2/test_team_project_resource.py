import os
import time
import itertools
import operator
from webdriver_testing.webdriver_base import WebdriverTestCase
from webdriver_testing.data_factories import UserFactory
from webdriver_testing.data_factories import TeamMemberFactory
from webdriver_testing.data_factories import TeamVideoFactory
from webdriver_testing.data_factories import TeamProjectFactory

from webdriver_testing import data_helpers
from webdriver_testing.pages.site_pages.teams import ATeamPage

class TestCaseTeamProjectResource(WebdriverTestCase):
    """TestSuite for getting and modifying video urls via api_v2.

       One can list, update, delete and add video urls to existing videos.
    """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseTeamProjectResource, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()

        cls.user = UserFactory.create(username = 'TestUser', is_partner=True)
        cls.team_owner = UserFactory.create(username = 'team_owner')
        

        #create an open team with description text and 2 members
        cls.open_team = TeamMemberFactory.create(
            team__name="Cool team",
            team__slug='team-with-projects',
            team__description='this is the coolest, most creative team ever',
            user = cls.team_owner,
            ).team
        TeamMemberFactory(team=cls.open_team, 
                               role='ROLE_ADMIN', 
                               user=cls.user)
        #Open to the teams page so you can see what's there.
        cls.project1 = TeamProjectFactory(
            team=cls.open_team,
            name='team project one',
            slug = 'team-project-one',
            description = 'subtitle project number 1',
            guidelines = 'do a good job')
        
        cls.project2 = TeamProjectFactory(
            team=cls.open_team,
            name='team project two')

        cls.team_pg = ATeamPage(cls)
        cls.team_pg.open_team_page(cls.open_team.slug)

    def test_projects__list(self):
        """List off the teams projects.

        GET /api2/partners/teams/[team-slug]/projects/
        """
        expected_projects = ['team project one', 'team project two'] 
        url_part = 'teams/%s/projects/' % self.open_team.slug
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json
        project_objects = response['objects']
        projects_list = []
        for k, v in itertools.groupby(
            project_objects, 
            operator.itemgetter('name')):
                projects_list.append(k)
        self.assertEqual(expected_projects, projects_list)



    def test_projects__details(self):
        """Get the details of a project.

           GET /api2/partners/teams/[team-slug]/projects/[project-slug]/
        """
        expected_data = { 'description': 'subtitle project number 1',
                          'guidelines': 'do a good job',
                          'name': 'team project one',
                          'slug': 'team-project-one',
                        }

        url_part = 'teams/{0}/projects/{1}/'.format(self.open_team.slug,
            self.project1.slug)
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json

        for k, v in expected_data.iteritems():
            self.assertEqual(v, response[k])


    def test_projects__create(self):
        """Create a new project for the team.

        POST /api2/partners/teams/[team-slug]/projects/
        """

        url_part = 'teams/%s/projects/' % self.open_team.slug
        project_data = {
                     "name": "Project name",
                     "slug": "project-slug",
                     "description": "This is an example project.",
                     "guidelines": "Only post family-friendly videos."
                    }
        self.data_utils.make_request(self.user, 'post', 
                                     url_part, **project_data)
        self.team_pg.open_team_page(self.open_team.slug)
        

        self.assertTrue(self.team_pg.has_project(project_data['slug']))



    def test_projects_update(self):
        """Update a projects information.

        PUT /api2/partners/teams/[team-slug]/projects/[project-slug]/
        """
        url_part = 'teams/{0}/projects/{1}/'.format(self.open_team.slug,
            self.project1.slug)
 
        updated_info = {
            'description': 'this a an updated test description' 
            } 
        r = self.data_utils.make_request(self.user, 'put', 
                                     url_part, **updated_info)
        response = r.json
        self.assertEqual(updated_info['description'], response['description'])

    def test_projects_delete(self):
        """Delete a team project.

           DELETE /api2/partners/teams/[team-slug]/projects/[project-slug]/
        """
        url_part = 'teams/{0}/projects/{1}/'.format(self.open_team.slug,
                                                    self.project1.slug)
        self.data_utils.make_request(self.user, 'delete', url_part) 


        self.team_pg.open_team_page(self.open_team.slug)

        #Verify project 1 is still present
        self.assertTrue(self.team_pg.has_project(self.project2.slug)) 

        #Verify project2 is deleted
        self.assertFalse(self.team_pg.has_project(self.project1.slug)) 
