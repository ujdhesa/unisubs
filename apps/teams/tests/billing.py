from __future__ import absolute_import
import collections
from datetime import datetime, timedelta
import itertools

from django.test import TestCase

from teams.models import BillingRecord, BillingReport, Task
from subtitles.pipeline import add_subtitles
from teams.permissions_const import (ROLE_CONTRIBUTOR, ROLE_MANAGER,
                                     ROLE_ADMIN)
from utils import test_factories
from utils import test_utils

def make_subtitle_lines(count, seconds=60):
    lines = []
    ms_per_line = seconds * 1000 // count
    for line_num in xrange(0, count):
        start_time = ms_per_line * line_num
        lines.append((start_time,
                      start_time + ms_per_line,
                      "subtitle %s" % line_num,
                     ))
    return lines

class DateMaker(object):
    """Get dates to use for billing events."""
    def __init__(self):
        self.current_date = self.start_date()

    def next_date(self):
        self.current_date += timedelta(days=1)
        return self.current_date

    def date_before_start(self):
        return self.start_date() - timedelta(days=1)

    def start_date(self):
        return datetime(2012, 1, 1, 0, 0, 0)

    def end_date(self):
        return self.current_date + timedelta(days=1)

def convert_rows_to_dicts(report_rows):
    """
    Converts each row into a dict, with the keys being the keys from the
    header row.
    """
    header_row = report_rows[0]
    rv = []
    for row in report_rows[1:]:
        rv.append(dict((header, value)
                       for (header, value) in zip(header_row, row)))
    return rv

def report_date(datetime):
    return datetime.strftime('%Y-%m-%d %H:%M:%S')

def group_report_rows(report_rows, key_columns):
    """Group report data in an easy to test way.

    Calls convert_rows_to_dicts() on each row, then converts the list of rows
    into a dict mapping the values from key_columns to rows.
    """
    rv = {}
    for row_data in convert_rows_to_dicts(report_rows):
        if len(key_columns) > 1:
            key = tuple(row_data[c] for c in key_columns)
        else:
            key = row_data[key_columns[0]]
        assert key not in rv, "Duplicate key: %s" % key
        rv[key] = row_data
    return rv

