#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from django.test import TestCase
from django.core import management

from apps.videos.models import Video

from apps.webdriver_testing.webdriver_base import WebdriverTestCase
from apps.webdriver_testing import data_helpers
from apps.webdriver_testing.pages.site_pages import video_page
from apps.webdriver_testing.pages.site_pages import video_language_page
from apps.webdriver_testing.pages.site_pages import editor_page
from apps.webdriver_testing.pages.editor_pages import dialogs
from apps.webdriver_testing.pages.editor_pages import unisubs_menu
from apps.webdriver_testing.pages.editor_pages import subtitle_editor 
from apps.webdriver_testing.data_factories import UserFactory
from apps.webdriver_testing.data_factories import TaskFactory
from apps.webdriver_testing.data_factories import WorkflowFactory
from apps.webdriver_testing.pages.site_pages.teams.tasks_tab import TasksTab
from apps.webdriver_testing.data_factories import TeamVideoFactory
from apps.webdriver_testing.data_factories import TeamMemberFactory


class TestCaseEntryExit(WebdriverTestCase):
    """Entry and Exit points to New Editor. """
    NEW_BROWSER_PER_TEST_CASE = False

    @classmethod
    def setUpClass(cls):
        super(TestCaseEntryExit, cls).setUpClass()
        fixt_data = [
                     'apps/webdriver_testing/fixtures/editor_auth.json', 
                     'apps/webdriver_testing/fixtures/editor_videos.json',
                     'apps/webdriver_testing/fixtures/editor_subtitles.json'
        ]
        for f in fixt_data:
            management.call_command('loaddata', f, verbosity=0)
        cls.logger.info("""Default Test Data - loaded from fixtures

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

        
        cls.create_modal = dialogs.CreateLanguageSelection(cls)
        cls.sub_editor = subtitle_editor.SubtitleEditor(cls)
        cls.unisubs_menu = unisubs_menu.UnisubsMenu(cls)
        cls.editor_pg = editor_page.EditorPage(cls)
        cls.video_pg = video_page.VideoPage(cls)
        cls.video_lang_pg = video_language_page.VideoLanguagePage(cls)
        cls.tasks_tab = TasksTab(cls)

        cls.user = UserFactory.create()
        cls.video_pg.open_page('auth/login/')
        cls.video_pg.log_in(cls.user.username, 'password')

        #Create a workflow enabled team to check review/approve dialog switching.
        cls.team = TeamMemberFactory.create(team__workflow_enabled=True,
                                            team__translate_policy=20, #any team
                                            team__subtitle_policy=20, #any team
                                            team__task_assign_policy=10, #any team
                                            user = cls.user,
                                            ).team
        cls.workflow = WorkflowFactory(team = cls.team,
                                       autocreate_subtitle=True,
                                       autocreate_translate=True,
                                       approve_allowed = 10, # manager
                                       review_allowed = 10, # peer
                                       )
        cls.user = UserFactory.create()

    @classmethod
    def tearDownClass(cls):
        super(TestCaseEntryExit, cls).tearDownClass()
        management.call_command('flush', verbosity=0, interactive=False)


    def setUp(self):
        self.video_pg.open_page('auth/login', True)
        self.video_pg.log_in(self.user.username, 'password')


    def test_timed_to_new(self):
        """From timed editor to beta, reference and working langs are same.

        """
        video = Video.objects.all()[0]
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.edit_subtitles()
        self.sub_editor.open_in_beta_editor()
        self.assertEqual('English', self.editor_pg.selected_ref_language())
        self.assertEqual('Editing English\u2026', 
                          self.editor_pg.working_language())
        self.editor_pg.exit()


    def test_timed_to_new_back_to_full(self):
        """From timed editor to beta, reference and working langs are same.

        """
        video = Video.objects.all()[0]
        self.video_lang_pg.open_video_lang_page(video.video_id, 'en')
        self.video_lang_pg.edit_subtitles()
        self.sub_editor.open_in_beta_editor()
        self.assertEqual('English', self.editor_pg.selected_ref_language())
        self.editor_pg.exit_to_full_editor()
        self.assertEqual('Typing', self.sub_editor.dialog_title())


    def test_forked_to_new(self):
        """Translation editor to beta, reference lang and version is source.

        """
        video = Video.objects.all()[0]
        self.video_lang_pg.open_video_lang_page(video.video_id, 'sv')
        self.video_lang_pg.edit_subtitles()
        self.sub_editor.open_in_beta_editor()
        self.assertEqual('English', self.editor_pg.selected_ref_language())
        self.assertEqual('Version 6', self.editor_pg.selected_ref_version())
        self.assertEqual('Editing Swedish\u2026', 
                          self.editor_pg.working_language())
        self.editor_pg.exit()



    def _old_to_new_sv_review(self):
        self.logger.info('creating video and adding to team')
        video = Video.objects.all()[0]
        member = TeamMemberFactory(team=self.team).user

        #Add video to team and create a review task
        tv = TeamVideoFactory(team=self.team, added_by=self.user, video=video)
        translate_task = TaskFactory.build(type = 20, 
                           team = self.team, 
                           team_video = tv, 
                           language = 'sv', 
                           assignee = member)

        self.logger.info('complete the translate task')
        translate_task.new_subtitle_version = translate_task.get_subtitle_version()
        translate_task.save()
        task = translate_task.complete()
        self.logger.info('perform review task to open in old editor')
        self.tasks_tab.open_tasks_tab(self.team.slug)
        self.tasks_tab.log_in(member.username, 'password')

        self.tasks_tab.open_tasks_tab(self.team.slug)

        self.tasks_tab.open_page('teams/{0}/tasks/?team_video={1}'
                                 '&assignee=anyone&lang=sv'.format(
                                 self.team.slug, tv.pk))
        self.tasks_tab.perform_and_assign_task('Review Swedish Subtitles', 
                                               video.title)
        self.sub_editor.continue_to_next_step()
        self.logger.info('open in new editor')
        self.sub_editor.open_in_beta_editor()
        return video, tv
        self.editor_pg.exit()



    def test_review_to_new(self):
        self._old_to_new_sv_review()
        self.assertEqual('English', self.editor_pg.selected_ref_language())
        self.assertEqual('Version 6', self.editor_pg.selected_ref_version())
        self.assertEqual('Editing Swedish\u2026', 
                          self.editor_pg.working_language())
        self.editor_pg.exit()


    def test_review_to_new_back_to_full(self):
        """Start Review task, switch to new editor and back to Review.

        """
        self.skipTest('Needs i2388 fixed')
        self._old_to_new_sv_review()
        self.assertEqual('Editing Swedish\u2026', 
                          self.editor_pg.working_language())
        self.editor_pg.exit_to_full_editor()
        self.assertEqual('Review subtitles', self.sub_editor.dialog_title())

    def test_review_to_new_approve(self):
        """Start Review task, switch to new editor and endorse 

        """
        video, tv = self._old_to_new_sv_review()
        self.assertEqual('Editing Swedish\u2026', 
                          self.editor_pg.working_language())
        self.editor_pg.approve_task()
        self.assertEqual(video.title, 
                         self.video_pg.video_title())
        self.assertEqual(1, len(list(tv.task_set.all_approve().all())))


    def test_edit_approve_version(self):
        """Edit then and approve review task save new version.

        """
        video, tv = self._old_to_new_sv_review()
        self.editor_pg.edit_sub_line('12345 chars', 1)
        self.editor_pg.save('Resume editing')
        self.editor_pg.approve_task()
        sv = video.subtitle_language('sv').get_tip(full=True)
        self.assertEqual(4, sv.version_number)


    def test_save_back_to_old(self):
        """Open in new editor, then save and go back to old editor.

        """
        video = Video.objects.all()[3]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.editor_pg.edit_sub_line('12345 chars', 1)
        self.editor_pg.save('Back to full editor')
        self.assertEqual('Typing', self.sub_editor.dialog_title())

    def test_save_resume(self):
        """Open in new editor, then save and go back to old editor.

        """
        video = Video.objects.all()[3]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.editor_pg.edit_sub_line('12345 chars', 1)
        self.editor_pg.save('Resume editing')
        self.assertEqual(u"English \u2022 Italo Calvino's Cosmicomics by Sheri Prather",
                         self.editor_pg.video_title())
        self.editor_pg.exit()



    def test_save_exit(self):
        video = Video.objects.all()[3]
        self.editor_pg.open_editor_page(video.video_id, 'en')
        self.editor_pg.edit_sub_line('12345 chars', 1)
        self.editor_pg.save('Exit')
        self.assertEqual("Italo Calvino's Cosmicomics by Sheri Prather", 
                         self.video_pg.video_title())
