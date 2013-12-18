#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time 
from django.test import TestCase
from django.core import management

from videos.models import Video


from webdriver_testing.webdriver_base import WebdriverTestCase
from webdriver_testing import data_helpers
from webdriver_testing.pages.site_pages import video_page
from webdriver_testing.pages.site_pages import editor_page
from webdriver_testing.data_factories import UserFactory

class TestCaseTools(WebdriverTestCase):

    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseTools, cls).setUpClass()
        fixt_data = [
                     'apps/webdriver_testing/fixtures/editor_auth.json', 
                     'apps/webdriver_testing/fixtures/editor_videos.json',
                     'apps/webdriver_testing/fixtures/editor_subtitles.json'
        ]
        for f in fixt_data:
            management.call_command('loaddata', f, verbosity=0)
        
        cls.logger.info("""
                        video[0] Default Test Data loaded from fixtures

                          English, source primary v2 -> v6
                                 v1 -> deleted

                          Chinese v1 -> v3
                                v3 {"zh-cn": 2, "en": 6}

                          Danish v1 --> v4
                               v4 {"en": 5, "da": 3}
                               
                          Swedish v1 --> v3 FORKED
                                v3 {"sv": 2}
                                v1 --> private

                          Turkish (tr) v1 incomplete {"en": 5}

                        video[1]: No subs - about amara video
                        video[2]: No subs youtube
                        video[3]: en original 1 version complete.
                        video[4]: nl unsynced, not original

                       """)
        cls.editor_pg = editor_page.EditorPage(cls)
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_pg = video_page.VideoPage(cls)
        cls.user = UserFactory.create()
        cls.video_pg.open_page('auth/login/', alert_check=True)
        cls.video_pg.log_in(cls.user.username, 'password')

    def tearDown(self):
        try:
            self.editor_pg.exit()
        except:
            self.editor_pg.open_page('/')
            self.editor_pg.handle_js_alert('accept') 

    def test_copy_timings_to_new_translation(self):
        """Copy timing to new translation blank lines. """

        video = Video.objects.all()[0]
        #video = self.data_utils.create_video()
        test_user = UserFactory.create()
        self.video_pg.log_in(test_user.username, 'password')
        self.editor_pg.open_editor_page(video.video_id, 'pl')
        subs = ['one', 'two', 'three', 'four', 'five', 'six']
        self.editor_pg.add_new_lines(6)
        self.editor_pg.copy_timings()
        working_times = self.editor_pg.start_times()
        ref_times = self.editor_pg.reference_times()
        self.assertEqual(ref_times[0], working_times[0])

    def test_copy_timings_to_txt_upload(self):
        """Copy timings to untimed text upload. """
        video = Video.objects.all()[3]
        #video = self.data_utils.create_video()
        test_user = UserFactory.create()
        sub_file = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                'subtitle_data', 'Untimed_text.txt')
        self.video_pg.log_in(test_user.username, 'password')
        self.video_pg.open_video_page(video.video_id)
        self.video_pg.upload_subtitles('Dutch', sub_file)
        self.editor_pg.open_editor_page(video.video_id, 'nl')
        self.editor_pg.copy_timings()
        working_times = self.editor_pg.start_times()
        ref_times = self.editor_pg.reference_times()
        self.assertEqual(ref_times[:5], working_times[:5]) 


    def test_copy_timings_change_reference(self):
        """Change reference lang then copy timings. """
        video = Video.objects.all()[0]
        test_user = UserFactory.create()
        sub_file = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                'subtitle_data', 'Untimed_text.txt')
        self.video_pg.log_in(test_user.username, 'password')
        self.video_pg.open_video_page(video.video_id)
        self.video_pg.upload_subtitles('Dutch', sub_file)
        self.editor_pg.open_editor_page(video.video_id, 'nl')
        self.editor_pg.select_ref_language('Danish')
        self.editor_pg.copy_timings()
        working_times = self.editor_pg.start_times()
        ref_times = self.editor_pg.reference_times()
        self.assertEqual(ref_times[:5], working_times[:5]) 

    def test_copy_timings_reference_unsynced(self):
        """No copy in menu if reference subs are unsynced. """
        video = Video.objects.all()[0]
        test_user = UserFactory.create()
        sub_file = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                'subtitle_data', 'Untimed_text.txt')
        self.video_pg.log_in(test_user.username, 'password')
        self.video_pg.open_video_page(video.video_id)
        self.video_pg.upload_subtitles('Dutch', sub_file)
        self.editor_pg.open_ed_with_base(video.video_id, 'sv', 'nl')
        self.editor_pg.select_ref_language('Dutch')
        time.sleep(3)
        self.assertEqual("Element not displayed", self.editor_pg.copy_timings())

    def test_copy_timings_reference_draft(self):
        """No copy in menu if reference subs are draft (incomplete). """
        video = Video.objects.all()[0]
        test_user = UserFactory.create()
        self.video_pg.log_in(test_user.username, 'password')
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.editor_pg.select_ref_language('Turkish')
        self.assertEqual("Element not displayed", self.editor_pg.copy_timings())

    def test_copy_timings_working_blank(self):
        """No copy in menu if there are no working subs. """
        video = Video.objects.all()[0]
        test_user = UserFactory.create()
        self.video_pg.log_in(test_user.username, 'password')
        self.editor_pg.open_editor_page(video.video_id, 'hr')
        self.assertEqual("Element not displayed", self.editor_pg.copy_timings())