class BillingRecordTest(TestCase):
    def setUp(self):
        self.team = test_factories.create_team()

    def add_subtitles(self, video, *args, **kwargs):
        version = add_subtitles(video, *args, **kwargs)
        BillingRecord.objects.insert_record(version)
        return version

    def get_report_data(self, team, start_date, end_date):
        """Get report data in an easy to test way.
        """
        report = BillingReport.objects.create(
            start_date=start_date,
            end_date=end_date,
            type=BillingReport.TYPE_BILLING_RECORD)
        report.teams.add(team)
        return group_report_rows(report.generate_rows(),
                                 ('Video ID', 'Language'))

    def test_language_number(self):
        date_maker = DateMaker()
        user = test_factories.create_team_member(self.team).user

        video = test_factories.create_video(primary_audio_language_code='en')
        test_factories.create_team_video(self.team, user, video)
        self.add_subtitles(video, 'en', make_subtitle_lines(4),
                           created=date_maker.next_date(),
                           complete=True)
        self.add_subtitles(video, 'fr', make_subtitle_lines(4),
                           created=date_maker.next_date(),
                           complete=True)
        self.add_subtitles(video, 'de', make_subtitle_lines(4),
                           created=date_maker.next_date(),
                           complete=True)

        video2 = test_factories.create_video(primary_audio_language_code='en')
        test_factories.create_team_video(self.team, user, video2)
        # the english version was added before the date range of the report.
        # It should still bump the language number though.
        self.add_subtitles(video2, 'en', make_subtitle_lines(4),
                           created=date_maker.date_before_start(),
                           complete=True)
        self.add_subtitles(video2, 'fr', make_subtitle_lines(4),
                           created=date_maker.next_date(),
                           complete=True)

        data = self.get_report_data(self.team,
                                    date_maker.start_date(),
                                    date_maker.end_date())
        self.assertEquals(len(data), 4)
        self.assertEquals(data[video.video_id, 'en']['Language number'], 1)
        self.assertEquals(data[video.video_id, 'fr']['Language number'], 2)
        self.assertEquals(data[video.video_id, 'de']['Language number'], 3)
        self.assertEquals(data[video2.video_id, 'fr']['Language number'], 2)

    def test_missing_records(self):
        date_maker = DateMaker()
        user = test_factories.create_team_member(self.team).user

        video = test_factories.create_video(primary_audio_language_code='en')
        test_factories.create_team_video(self.team, user, video)
        # For en and de, we call pipeline.add_subtitles directly, so there's
        # no BillingRecord in the sytem.  This simulates the languages that
        # were completed before BillingRecords were around.
        add_subtitles(video, 'en', make_subtitle_lines(4),
                           created=date_maker.next_date(),
                           complete=True)
        add_subtitles(video, 'de', make_subtitle_lines(4),
                           created=date_maker.next_date(),
                           complete=True)
        # pt-br has a uncompleted subtitle language.  We should not list that
        # language in the report
        add_subtitles(video, 'pt-br', make_subtitle_lines(4),
                           created=date_maker.next_date(),
                           complete=False)
        self.add_subtitles(video, 'fr', make_subtitle_lines(4),
                           created=date_maker.next_date(),
                           complete=True)
        self.add_subtitles(video, 'es', make_subtitle_lines(4),
                           created=date_maker.next_date(),
                           complete=True)
        data = self.get_report_data(self.team,
                                    date_maker.start_date(),
                                    date_maker.end_date())
        self.assertEquals(len(data), 4)
        self.assertEquals(data[video.video_id, 'en']['Language number'], 0)
        self.assertEquals(data[video.video_id, 'de']['Language number'], 0)
        self.assertEquals(data[video.video_id, 'fr']['Language number'], 1)
        self.assertEquals(data[video.video_id, 'es']['Language number'], 2)
        self.assertEquals(data[video.video_id, 'en']['Minutes'], 0)
        self.assertEquals(data[video.video_id, 'de']['Minutes'], 0)

    def test_minutes(self):
        date_maker = DateMaker()
        user = test_factories.create_team_member(self.team).user

        video = test_factories.create_video(primary_audio_language_code='en')
        test_factories.create_team_video(self.team, user, video)
        self.add_subtitles(video, 'en', make_subtitle_lines(100, 100),
                           created=date_maker.next_date(), complete=True)
        self.add_subtitles(video, 'fr', make_subtitle_lines(100, 80),
                           created=date_maker.next_date(), complete=True)

        data = self.get_report_data(self.team,
                                    date_maker.start_date(),
                                    date_maker.end_date())
        self.assertEquals(len(data), 2)
        # For english the duration is 1:40, for french it's 1:20.  We should
        # always round up, so both should count as 2 minutes
        self.assertEquals(data[video.video_id, 'en']['Minutes'], 2)
        self.assertEquals(data[video.video_id, 'fr']['Minutes'], 2)

class ProcessReportTest(TestCase):
    def setUp(self):
        self.team = test_factories.create_team()
        self.report = BillingReport.objects.create(
            start_date=datetime(2013, 1, 1),
            end_date=datetime(2013, 2, 1),
            type=BillingReport.TYPE_APPROVAL)
        self.report.teams.add(self.team)

    @test_utils.patch_for_test("teams.models.BillingReport.generate_rows")
    def test_success(self, mock_generate_rows):
        mock_generate_rows.return_value = [
            ('Foo', 'Bar'),
            ('foo value', 'bar value'),
        ]
        self.report.process()
        self.assertNotEquals(self.report.processed, None)
        self.assertNotEquals(self.report.csv_file, None)

    @test_utils.patch_for_test("teams.models.BillingReport.generate_rows")
    def test_error(self, mock_generate_rows):
        mock_generate_rows.side_effect = ValueError()
        self.report.process()
        self.assertNotEquals(self.report.processed, None)
        self.assertEquals(self.report.csv_file, None)

