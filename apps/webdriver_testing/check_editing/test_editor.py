#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from django.test import TestCase
from django.core import management

from datetime import datetime as dt

from videos.models import Video


from webdriver_testing.webdriver_base import WebdriverTestCase
from webdriver_testing import data_helpers
from webdriver_testing.pages.site_pages import video_page
from webdriver_testing.pages.site_pages import editor_page
from webdriver_testing.data_factories import UserFactory

class TestCaseLeftSide(WebdriverTestCase):

    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseLeftSide, cls).setUpClass()
        fixt_data = [
                     'apps/webdriver_testing/fixtures/editor_auth.json', 
                     'apps/webdriver_testing/fixtures/editor_videos.json',
                     'apps/webdriver_testing/fixtures/editor_subtitles.json'
        ]
        for f in fixt_data:
            management.call_command('loaddata', f, verbosity=0)
        
        cls.logger.info("""Default Test Data loaded from fixtures

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
                       """)
        cls.editor_pg = editor_page.EditorPage(cls)
        cls.data_utils = data_helpers.DataHelpers()
        cls.video_pg = video_page.VideoPage(cls)
        cls.user = UserFactory.create()
        cls.video_pg.open_page('auth/login/', alert_check=True)
        cls.video_pg.log_in(cls.user.username, 'password')



    @classmethod
    def tearDownClass(cls):
        super(TestCaseLeftSide, cls).tearDownClass()
        management.call_command('flush', verbosity=0, interactive=False)


    def test_reference_lang__forked(self):
        """Default reference lang for forked translation is the same lang. """
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'sv')
        self.assertEqual('English', self.editor_pg.selected_ref_language())
        self.editor_pg.exit()



    def test_reference_lang__primary(self):
        """Default reference lang for transcription is the same lang. """
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.assertEqual('English', self.editor_pg.selected_ref_language())
        self.editor_pg.exit()


    def test_reference_lang__translation(self):
        """Default reference lang for translation is the parent lang. """
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'da')
        self.assertEqual('English', self.editor_pg.selected_ref_language())
        self.editor_pg.exit()


    def test_reference_version__translation_latest(self):
        """Default reference version is version translatied from source. """
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'zh-cn')
        self.assertEqual('Version 6', self.editor_pg.selected_ref_version())
        self.editor_pg.open_editor_page(video.video_id, 'da')
        self.assertEqual('Version 6', self.editor_pg.selected_ref_version())
        self.editor_pg.exit()


    def test_reference_text_displayed(self):
        """Reference language text updated when language and version changed.

        """
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'da')
        self.assertEqual('Tangible problems.', 
                         self.editor_pg.reference_text(1))
        self.editor_pg.select_ref_language('Danish')
        self.assertEqual('Konkrete problemer', 
                         self.editor_pg.reference_text(1))
        self.editor_pg.select_ref_language('Turkish')
        self.assertEqual(u'\xe7\xf6zmekte olan g\xfcc\xfcn\xfc hep hissettim.', 
                         self.editor_pg.reference_text(3))
        #Switch from a version 1 to a version 1 lang.
        self.logger.info('Check text switching from lang1 v1, to lang2 v1')
        self.editor_pg.select_ref_version('Version 1')
        self.editor_pg.select_ref_language('Chinese, Simplified')
        self.logger.info(self.editor_pg.reference_text(3))
        self.assertEqual(u'可以来解决各种迫切的问题。', 
                         self.editor_pg.reference_text(3))
        self.editor_pg.exit()


    def test_reference_private_versions(self):
        """Reference version has no default when all versions are private

        """
        video = Video.objects.all()[0]
        sl_tr = video.en = video.subtitle_language('tr').get_tip(full=True)
        sl_tr.visibility_override = 'private'
        sl_tr.save()
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.editor_pg.select_ref_language('Turkish')
        self.assertEqual(None, self.editor_pg.default_ref_version())
        self.assertEqual(None, 
                         self.editor_pg.reference_text(1))
        self.editor_pg.exit()


