# -*- coding: utf-8 -*-
import os
import time
import itertools
import operator
from webdriver_testing.webdriver_base import WebdriverTestCase
from webdriver_testing.data_factories import UserFactory
from webdriver_testing.data_factories import TeamMemberFactory

from webdriver_testing.data_factories import TeamVideoFactory
from webdriver_testing.data_factories import TeamLangPrefFactory
from webdriver_testing.data_factories import WorkflowFactory
from webdriver_testing.data_factories import VideoUrlFactory
from webdriver_testing import data_helpers
from webdriver_testing.pages.site_pages.teams_dir_page import TeamsDirPage

class TestCaseTeamTaskResource(WebdriverTestCase):
    """TestSuite for getting and modifying video urls via api_v2.

       One can list, update, delete and add video urls to existing videos.
 	
    """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseTeamTaskResource, cls).setUpClass()
        cls.data_utils = data_helpers.DataHelpers()
        cls.user = UserFactory.create(
            username='TestUser',
            is_partner = True)
        
        cls.team = cls.create_workflow_team()
        cls.team2 = cls.create_workflow_team()

        langs = ['ru', 'pt-br', 'de']
        for lc in langs:
            cls.test_video, tv = cls.create_tv_with_original_subs('en', cls.user, cls.team)
            cls.data_utils.complete_review_task(tv, 20, cls.user)
            cls.data_utils.complete_approve_task(tv, 20, cls.user)
            cls.add_translation(lc, cls.test_video,  cls.user, complete=True)
            cls.data_utils.complete_review_task(tv, 20, cls.user)
            cls.data_utils.complete_approve_task(tv, 20, cls.user)

        cls.inc_vid, tv = cls.create_tv_with_original_subs('fr', cls.user, cls.team)
        cls.data_utils.complete_review_task(tv, 20, cls.user)
        cls.data_utils.complete_approve_task(tv, 20, cls.user)
        cls.test_video2, tv = cls.create_tv_with_original_subs('en', cls.user, cls.team2)
        cls.data_utils.complete_review_task(tv, 20, cls.user)
        cls.data_utils.complete_approve_task(tv, 20, cls.user)



    @classmethod
    def create_workflow_team(cls):
        team = TeamMemberFactory.create(team__workflow_style='T',
                                            team__translate_policy=20, #any team
                                            team__subtitle_policy=20, #any team
                                            team__task_assign_policy=10, #any team
                                            user = cls.user,
                                            ).team
        cls.workflow = WorkflowFactory(team = team,
                                       autocreate_subtitle=True,
                                       autocreate_translate=True,
                                       approve_allowed = 10, # manager 
                                       review_allowed = 10, # peer
                                       )
        lang_list = ['en', 'ru', 'pt-br', 'de', 'sv']
        for language in lang_list:
            TeamLangPrefFactory.create(team=team, language_code=language,
                                       preferred=True)

        return team



    @classmethod
    def create_tv_with_original_subs(cls, lc, user, team, complete=True):
        sub_file = 'apps/webdriver_testing/subtitle_data/Timed_text.en.srt'
        video = cls.data_utils.create_video()
        tv = TeamVideoFactory.create(
            team=team, 
            video=video, 
            added_by=user)

        data = {
                    'language_code': lc,
                    'complete': complete, 
                    'visibility': 'private',
                    'committer': user,
                    'video': video
                }
        cls.data_utils.add_subs(**data)

        return video, tv

    @classmethod
    def add_translation(cls, lc, video, user, complete=False):
        data = {
                    'language_code': lc,
                    'complete': complete, 
                    'visibility': 'private',
                    'committer': user,
                    'video': video
                }
        cls.data_utils.add_subs(**data)



    def test_tasks_list_type(self):
        """List off the existing tasks. 

        GET /api2/partners/teams/[team-slug]/tasks/
        """
        url_part = 'teams/%s/tasks/?type=Translate' % self.team.slug
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        task_objects =  response['objects']
        self.assertEqual(17, len(task_objects))

    def test_tasks_list_completed_type(self):
        """List off the existing completed tasks filtered by type. 

        GET /api2/partners/teams/[team-slug]/tasks/
        """
        url_part = 'teams/%s/tasks/?completed&type=Translate' % self.team.slug
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        task_objects =  response['objects']
        self.assertEqual(3, len(task_objects))

    def test_tasks_list_open_type(self):
        """List off the existing open tasks of a type. 

        GET /api2/partners/teams/[team-slug]/tasks/
        """
        url_part = 'teams/%s/tasks/?open&type=Translate' % self.team.slug
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        task_objects =  response['objects']
        self.assertEqual(14, len(task_objects))


    def test_tasks_query_video_id(self):
        """Query for tasks of a video_id. 

        GET /api2/partners/teams/[team-slug]/tasks/
        """
        url_part = 'teams/{0}/tasks/?video_id={1}'.format(
            self.team.slug, self.test_video.video_id)
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        
        task_objects =  response['objects']
        self.assertEqual(9, len(task_objects)) 

    def test_query_video_id_type(self):
        """Query for tasks of a video_id and type. 

        GET /api2/partners/teams/[team-slug]/tasks/
        """
        url_part = 'teams/{0}/tasks/?video_id={1}&type=Approve'.format(
            self.team.slug, self.test_video.video_id)
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        
        task_objects =  response['objects']
        self.assertEqual(2, len(task_objects)) 


    def test_query_video_id_lang(self):
        """Query for tasks of a video_id. 

        GET /api2/partners/teams/[team-slug]/tasks/
        """
        url_part = 'teams/{0}/tasks/?video_id={1}&language=de'.format(
            self.team.slug, self.test_video.video_id)
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        
        task_objects =  response['objects']
        self.assertEqual(3, len(task_objects)) 


    def test_query_completed_videoid_lang(self):
        """Query for tasks of a video_id. 

        GET /api2/partners/teams/[team-slug]/tasks/
        """
        url_part = 'teams/{0}/tasks/?video_id={1}&language=en&completed'.format(
            self.team.slug, self.test_video.video_id)
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        
        task_objects =  response['objects']
        self.assertEqual(3, len(task_objects)) 


    def test_query_assignee(self):
        """Query for tasks by assignee.
       
        GET /api2/partners/teams/[team-slug]/tasks/
        """

        url_part = 'teams/%s/tasks/?assignee=%s' % (
                self.team2.slug, self.user.username)
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        
        task_objects =  response['objects']
        self.assertEqual(3, len(task_objects))

 
    def test_tasks_details(self):
        """Get the details of a task.

        GET /api2/partners/teams/[team-slug]/tasks/[task-id]/
        """
        url_part = 'teams/%s/tasks/' % self.team2.slug
        task_data = {   "type": "Translate",
                        "video_id": self.test_video2.video_id,
                        "language": "bo"
                    }
        r = self.data_utils.make_request(self.user, 'post', url_part, **task_data)
        response = r.json
        url_part = 'teams/{0}/tasks/{1}/'.format(self.team2.slug, 
            response['id'])

        del task_data['language']
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 
        
        for k, v in task_data.iteritems():
            self.assertEqual(v, response[k])



    def test_tasks_create(self):
        """Create a new task for a video.

        POST /api2/partners/teams/[team-slug]/tasks/
        """

        url_part = 'teams/%s/tasks/' % self.team2.slug
        task_data = {   "type": "Translate",
                        "video_id": self.test_video2.video_id,
                        "language": "es-mx"
                    }
        r = self.data_utils.make_request(self.user, 'post', url_part, **task_data)
        response = r.json 

        del task_data['language']
        for k, v in task_data.iteritems():
            self.assertEqual(v, response[k])


    def test_tasks_update(self):
        """Update a task 

        PUT /api2/partners/teams/[team-slug]/tasks/[task-id]/
        """
        url_part = 'teams/%s/tasks/' % self.team2.slug
        task_data = {   "type": "Translate",
                        "video_id": self.test_video2.video_id,
                        "language": "cs"
                    }

        r = self.data_utils.make_request(self.user, 'post', url_part, **task_data)
        response = r.json
        url_part = 'teams/{0}/tasks/{1}/'.format(self.team2.slug, 
            response['id'])
 
        updated_info = {'priority': 3} 
        r = self.data_utils.make_request(self.user, 'put', url_part, **updated_info)
        response = r.json 
        self.assertEqual(updated_info['priority'], response['priority'])

    def test_tasks_delete(self):
        """Delete a task.

           DELETE /api2/partners/teams/[team-slug]/tasks/[task-id]/
        """
        #Post a new task
        url_part = 'teams/%s/tasks/' % self.team2.slug
        task_data = {   "type": "Translate",
                        "video_id": self.test_video2.video_id,
                        "language": "hr"
                    }

        r = self.data_utils.make_request(self.user, 'post', url_part, **task_data)
        response = r.json 
        task_id = response['id']
        #Make the DELETE request
        url_part = 'teams/{0}/tasks/{1}/'.format(self.team2.slug, task_id)

        r = self.data_utils.make_request(self.user, 'delete', url_part)

        url_part = 'teams/%s/tasks/' % self.team2.slug
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json 

        task_objects =  response['objects']
        task_ids = []
        for k, v in itertools.groupby(task_ids, 
            operator.itemgetter('id')):
                tasks_list.append(k)
        self.assertNotIn(task_id, task_ids)


    def test_fetch_public_subtitles(self):
        """Return public subtitles of a moderated video.

        For videos under moderation only the latest published version is returned. 
        """
        url_part = 'videos/{0}/languages/en/?format=json'.format(
                    self.test_video.video_id)

        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.json
        self.logger.info(response)
        self.assertNotEqual(404, r.status_code)
        self.assertIs(6, response['subtitle_count'])

    def test_fetch_draft_subtitles(self):
        """Fetch nothing if moderated and no version has been accepted in review.
        """
        draft_video, tv = self.create_tv_with_original_subs(
                    'en', self.user, self.team2)

        url_part = 'videos/{0}/languages/en/?format=srt'.format(draft_video.video_id)
        r = self.data_utils.make_request(self.user, 'get', url_part)
        response = r.content
        self.logger.info(r.content)
        self.assertNotEqual(404, r.status_code)