class ApprovalTestBase(TestCase):
    @test_utils.patch_for_test('teams.models.Task.now')
    def setUp(self, mock_now):
        self.date_maker = DateMaker()
        mock_now.side_effect = self.date_maker.next_date
        self.setup_team()
        self.setup_users()
        self.setup_videos()

    def setup_team(self):
        self.team = test_factories.create_team(workflow_enabled=True)
        test_factories.create_tasks_workflow(
            self.team,
            review_allowed=20, # manager must review
            approve_allowed=20, # admin must approve
        )

    def setup_users(self):
        # make a bunch of users to subtitle/review the work
        subtitlers = [test_factories.create_user(pay_rate_code='S%s' % i)
                      for i in xrange(3)]
        reviewers = [test_factories.create_user(pay_rate_code='R%s' % i)
                     for i in xrange(2)]
        for u in subtitlers:
            test_factories.create_team_member(user=u, team=self.team,
                                              role=ROLE_CONTRIBUTOR)
        for u in reviewers:
            test_factories.create_team_member(user=u, team=self.team,
                                              role=ROLE_MANAGER)
        self.subtitler_iter = itertools.cycle(subtitlers)
        self.reviewer_iter = itertools.cycle(reviewers)

        self.admin = test_factories.create_team_member(team=self.team,
                                                       role=ROLE_ADMIN).user
        self.users = dict((unicode(u), u) for u in subtitlers + reviewers)

    def setup_videos(self):
        # make a bunch of languages that have moved through the review process
        self.subtitled_languages = collections.defaultdict(list)
        self.reviewed_languages = collections.defaultdict(list)
        self.notes = {}
        self.approved_languages = []
        self.approval_dates = {}
        self.review_dates = {}
        self.subtitle_dates = {}
        self.translations = set()

        v1 = test_factories.create_team_video(self.team).video
        v2 = test_factories.create_team_video(self.team).video
        v3 = test_factories.create_team_video(self.team).video
        languages = [
            (v1, 'en'),
            (v1, 'fr'),
            (v1, 'de'),
            (v1, 'pt-br'),
            (v2, 'en'),
            (v2, 'es'),
            (v2, 'fr'),
            (v2, 'de'),
            (v2, 'pt-br'),
            (v3, 'en'),
            (v3, 'de'),
        ]
        self.videos = {
            v1.video_id: v1,
            v2.video_id: v2,
            v3.video_id: v3,
        }
        notes_iter = itertools.cycle(['Great', 'Bad', 'Okay', ''])

        for i, (video, language_code) in enumerate(languages):
            video_id = video.video_id
            subtitler = self.subtitler_iter.next()
            reviewer = self.reviewer_iter.next()
            note = notes_iter.next()
            if i % 3 == 0:
                task_type = 'Translate'
                self.translations.add((video_id, language_code))
            else:
                task_type = 'Subtitle'
            review_task = test_factories.make_review_task(
                video.get_team_video(), language_code, subtitler, task_type,
                sub_data=make_subtitle_lines(10, 90))
            self.subtitle_dates[video_id, language_code] = \
                    self.date_maker.current_date
            review_task.body = note
            approve_task = review_task.complete_approved(reviewer)
            self.review_dates[video_id, language_code] = \
                    self.date_maker.current_date
            self.assertEquals(approve_task.type, Task.TYPE_IDS['Approve'])
            self.notes[video_id, language_code, 'Review'] = note
            if i < 6:
                # for some of those videos, approve them
                approve_task.complete_approved(self.admin)
                self.add_approved_language(video, language_code, subtitler,
                                           reviewer)
            if 6 <= i < 8:
                # for some of those videos, send them back to review, then
                # review again and approve the final result
                # for some of those videos, approve them
                review_task2 = approve_task.complete_rejected(self.admin)
                note = notes_iter.next()
                review_task2.body = note
                self.notes[video_id, language_code, 'Review'] = note
                approve_task2 = review_task2.complete_approved(reviewer)
                self.review_dates[video_id, language_code] = \
                        self.date_maker.current_date
                approve_task2.complete_approved(self.admin)
                self.add_approved_language(video, language_code, subtitler,
                                           reviewer)

    def add_approved_language(self, video, language_code, subtitler, reviewer):
        video_id = video.video_id
        self.approved_languages.append(
            video.subtitle_language(language_code))
        self.approval_dates[video_id, language_code] = \
                self.date_maker.current_date
        self.subtitled_languages[unicode(subtitler)].append((video_id,
                                                             language_code))
        self.reviewed_languages[unicode(reviewer)].append((video_id,
                                                           language_code))