class TestCaseCenter(WebdriverTestCase):
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseCenter, cls).setUpClass()
        fixt_data = [
                     'apps/webdriver_testing/fixtures/editor_auth.json', 
                     'apps/webdriver_testing/fixtures/editor_videos.json',
                     'apps/webdriver_testing/fixtures/editor_subtitles.json'
        ]
        for f in fixt_data:
            management.call_command('loaddata', f, verbosity=0)

        cls.logger.info("""Default Test Data

                        video[0]:
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
        cls.video_pg.open_page('auth/login/')
        cls.video_pg.log_in(cls.user.username, 'password')



    @classmethod
    def tearDownClass(cls):
        super(TestCaseCenter, cls).tearDownClass()
        management.call_command('flush', verbosity=0, interactive=False)


    def setUp(self):
        self.video_pg.open_page('auth/login/', True)
        self.video_pg.log_in(self.user.username, 'password')


    def test_selected_subs_on_video(self):
        """Clicking a working subs displays it on the video."""
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        sub_text, _ = self.editor_pg.click_working_sub_line(3)
        self.assertEqual(sub_text, self.editor_pg.sub_overlayed_text())
        self.editor_pg.exit()


    def test_remove_active_subtitle(self):
        """Remove the selected subtitle line.
 
        from i2441
        """
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        subtext = self.editor_pg.working_text()
        removed_text = self.editor_pg.remove_active_subtitle(3)
        self.assertEqual(subtext[2], removed_text)
        subtext = self.editor_pg.working_text()
        self.assertNotEqual(subtext[2], removed_text)
        self.editor_pg.exit()

        

    def test_working_language(self):
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.assertEqual(u'Editing English\u2026', self.editor_pg.working_language())
        self.editor_pg.open_editor_page(video.video_id, 'tr')
        self.assertEqual(u'Editing Turkish\u2026', self.editor_pg.working_language())
        self.editor_pg.exit()


    def test_page_title(self):
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.assertEqual('Open Source Philosophy',
                         self.editor_pg.video_title())
        self.editor_pg.exit()



    def test_info_tray(self):
        """Info tray displays start, stop, char count, chars/second."""
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        sub_info = (self.editor_pg.subtitle_info(4))
        self.assertEqual('0:09.24', sub_info['Start'], 
                         'start time is not expected value')
        self.assertEqual('0:12.84', sub_info['End'], 
                         'stop time is not expected value')
        self.assertEqual('70', sub_info['Characters'], 
                         'character count is not expected value')
        self.assertEqual('19.5', sub_info['Chars/sec'], 
                         'character rate is not expected value')
        self.editor_pg.exit()


    def test_info_tray__multiline(self):
        """Info tray displays start, stop, char count, chars/second."""
        video = Video.objects.all()[3]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        line1 = 'This is the first line'
        line2 = 'This is the much longer second line'
        self.editor_pg.edit_sub_line([line1, 'br', line2], 1)
        sub_info  = self.editor_pg.subtitle_info(1, True)
        self.assertEqual('22', sub_info['Line 1'], 
                         'Line 1 is not expected value')
        self.assertEqual('35', sub_info['Line 2'], 
                         'Line 2 is not expected value')
        self.assertEqual('59', sub_info['Characters'], 
                         'character count is not expected value')
        self.editor_pg.exit()


    def test_info_tray__char_updates(self):
        """Info tray character counts updates dynamically"""
        video = Video.objects.all()[3]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.editor_pg.edit_sub_line('12345 chars', 1, enter=False)
        sub_info  = (self.editor_pg.subtitle_info(1, active=True))
        self.assertEqual('11', sub_info['Characters'], 
                         'character count is not expected value')
        self.editor_pg.exit()



    def test_add_lines_to_end(self):
        """Add sub to the end of the subtitle list, enter adds new active sub."""
        self.logger.info(Video.objects.all())
        video = Video.objects.all()[4]
        self.editor_pg.open_editor_page(video.video_id, 'nl')

        subs = ['third to last', 'pentulitmate subtitle', 'THE END']
        self.editor_pg.add_subs_to_the_end(subs)
        new_subs = self.editor_pg.working_text()[-3:]
        self.assertEqual(subs, new_subs)
        self.editor_pg.exit()


    def test_one_version__original(self):
        """Video with only 1 version displays subs in working section.

        """
        video = Video.objects.all()[3]
        self.logger.info('checking subs on en-original')
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.assertEqual(5, len(self.editor_pg.working_text()))
        self.assertEqual(5, len(self.editor_pg.reference_text()))
        self.editor_pg.exit()


    def test_one_version__forked(self):
        """Video with only 1 version displays subs in working section.

        """
        video = Video.objects.all()[4]
        self.logger.info('checking subs on single version forked')
        self.editor_pg.open_editor_page(video.video_id, 'nl')
        self.assertEqual(6, len(self.editor_pg.working_text()))
        self.editor_pg.exit()


    def test_sync_subs(self):
        """Sync subtitles """
        video = Video.objects.all()[4]
        self.editor_pg.open_editor_page(video.video_id, 'nl')
        self.editor_pg.buffer_up_subs()
        self.editor_pg.toggle_playback()
        self.editor_pg.sync(8, 6)
        self.editor_pg.toggle_playback()
        times = self.editor_pg.start_times()
        times = [x for x in times if x != '--']
        diffs = [(dt.strptime(x, '%M:%S.%f') - dt.strptime(y, '%M:%S.%f')) 
                  for (x, y) in zip(times[1:], times[:-1])]
        self.logger.info(diffs)
        for x in diffs:
            self.assertGreater(x.seconds, 4)
        self.editor_pg.exit()


    def test_syncing_scroll(self):
        """Scroll sub list while syncing so sub text is always in view.

        """
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'tr')
        text = self.editor_pg.working_text()
        self.editor_pg.buffer_up_subs()
        self.editor_pg.toggle_playback()
        text_els = self.editor_pg.working_text_elements()[:25]
        for x in range(0, 20):
            el = self.editor_pg.working_text_elements()[x]
            self.assertTrue(el.is_displayed())
            self.editor_pg.sync(1, sub_length=1, sub_space=.05)
        self.editor_pg.exit()


    def test_helper_syncing(self):
        """Sync helper stays in view while syncing subs.

        """
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'tr')
        text = self.editor_pg.working_text()
        self.editor_pg.buffer_up_subs()
        self.editor_pg.toggle_playback()
        self.editor_pg.sync(1, sub_length=2, sub_space=2)

        for x in range(0, 20):
            self.editor_pg.sync(1, sub_length=1, sub_space=.05)
            self.assertTrue(self.editor_pg.sync_help_displayed())
        self.editor_pg.exit()


    def test_helper_scrolling(self):
        """Sync helper not in view after manually scrolling subs.

        """
        video = Video.objects.all()[0]
        self.editor_pg.open_editor_page(video.video_id, 'tr')
        text = self.editor_pg.working_text()
        self.editor_pg.buffer_up_subs()
        self.editor_pg.toggle_playback()
        self.editor_pg.sync(1, sub_length=2, sub_space=2)
        for x in range(0, 3):
            self.editor_pg.sync(1, sub_length=1, sub_space=.05)
            self.assertTrue(self.editor_pg.sync_help_displayed())
        self.editor_pg.toggle_playback()
        self.browser.execute_script("window.location.hash='add-sub-at-end'")
        self.assertFalse(self.editor_pg.sync_help_displayed())
        self.editor_pg.exit()



    def test_rtl(self):
        video = Video.objects.all()[3]
        #video = self.data_utils.create_video()
        test_user = UserFactory.create()
        sub_file = os.path.join(os.getcwd(), 'apps', 'webdriver_testing', 
                                'subtitle_data', 'Timed_text.ar.xml')
        self.video_pg.log_in(test_user.username, 'password')
        self.video_pg.open_video_page(video.video_id)
        self.video_pg.upload_subtitles('Arabic', sub_file)
        self.editor_pg.open_editor_page(video.video_id, 'ar')
        expected_text = (u'\u0623\u0648\u062f \u0623\u0646 \u0623\u0628\u062f'
                         u'\u0623 \u0628\u0623\u0631\u0628\u0639\u0629 \u0623'
                         u'\u0633\u0626\u0644\u0629.')
        sub_text, _ = self.editor_pg.click_working_sub_line(3)
        self.assertEqual(expected_text, sub_text)
        self.assertEqual(sub_text, self.editor_pg.sub_overlayed_text())
        self.assertEqual(expected_text, sub_text)
        self.editor_pg.exit()