class ApprovalTest(ApprovalTestBase):
    def get_report_data(self, start_date, end_date):
        """Get report data in an easy to test way.
        """
        report = BillingReport.objects.create(
            start_date=start_date, end_date=end_date,
            type=BillingReport.TYPE_APPROVAL)
        report.teams.add(self.team)
        return group_report_rows(report.generate_rows(),
                                 ('Video ID', 'Language'))

    def check_report_rows(self, report_data):
        # check that we got the right number of rows
        self.assertEquals(len(report_data), len(self.approved_languages))
        # check video ids and language codes
        self.assertEquals(set(report_data.keys()),
                          set((lang.video.video_id, lang.language_code)
                              for lang in self.approved_languages))

    def check_approver(self, report_data):
        for (video_id, language_code), row in report_data.items():
            approval_date = self.approval_dates[video_id, language_code]
            self.assertEquals(row['Approver'], unicode(self.admin))
            self.assertEquals(row['Date'], report_date(approval_date))

    def check_language_columns(self, report_data):
        for (video_id, language_code), row in report_data.items():
            lang = self.videos[video_id].subtitle_language(language_code)
            self.assertEquals(row['Original'],
                              lang.is_primary_audio_language())
            if (video_id, language_code) in self.translations:
                self.assertEquals(row['Translation?'], True)
            else:
                self.assertEquals(row['Translation?'], False)

    def check_minutes(self, report_data):
        # all subtitles are 90 seconds long, we should report this as 1.5
        # minutes.
        for (video_id, language_code), row in report_data.items():
            self.assertEquals(row['Minutes'], 1.5)

    def test_report(self):
        report_data = self.get_report_data(self.date_maker.start_date(),
                                    self.date_maker.end_date())
        self.check_report_rows(report_data)
        self.check_approver(report_data)
        self.check_language_columns(report_data)
        self.check_minutes(report_data)

class ApprovalForUsersTest(ApprovalTestBase):
    def get_report_data(self, start_date, end_date):
        """Get report data in an easy to test way.
        """
        report = BillingReport.objects.create(
            start_date=start_date, end_date=end_date,
            type=BillingReport.TYPE_APPROVAL_FOR_USERS)
        report.teams.add(self.team)
        return convert_rows_to_dicts(report.generate_rows())

    def check_report_rows(self, report_data):
        # we should have 2 rows per approved language, since each language has
        # a reviewer and subtitler
        self.assertEquals(len(report_data), len(self.approved_languages) * 2)
        report_users = [r['User'] for r in report_data]
        for u, langs in self.reviewed_languages.items():
            self.assertEquals(report_users.count(u), len(langs))
        self.assertEquals(report_users, list(sorted(report_users)))

    def check_videos_and_languages(self, report_data):
        for row in report_data:
            video_id = row['Video ID']
            language = row['Language']
            if (video_id, language) in self.subtitled_languages[row['User']]:
                if (video_id, language) in self.translations:
                    self.assertEquals(row['Task Type'], 'Translate')
                else:
                    self.assertEquals(row['Task Type'], 'Subtitle')
            elif (video_id, language) in self.reviewed_languages[row['User']]:
                self.assertEquals(row['Task Type'], 'Review')
            else:
                raise AssertionError("%s - %s was not subtitled or reviewed" %
                                     (video_id, language))

    def check_notes(self, report_data):
        for row in report_data:
            key = (row['Video ID'], row['Language'], row['Task Type'])
            correct_note = self.notes.get(key, '')
            if row['Note'] != correct_note:
                raise AssertionError("Wrong notes for %s, %s, %s.  "
                                     "note: %r should be %r" % (
                                         row['Video ID'], row['Language'],
                                         row['Task Type'], row['Note'],
                                         correct_note))

    def check_dates(self, report_data):
        for row in report_data:
            video_id = row['Video ID']
            language = row['Language']
            if row['Task Type'] in ('Subtitle', 'Translate'):
                subtitle_date = self.subtitle_dates[video_id, language]
                self.assertEquals(row['Date'], report_date(subtitle_date))
            elif row['Task Type'] == 'Review':
                review_date = self.review_dates[video_id, language]
                self.assertEquals(row['Date'], report_date(review_date))

    def check_minutes(self, report_data):
        # all subtitles are 90 seconds long, we should report this as 1.5
        # minutes.
        for row in report_data:
            self.assertEquals(row['Minutes'], 1.5)

    def check_pay_rates(self, report_data):
        # all subtitles are 90 seconds long, we should report this as 1.5
        # minutes.
        for row in report_data:
            user = self.users[row['User']]
            self.assertEquals(row['Pay Rate'], user.pay_rate_code)

    def test_report(self):
        report_data = self.get_report_data(self.date_maker.start_date(),
                                    self.date_maker.end_date())
        self.check_report_rows(report_data)
        self.check_videos_and_languages(report_data)
        self.check_notes(report_data)
        self.check_dates(report_data)
        self.check_minutes(report_data)
        self.check_pay_rates(report_data)

class SimpleApprovalTestCase(TestCase):
    @test_utils.patch_for_test('teams.models.Task.now')
    def setUp(self, mock_now):
        self.date_maker = DateMaker()
        mock_now.side_effect = self.date_maker.next_date
        self.team = test_factories.create_team(workflow_enabled=True)
        test_factories.create_tasks_workflow(
            self.team,
            review_allowed=0, # no review
            approve_allowed=20, # admin must approve
        )
        self.admin = test_factories.create_team_member(team=self.team,
                                                       role=ROLE_ADMIN).user
        self.video = test_factories.create_team_video(self.team).video

class ApprovalForUsersNoReviewTest(SimpleApprovalTestCase):
    # Test the approval for users type when review is disabled
    def test_report(self):
        approve_task = test_factories.make_approve_task(
            self.video.get_team_video(), 'en', self.admin, 'Subtitle')
        approve_task.complete_approved(self.admin)
        report = BillingReport.objects.create(
            start_date=self.date_maker.start_date(),
            end_date=self.date_maker.end_date(),
            type=BillingReport.TYPE_APPROVAL_FOR_USERS)
        report.teams.add(self.team)
        report_data = group_report_rows(report.generate_rows(),
                                        ('User',))
        self.assertEquals(len(report_data), 1)
        self.assertEquals(report_data[unicode(self.admin)]['Video ID'],
                          self.video.video_id)

class ApprovalReportSubtitleWithNoTimingTest(SimpleApprovalTestCase):
    # Test the approval for users type when review is disabled
    def check_report(self, subtitle_data):
        approve_task = test_factories.make_approve_task(
            self.video.get_team_video(), 'en', self.admin, 'Subtitle',
            subtitle_data)
        approve_task.complete_approved(self.admin)
        report = BillingReport.objects.create(
            start_date=self.date_maker.start_date(),
            end_date=self.date_maker.end_date(),
            type=BillingReport.TYPE_APPROVAL)
        report.teams.add(self.team)
        report_data = group_report_rows(report.generate_rows(),
                                        ('Video ID', 'Language'))
        self.assertEquals(len(report_data), 1)

    def test_no_timings_at_all(self):
        self.check_report([
            (None, None, 'subtitle without timing'),
        ])

    def test_extra_sub_without_timing_at_end(self):
        self.check_report([
            (100, 200, 'subtitle with timing'),
            (None, None, 'subtitle without timing'),
        ])

    def test_no_end_time(self):
        self.check_report([
            (100, 200, 'subtitle with timing'),
            (300, None, 'subtitle with no end time'),
        ])

    def test_no_start_time(self):
        self.check_report([
            (None, 200, 'subtitle with no start time'),
            (300, 400, 'subtitle with timing'),
        ])
