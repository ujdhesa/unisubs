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
from collections import defaultdict
from itertools import groupby
from math import ceil
import csv
import datetime
import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import connection, transaction
from django.db import models
from django.db.models.signals import post_save, post_delete, pre_delete
from django.http import Http404
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from haystack import site
from haystack.query import SQ

from auth.models import CustomUser as User
from auth.providers import get_authentication_provider
from messages import tasks as notifier
from subtitles.signals import language_deleted
from teams.workflow import TaskWorkflow, CollaborationWorkflow, Task
from teams import workflow
from teams.permissions_const import (
    TEAM_PERMISSIONS, PROJECT_PERMISSIONS, ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER,
    ROLE_CONTRIBUTOR
)
from videos.tasks import sync_latest_versions_for_video
from teams import tasks
from utils import DEFAULT_PROTOCOL
from utils.amazon import S3EnabledImageField, S3EnabledFileField
from utils.panslugify import pan_slugify
from utils.searching import get_terms
from videos.models import Video, SubtitleVersion, SubtitleLanguage
from subtitles.models import (
    SubtitleVersion as NewSubtitleVersion,
    SubtitleLanguage as NewSubtitleLanguage,
)

logger = logging.getLogger(__name__)
celery_logger = logging.getLogger('celery.task')

BILLING_CUTOFF = getattr(settings, 'BILLING_CUTOFF', None)
ALL_LANGUAGES = [(val, _(name))for val, name in settings.ALL_LANGUAGES]

# Teams
class TeamManager(models.Manager):
    def get_query_set(self):
        """Return a QS of all non-deleted teams."""
        return super(TeamManager, self).get_query_set().filter(deleted=False)

    def for_user(self, user):
        """Return a QS of all the (non-deleted) teams visible for the given user."""
        if user.is_authenticated():
            return self.get_query_set().filter(
                    models.Q(is_visible=True) |
                    models.Q(members__user=user)
            ).distinct()
        else:
            return self.get_query_set().filter(is_visible=True)

    def with_recent_billing_record(self, day_range):
        """Find teams that have had a new video recently"""
        start_date = (datetime.datetime.now() -
                      datetime.timedelta(days=day_range))
        team_ids = list(BillingRecord.objects
                        .order_by()
                        .filter(created__gt=start_date)
                        .values_list('team_id', flat=True)
                        .distinct())
        return Team.objects.filter(id__in=team_ids)

    def needs_new_video_notification(self, notify_interval):
        return (self.filter(
            notify_interval=notify_interval,
            teamvideo__created__gt=models.F('last_notification_time'))
            .distinct())


class Team(models.Model):
    APPLICATION = 1
    INVITATION_BY_MANAGER = 2
    INVITATION_BY_ALL = 3
    OPEN = 4
    INVITATION_BY_ADMIN = 5
    MEMBERSHIP_POLICY_CHOICES = (
            (OPEN, _(u'Open')),
            (APPLICATION, _(u'Application')),
            (INVITATION_BY_ALL, _(u'Invitation by any team member')),
            (INVITATION_BY_MANAGER, _(u'Invitation by manager')),
            (INVITATION_BY_ADMIN, _(u'Invitation by admin')),
            )

    VP_MEMBER = 1
    VP_MANAGER = 2
    VP_ADMIN = 3
    VIDEO_POLICY_CHOICES = (
        (VP_MEMBER, _(u'Any team member')),
        (VP_MANAGER, _(u'Managers and admins')),
        (VP_ADMIN, _(u'Admins only'))
    )

    TASK_ASSIGN_CHOICES = (
            (10, 'Any team member'),
            (20, 'Managers and admins'),
            (30, 'Admins only'),
            )
    TASK_ASSIGN_NAMES = dict(TASK_ASSIGN_CHOICES)
    TASK_ASSIGN_IDS = dict([choice[::-1] for choice in TASK_ASSIGN_CHOICES])

    SUBTITLE_CHOICES = (
            (10, 'Anyone'),
            (20, 'Any team member'),
            (30, 'Only managers and admins'),
            (40, 'Only admins'),
            )
    SUBTITLE_NAMES = dict(SUBTITLE_CHOICES)
    SUBTITLE_IDS = dict([choice[::-1] for choice in SUBTITLE_CHOICES])

    NOTIFY_DAILY = 'D'
    NOTIFY_HOURLY = 'H'
    NOTIFY_INTERVAL_CHOICES = (
        (NOTIFY_DAILY, _('Daily')),
        (NOTIFY_HOURLY, _('Hourly')),
    )

    name = models.CharField(_(u'name'), max_length=250, unique=True)
    slug = models.SlugField(_(u'slug'), unique=True)
    description = models.TextField(_(u'description'), blank=True, help_text=_('All urls will be converted to links. Line breaks and HTML not supported.'))

    logo = S3EnabledImageField(verbose_name=_(u'logo'), blank=True, upload_to='teams/logo/')
    is_visible = models.BooleanField(_(u'publicly Visible?'), default=True)
    videos = models.ManyToManyField(Video, through='TeamVideo',  verbose_name=_('videos'))
    users = models.ManyToManyField(User, through='TeamMember', related_name='teams', verbose_name=_('users'))

    # these allow unisubs to do things on user's behalf such as uploding subs to Youtub
    third_party_accounts = models.ManyToManyField("accountlinker.ThirdPartyAccount",  related_name='teams', verbose_name=_('third party accounts'))

    points = models.IntegerField(default=0, editable=False)
    applicants = models.ManyToManyField(User, through='Application', related_name='applicated_teams', verbose_name=_('applicants'))
    created = models.DateTimeField(auto_now_add=True)
    highlight = models.BooleanField(default=False)
    video = models.ForeignKey(Video, null=True, blank=True, related_name='intro_for_teams', verbose_name=_(u'Intro Video'))
    application_text = models.TextField(blank=True)
    page_content = models.TextField(_(u'Page content'), blank=True, help_text=_(u'You can use markdown. This will replace Description.'))
    is_moderated = models.BooleanField(default=False)
    header_html_text = models.TextField(blank=True, default='', help_text=_(u"HTML that appears at the top of the teams page."))
    last_notification_time = models.DateTimeField(editable=False, default=datetime.datetime.now)
    notify_interval = models.CharField(max_length=1,
                                       choices=NOTIFY_INTERVAL_CHOICES,
                                       default=NOTIFY_DAILY)

    auth_provider_code = models.CharField(_(u'authentication provider code'),
            max_length=24, blank=True, default="")

    # Enabling Features
    projects_enabled = models.BooleanField(default=False)
    workflow_style = models.CharField(max_length=1,
                                      default=workflow.WORKFLOW_DEFAULT,
                                      choices=workflow.WORKFLOW_CHOICES)

    # Policies and Permissions
    membership_policy = models.IntegerField(_(u'membership policy'),
            choices=MEMBERSHIP_POLICY_CHOICES,
            default=OPEN)
    video_policy = models.IntegerField(_(u'video policy'),
            choices=VIDEO_POLICY_CHOICES,
            default=VP_MEMBER)
    task_assign_policy = models.IntegerField(_(u'task assignment policy'),
            choices=TASK_ASSIGN_CHOICES,
            default=TASK_ASSIGN_IDS['Any team member'])
    subtitle_policy = models.IntegerField(_(u'subtitling policy'),
            choices=SUBTITLE_CHOICES,
            default=SUBTITLE_IDS['Anyone'])
    translate_policy = models.IntegerField(_(u'translation policy'),
            choices=SUBTITLE_CHOICES,
            default=SUBTITLE_IDS['Anyone'])
    max_tasks_per_member = models.PositiveIntegerField(_(u'maximum tasks per member'),
            default=None, null=True, blank=True)
    task_expiration = models.PositiveIntegerField(_(u'task expiration (days)'),
            default=None, null=True, blank=True)

    deleted = models.BooleanField(default=False)
    partner = models.ForeignKey('Partner', null=True, blank=True,
            related_name='teams')

    objects = TeamManager()
    all_objects = models.Manager() # For accessing deleted teams, if necessary.

    class Meta:
        ordering = ['name']
        verbose_name = _(u'Team')
        verbose_name_plural = _(u'Teams')

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super(Team, self).save(*args, **kwargs)
        if creating:
            # make sure we create a default project
            self.default_project

    def __unicode__(self):
        return self.name or self.slug

    def render_message(self, msg):
        """Return a string of HTML represention a team header for a notification.

        TODO: Get this out of the model and into a templatetag or something.

        """
        author_page = msg.author.get_absolute_url() if msg.author else ''
        context = {
            'team': self,
            'msg': msg,
            'author': msg.author,
            'author_page': author_page,
            'team_page': self.get_absolute_url(),
            "STATIC_URL": settings.STATIC_URL,
        }
        return render_to_string('teams/_team_message.html', context)

    def is_open(self):
        """Return whether this team's membership is open to the public."""
        return self.membership_policy == self.OPEN

    def is_by_application(self):
        """Return whether this team's membership is by application only."""
        return self.membership_policy == self.APPLICATION

    @classmethod
    def get(cls, slug, user=None, raise404=True):
        """Return the Team with the given slug.

        If a user is given the Team must be visible to that user.  Otherwise the
        Team must be visible to the public.

        If raise404 is given an Http404 exception will be raised if a suitable
        team is not found.  Otherwise None will be returned.

        """
        if user:
            qs = cls.objects.for_user(user)
        else:
            qs = cls.objects.filter(is_visible=True)
        try:
            return qs.get(slug=slug)
        except cls.DoesNotExist:
            try:
                return qs.get(pk=int(slug))
            except (cls.DoesNotExist, ValueError):
                pass

        if raise404:
            raise Http404

    def _get_workflow_enabled(self):
        """Deprecated way to check if tasks are enabled for this team."""
        return self.workflow_style == workflow.WORKFLOW_TASKS

    def _set_workflow_enabled(self, value):
        """Deprecated way to set the workflow style to tasks."""
        if value:
            self.workflow_style = workflow.WORKFLOW_TASKS
        else:
            self.workflow_style = workflow.WORKFLOW_DEFAULT
    workflow_enabled = property(_get_workflow_enabled, _set_workflow_enabled)

    def get_workflow(self):
        """Deprecated: get the TaskForkflow for this team.

        This is a letfover from when tasks were the only workflow option.  New
        code should use the workflow property.

        A workflow will always be returned.  If one isn't specified for the team
        a default (unsaved) one will be populated with default values and
        returned.
        """
        if self.workflow_enabled:
            try:
                return TaskWorkflow.objects.get(team=self)
            except TaskWorkflow.DoesNotExist:
                pass
        return TaskWorkflow(team=self)

    @property
    def workflow(self):
        if hasattr(self, '_workflow'):
            return self._workflow
        self._workflow = workflow.get_team_workflow(self)
        return self._workflow

    def clear_cached_workflow(self):
        if hasattr(self, '_workflow'):
            del self._workflow

    def collaboration_enabled(self):
        return self.workflow_style == workflow.WORKFLOW_COLLABORATION

    def tasks_enabled(self):
        return self.workflow_style == workflow.WORKFLOW_TASKS

    @property
    def auth_provider(self):
        """Return the authentication provider class for this Team, or None.

        No DB queries are used, so this is safe to call many times.

        """
        if not self.auth_provider_code:
            return None
        else:
            return get_authentication_provider(self.auth_provider_code)

    # Thumbnails
    def logo_thumbnail(self):
        """Return the URL for a kind-of small version of this team's logo, or None."""
        if self.logo:
            return self.logo.thumb_url(100, 100)

    def medium_logo_thumbnail(self):
        """Return the URL for a medium version of this team's logo, or None."""
        if self.logo:
            return self.logo.thumb_url(280, 100)

    def small_logo_thumbnail(self):
        """Return the URL for a really small version of this team's logo, or None."""
        if self.logo:
            return self.logo.thumb_url(50, 50)


    # URLs
    @models.permalink
    def get_absolute_url(self):
        return ('teams:dashboard', [self.slug])

    def get_site_url(self):
        """Return the full, absolute URL for this team, including http:// and the domain."""
        return '%s://%s%s' % (DEFAULT_PROTOCOL,
                              Site.objects.get_current().domain,
                              self.get_absolute_url())


    # Membership and roles
    def get_member(self, user):
        if not user.is_authenticated():
            raise TeamMember.DoesNotExist()
        return self.members.get(user=user)

    def _is_role(self, user, role=None):
        """Return whether the given user has the given role in this team.

        Safe to use with null or unauthenticated users.

        If no role is given, simply return whether the user is a member of this team at all.

        TODO: Change this to use the stuff in teams.permissions.

        """
        if not user or not user.is_authenticated():
            return False
        qs = self.members.filter(user=user)
        if role:
            qs = qs.filter(role=role)
        return qs.exists()

    def is_owner(self, user):
        """
        Return whether the given user is an owner of this team.
        """
        return self._is_role(user, TeamMember.ROLE_OWNER)

    def is_admin(self, user):
        """Return whether the given user is an admin of this team."""
        return self._is_role(user, TeamMember.ROLE_ADMIN)

    def is_manager(self, user):
        """Return whether the given user is a manager of this team."""
        return self._is_role(user, TeamMember.ROLE_MANAGER)

    def is_member(self, user):
        """Return whether the given user is a member of this team."""
        return self._is_role(user)

    def is_contributor(self, user, authenticated=True):
        """Return whether the given user is a contributor of this team, False otherwise."""
        return self._is_role(user, TeamMember.ROLE_CONTRIBUTOR)

    def can_see_video(self, user, team_video=None):
        """I have no idea.

        TODO: Figure out what this thing is, and if it's still necessary.

        """
        if not user.is_authenticated():
            return False
        return self.is_member(user)

    # moderation


    # Moderation
    def moderates_videos(self):
        """Return whether this team moderates videos in some way, False otherwise.

        Moderation means the team restricts who can create subtitles and/or
        translations.

        """
        if self.subtitle_policy != Team.SUBTITLE_IDS['Anyone']:
            return True

        if self.translate_policy != Team.SUBTITLE_IDS['Anyone']:
            return True

        return False

    def video_is_moderated_by_team(self, video):
        """Return whether this team moderates the given video."""
        return video.moderated_by == self


    # Item counts
    @property
    def member_count(self):
        """Return the number of members of this team.

        Caches the result in-object for performance.

        """
        if not hasattr(self, '_member_count'):
            setattr(self, '_member_count', self.users.count())
        return self._member_count

    @property
    def videos_count(self):
        """Return the number of videos of this team.

        Caches the result in-object for performance.

        """
        if not hasattr(self, '_videos_count'):
            setattr(self, '_videos_count', self.teamvideo_set.count())
        return self._videos_count

    def _count_tasks(self):
        qs = Task.objects.filter(team=self, deleted=False, completed=None)
        # quick, check, are there more than 1000 tasks, if so return 1001, and
        # let the UI display > 1000
        if qs[1000:1001].exists():
            return 1001
        else:
            return qs.count()

    @property
    def tasks_count(self):
        """Return the number of incomplete, undeleted tasks of this team.

        Caches the result in-object for performance.

        """
        if not hasattr(self, '_tasks_count'):
            setattr(self, '_tasks_count', self._count_tasks())
        return self._tasks_count

    # Applications (people applying to join)
    def application_message(self):
        """Return the membership application message for this team, or '' if none exists."""
        try:
            return self.settings.get(key=Setting.KEY_IDS['messages_application']).data
        except Setting.DoesNotExist:
            return ''

    @property
    def applications_count(self):
        """Return the number of open membership applications to this team.

        Caches the result in-object for performance.

        """
        if not hasattr(self, '_applications_count'):
            setattr(self, '_applications_count', self.applications.count())
        return self._applications_count


    # Language pairs
    def _lang_pair(self, lp, suffix):
        return SQ(content="{0}_{1}_{2}".format(lp[0], lp[1], suffix))

    def get_videos_for_languages_haystack(self, language=None,
                                          num_completed_langs=None,
                                          project=None, user=None, query=None,
                                          sort=None, exclude_language=None):
        qs = self.get_videos_for_user(user)

        if project:
            qs = qs.filter(project_pk=project.pk)

        if query:
            for term in get_terms(query):
                qs = qs.auto_query(qs.query.clean(term).decode('utf-8'))

        if language:
            qs = qs.filter(video_completed_langs=language)

        if exclude_language:
            qs = qs.exclude(video_completed_langs=exclude_language)

        if num_completed_langs is not None:
            qs = qs.filter(num_completed_langs=num_completed_langs)

        qs = qs.order_by({
             'name':  'video_title_exact',
            '-name': '-video_title_exact',
             'subs':  'num_completed_langs',
            '-subs': '-num_completed_langs',
             'time':  'team_video_create_date',
            '-time': '-team_video_create_date',
        }.get(sort or '-time'))

        return qs

    def get_videos_for_user(self, user):
        from teams.search_indexes import TeamVideoLanguagesIndex

        is_member = (user and user.is_authenticated()
                     and self.members.filter(user=user).exists())

        if is_member:
            return TeamVideoLanguagesIndex.results_for_members(self).filter(team_id=self.id)
        else:
            return TeamVideoLanguagesIndex.results().filter(team_id=self.id)

    # Projects
    @property
    def default_project(self):
        """Return the default project for this team.

        If it doesn't already exist it will be created.

        TODO: Move the creation into a signal on the team to avoid creating
        multiple default projects here?

        """
        try:
            return Project.objects.get(team=self, slug=Project.DEFAULT_NAME)
        except Project.DoesNotExist:
            p = Project(team=self,name=Project.DEFAULT_NAME)
            p.save()
            return p

    @property
    def has_projects(self):
        """Return whether this team has projects other than the default one."""
        return self.project_set.count() > 1


    # Readable/writeable language codes
    def get_writable_langs(self):
        """Return a list of language code strings that are writable for this team.

        This value may come from memcache.

        """
        return TeamLanguagePreference.objects.get_writable(self)

    def get_readable_langs(self):
        """Return a list of language code strings that are readable for this team.

        This value may come from memcache.

        """
        return TeamLanguagePreference.objects.get_readable(self)

# This needs to be constructed after the model definition since we need a
# reference to the class itself.
Team._meta.permissions = TEAM_PERMISSIONS


# Project
class ProjectManager(models.Manager):
    def for_team(self, team_identifier):
        """Return all non-default projects for the given team with the given identifier.

        The team_identifier passed may be an actual Team object, or a string
        containing a team slug, or the primary key of a team as an integer.

        """
        if hasattr(team_identifier, "pk"):
            team = team_identifier
        elif isinstance(team_identifier, int):
            team = Team.objects.get(pk=team_identifier)
        elif isinstance(team_identifier, str):
            team = Team.objects.get(slug=team_identifier)
        return Project.objects.filter(team=team).exclude(name=Project.DEFAULT_NAME)

    def all_projects_for_team(self, team):
        """Get all projects that a team is working

        This includes:
            - The default project
            - Other team projects
            - Projects shared with the team
        """
        return self.extra(where=[
            'team_id=%s OR EXISTS '
            '(SELECT 1 FROM teams_project_shared_teams shared_map '
            'WHERE shared_map.team_id=%s AND '
            'shared_map.project_id=teams_project.id)'],
            params=(team.id, team.id))

class Project(models.Model):
    # All tvs belong to a project, wheather the team has enabled them or not
    # the default project is just a convenience UI that pretends to be part of
    # the team . If this ever gets changed, you need to change migrations/0044
    DEFAULT_NAME = "_root"

    team = models.ForeignKey(Team)
    shared_teams = models.ManyToManyField(Team,
                                          related_name='shared_projects',
                                          blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(blank=True)

    name = models.CharField(max_length=255, null=False)
    description = models.TextField(blank=True, null=True, max_length=2048)
    guidelines = models.TextField(blank=True, null=True, max_length=2048)

    slug = models.SlugField(blank=True)
    order = models.PositiveIntegerField(default=0)

    objects = ProjectManager()

    def __unicode__(self):
        if self.is_default_project:
            return u"---------"
        return u"%s" % (self.name)

    def save(self, slug=None,*args, **kwargs):
        self.modified = datetime.datetime.now()
        slug = slug if slug is not None else self.slug or self.name
        self.slug = pan_slugify(slug)
        super(Project, self).save(*args, **kwargs)

    @property
    def is_default_project(self):
        """Return whether this project is a default project for a team."""
        return self.name == Project.DEFAULT_NAME


    def get_site_url(self):
        """Return the full, absolute URL for this project, including http:// and the domain."""
        return '%s://%s%s' % (DEFAULT_PROTOCOL, Site.objects.get_current().domain, self.get_absolute_url())

    @models.permalink
    def get_absolute_url(self):
        return ('teams:project_video_list', [self.team.slug, self.slug])


    @property
    def videos_count(self):
        """Return the number of videos in this project.

        Caches the result in-object for performance.

        """
        if not hasattr(self, '_videos_count'):
            setattr(self, '_videos_count', TeamVideo.objects.filter(project=self).count())
        return self._videos_count

    def _count_tasks(self):
        qs = tasks.filter(team_video__project = self)
        # quick, check, are there more than 1000 tasks, if so return 1001, and
        # let the UI display > 1000
        if qs[1000:1001].exists():
            return 1001
        else:
            return qs.count()

    @property
    def tasks_count(self):
        """Return the number of incomplete, undeleted tasks in this project.

        Caches the result in-object for performance.

        """
        tasks = Task.objects.filter(team=self.team, deleted=False, completed=None)

        if not hasattr(self, '_tasks_count'):
            setattr(self, '_tasks_count', self._count_tasks())
        return self._tasks_count


    class Meta:
        unique_together = (
                ("team", "name",),
                ("team", "slug",),
        )
        permissions = PROJECT_PERMISSIONS


# TeamVideo
class TeamVideo(models.Model):
    THUMBNAIL_SIZE = (288, 162)

    team = models.ForeignKey(Team)
    video = models.OneToOneField(Video)
    description = models.TextField(blank=True,
        help_text=_(u'Use this space to explain why you or your team need to '
                    u'caption or subtitle this video. Adding a note makes '
                    u'volunteers more likely to help out!'))
    thumbnail = S3EnabledImageField(upload_to='teams/video_thumbnails/', null=True, blank=True,
        help_text=_(u'We automatically grab thumbnails for certain sites, e.g. Youtube'),
                                    thumb_sizes=(THUMBNAIL_SIZE, (120,90),))
    all_languages = models.BooleanField(_('Need help with all languages'), default=False,
        help_text=_(u'If you check this, other languages will not be displayed.'))
    added_by = models.ForeignKey(User)
    # this is an auto_add like field, but done on the model save so the
    # admin doesn't throw a fit
    created = models.DateTimeField(blank=True)
    partner_id = models.CharField(max_length=100, blank=True, default="")

    project = models.ForeignKey(Project)

    class Meta:
        unique_together = (('team', 'video'),)

    def __unicode__(self):
        return unicode(self.video)

    @models.permalink
    def get_absolute_url(self):
        return ('teams:team_video', [self.pk])

    def get_thumbnail(self):
        if self.thumbnail:
            return self.thumbnail.thumb_url(*TeamVideo.THUMBNAIL_SIZE)

        video_thumb = self.video.get_thumbnail(fallback=False)
        if video_thumb:
            return video_thumb

        return "%simages/video-no-thumbnail-medium.png" % settings.STATIC_URL_BASE

    def _original_language(self):
        if not hasattr(self, 'original_language_code'):
            sub_lang = self.video.subtitle_language()
            setattr(self, 'original_language_code', None if not sub_lang else sub_lang.language)
        return getattr(self, 'original_language_code')

    def save(self, *args, **kwargs):
        if not hasattr(self, "project"):
            self.project = self.team.default_project

        assert self.project.team == self.team, \
                    "%s: Team (%s) is not equal to project's (%s) team (%s)"\
                         % (self, self.team, self.project, self.project.team)

        if not self.pk:
            self.created = datetime.datetime.now()
        super(TeamVideo, self).save(*args, **kwargs)


    def is_checked_out(self, ignore_user=None):
        '''Return whether this video is checked out in a task.

        If a user is given, checkouts by that user will be ignored.  This
        provides a way to ask "can user X check out or work on this task?".

        This is similar to the writelocking done on Videos and
        SubtitleLanguages.

        '''
        tasks = self.task_set.filter(
                # Find all tasks for this video which:
                deleted=False,           # - Aren't deleted
                assignee__isnull=False,  # - Are assigned to someone
                language="",             # - Aren't specific to a language
                completed__isnull=True,  # - Are unfinished
        )
        if ignore_user:
            tasks = tasks.exclude(assignee=ignore_user)

        return tasks.exists()


    # Convenience functions
    def subtitles_started(self):
        """Return whether subtitles have been started for this video."""
        from subtitles.models import SubtitleLanguage
        return (SubtitleLanguage.objects.having_nonempty_versions()
                                        .filter(video=self.video)
                                        .exists())

    def subtitles_finished(self):
        """Return whether at least one set of subtitles has been finished for this video."""
        qs = (self.video.newsubtitlelanguage_set.having_public_versions()
              .filter(subtitles_complete=True))
        for lang in qs:
            if lang.is_synced():
                return True
        return False

    def get_workflow(self):
        """Return the appropriate TaskWorkflow for this TeamVideo."""
        return TaskWorkflow.get_for_team_video(self)

    def move_to(self, new_team, project=None):
        """
        Moves this TeamVideo to a new team.
        This method expects you to have run the correct permissions checks.
        """
        old_team = self.team
        if old_team == new_team:
            return

        # these imports are here to avoid circular imports, hacky
        from teams.signals import api_teamvideo_new
        from teams.signals import video_moved_from_team_to_team
        from videos import metadata_manager
        # For now, we'll just delete any tasks associated with the moved video.
        self.task_set.update(deleted=True)

        # We move the video by just switching the team, instead of deleting and
        # recreating it.
        self.team = new_team

        # projects are always team dependent:
        if project:
            self.project = project
        else:
            self.project = new_team.default_project

        self.save()

        # We need to make any as-yet-unmoderated versions public.
        # TODO: Dedupe this and the team video delete signal.
        video = self.video

        video.newsubtitleversion_set.extant().update(visibility='public')
        video.is_public = new_team.is_visible
        video.moderated_by = new_team if new_team.moderates_videos() else None
        video.save()

        TeamVideoMigration.objects.create(from_team=old_team,
                                          to_team=new_team,
                                          to_project=self.project)

        # Update all Solr data.
        metadata_manager.update_metadata(video.pk)
        video.update_search_index()
        tasks.update_one_team_video(self.pk)

        # Create any necessary tasks.
        autocreate_tasks(self)

        # fire a http notification that a new video has hit this team:
        api_teamvideo_new.send(self)
        video_moved_from_team_to_team.send(sender=self,
                destination_team=new_team, video=self.video)

class TeamVideoMigration(models.Model):
    from_team = models.ForeignKey(Team, related_name='+')
    to_team = models.ForeignKey(Team, related_name='+')
    to_project = models.ForeignKey(Project, related_name='+')
    datetime = models.DateTimeField()

    def __init__(self, *args, **kwargs):
        if 'datetime' not in kwargs:
            kwargs['datetime'] = self.now()
        models.Model.__init__(self, *args, **kwargs)

    @staticmethod
    def now():
        # Make now a function so we can patch it in the unittests
        return datetime.datetime.now()

def _create_translation_tasks(team_video, subtitle_version=None):
    """Create any translation tasks that should be autocreated for this video.

    subtitle_version should be the original SubtitleVersion that these tasks
    will probably be translating from.

    """
    preferred_langs = TeamLanguagePreference.objects.get_preferred(team_video.team)

    for lang in preferred_langs:
        # Don't create tasks for languages that are already complete.
        sl = team_video.video.subtitle_language(lang)
        if sl and sl.is_complete_and_synced():
            continue

        # Don't create tasks for languages that already have one.  This includes
        # review/approve tasks and such.
        # Doesn't matter if it's complete or not.
        task_exists = Task.objects.not_deleted().filter(
            team=team_video.team, team_video=team_video, language=lang
        ).exists()
        if task_exists:
            continue

        # Otherwise, go ahead and create it.
        task = Task(team=team_video.team, team_video=team_video,
                    language=lang, type=Task.TYPE_IDS['Translate'])

        # we should only update the team video after all tasks for
        # this video are saved, else we end up with a lot of
        # wasted tasks
        task.save(update_team_video_index=False)

    tasks.update_one_team_video.delay(team_video.pk)

def autocreate_tasks(team_video):
    workflow = TaskWorkflow.get_for_team_video(team_video)
    existing_subtitles = team_video.video.completed_subtitle_languages(public_only=True)

    # We may need to create a transcribe task, if there are no existing subs.
    if workflow.autocreate_subtitle and not existing_subtitles:
        if not team_video.task_set.not_deleted().exists():
            original_language = team_video.video.primary_audio_language_code
            Task(team=team_video.team,
                 team_video=team_video,
                 subtitle_version=None,
                 language= original_language or '',
                 type=Task.TYPE_IDS['Subtitle']
            ).save()

    # If there are existing subtitles, we may need to create translate tasks.
    #
    # TODO: This sets the "source version" for the translations to an arbitrary
    #       language's version.  In practice this probably won't be a problem
    #       because most teams will transcribe one language and then send to a
    #       new team for translation, but we can probably be smarter about this
    #       if we spend some time.
    if workflow.autocreate_translate and existing_subtitles:
        _create_translation_tasks(team_video)


def team_video_save(sender, instance, created, **kwargs):
    """Update the Solr index for this team video.

    TODO: Rename this to something more specific.

    """
    tasks.update_one_team_video.delay(instance.id)

def team_video_delete(sender, instance, **kwargs):
    """Perform necessary actions for when a TeamVideo is deleted.

    TODO: Split this up into separate signals.

    """
    from videos import metadata_manager
    # not using an async task for this since the async task
    # could easily execute way after the instance is gone,
    # and backend.remove requires the instance.
    tv_search_index = site.get_index(TeamVideo)
    tv_search_index.backend.remove(instance)
    try:
        video = instance.video

        # we need to publish all unpublished subs for this video:
        NewSubtitleVersion.objects.filter(video=video,
                visibility='private').update(visibility='public')

        video.is_public = True
        video.moderated_by = None
        video.save()

        metadata_manager.update_metadata(video.pk)
        video.update_search_index()
        sync_latest_versions_for_video.delay(video.pk)
    except Video.DoesNotExist:
        pass

def on_language_deleted(sender, **kwargs):
    """When a language is deleted, delete all tasks associated with it."""
    team_video = sender.video.get_team_video()
    if not team_video:
        return
    Task.objects.filter(team_video=team_video,
                        language=sender.language_code).delete()
    # check if there are no more source languages for the video, and in that
    # case delete all transcribe tasks.  Don't delete:
    #     - transcribe tasks that have already been started
    #     - review tasks
    #     - approve tasks
    if not sender.video.has_public_version():
        # filtering on new_subtitle_version=None excludes all 3 cases where we
        # don't want to delete tasks
        Task.objects.filter(team_video=team_video,
                            new_subtitle_version=None).delete()

def team_video_autocreate_task(sender, instance, created, raw, **kwargs):
    """Create subtitle/translation tasks for a newly added TeamVideo, if necessary."""
    if created and not raw:
        autocreate_tasks(instance)

def team_video_add_video_moderation(sender, instance, created, raw, **kwargs):
    """Set the .moderated_by attribute on a newly created TeamVideo's Video, if necessary."""
    if created and not raw and instance.team.moderates_videos():
        instance.video.moderated_by = instance.team
        instance.video.save()

def team_video_rm_video_moderation(sender, instance, **kwargs):
    """Clear the .moderated_by attribute on a newly deleted TeamVideo's Video, if necessary."""
    try:
        # when removing a video, this will be triggered by the fk constraing
        # and will be already removed
        instance.video.moderated_by = None
        instance.video.save()
    except Video.DoesNotExist:
        pass


post_save.connect(team_video_save, TeamVideo, dispatch_uid="teams.teamvideo.team_video_save")
post_save.connect(team_video_autocreate_task, TeamVideo, dispatch_uid='teams.teamvideo.team_video_autocreate_task')
post_save.connect(team_video_add_video_moderation, TeamVideo, dispatch_uid='teams.teamvideo.team_video_add_video_moderation')
post_delete.connect(team_video_delete, TeamVideo, dispatch_uid="teams.teamvideo.team_video_delete")
post_delete.connect(team_video_rm_video_moderation, TeamVideo, dispatch_uid="teams.teamvideo.team_video_rm_video_moderation")
language_deleted.connect(on_language_deleted, dispatch_uid="teams.subtitlelanguage.language_deleted")

# TeamMember
class TeamMemberManager(models.Manager):
    use_for_related_fields = True

    def create_first_member(self, team, user):
        """Make sure that new teams always have an 'owner' member."""

        tm = TeamMember(team=team, user=user, role=ROLE_OWNER)
        tm.save()
        return tm

class TeamMember(models.Model):
    ROLE_OWNER = ROLE_OWNER
    ROLE_ADMIN = ROLE_ADMIN
    ROLE_MANAGER = ROLE_MANAGER
    ROLE_CONTRIBUTOR = ROLE_CONTRIBUTOR

    ROLES = (
        (ROLE_OWNER, _("Owner")),
        (ROLE_MANAGER, _("Manager")),
        (ROLE_ADMIN, _("Admin")),
        (ROLE_CONTRIBUTOR, _("Contributor")),
    )

    team = models.ForeignKey(Team, related_name='members')
    user = models.ForeignKey(User, related_name='team_members')
    role = models.CharField(max_length=16, default=ROLE_CONTRIBUTOR, choices=ROLES, db_index=True)
    created = models.DateTimeField(default=datetime.datetime.now, null=True,
            blank=True)

    objects = TeamMemberManager()

    def __unicode__(self):
        return u'%s' % self.user


    def project_narrowings(self):
        """Return any project narrowings applied to this member."""
        return self.narrowings.filter(project__isnull=False)

    def language_narrowings(self):
        """Return any language narrowings applied to this member."""
        return self.narrowings.filter(project__isnull=True)


    def project_narrowings_fast(self):
        """Return any project narrowings applied to this member.

        Caches the result in-object for speed.

        """
        return [n for n in  self.narrowings_fast() if n.project]

    def language_narrowings_fast(self):
        """Return any language narrowings applied to this member.

        Caches the result in-object for speed.

        """
        return [n for n in self.narrowings_fast() if n.language]

    def narrowings_fast(self):
        """Return any narrowings (both project and language) applied to this member.

        Caches the result in-object for speed.

        """
        if hasattr(self, '_cached_narrowings'):
            if self._cached_narrowings is not None:
                return self._cached_narrowings

        self._cached_narrowings = self.narrowings.all()
        return self._cached_narrowings


    def has_max_tasks(self):
        """Return whether this member has the maximum number of tasks."""
        max_tasks = self.team.max_tasks_per_member
        if max_tasks:
            if self.user.task_set.incomplete().filter(team=self.team).count() >= max_tasks:
                return True
        return False


    class Meta:
        unique_together = (('team', 'user'),)


def clear_tasks(sender, instance, *args, **kwargs):
    """Unassign all tasks assigned to a user.

    Used when deleting a user from a team.

    """
    tasks = instance.team.task_set.incomplete().filter(assignee=instance.user)
    tasks.update(assignee=None)

pre_delete.connect(clear_tasks, TeamMember, dispatch_uid='teams.members.clear-tasks-on-delete')


# MembershipNarrowing
class MembershipNarrowing(models.Model):
    """Represent narrowings that can be made on memberships.

    A single MembershipNarrowing can apply to a project or a language, but not both.

    """
    member = models.ForeignKey(TeamMember, related_name="narrowings")
    project = models.ForeignKey(Project, null=True, blank=True)
    language = models.CharField(max_length=24, blank=True, choices=ALL_LANGUAGES)

    added_by = models.ForeignKey(TeamMember, related_name="narrowing_includer", null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True, blank=None)
    modified = models.DateTimeField(auto_now=True, blank=None)

    def __unicode__(self):
        if self.project:
            return u"Permission restriction for %s to project %s " % (self.member, self.project)
        else:
            return u"Permission restriction for %s to language %s " % (self.member, self.language)


    def save(self, *args, **kwargs):
        # Cannot have duplicate narrowings for a language.
        if self.language:
            duplicate_exists = MembershipNarrowing.objects.filter(
                member=self.member, language=self.language
            ).exclude(id=self.id).exists()

            assert not duplicate_exists, "Duplicate language narrowing detected!"

        # Cannot have duplicate narrowings for a project.
        if self.project:
            duplicate_exists = MembershipNarrowing.objects.filter(
                member=self.member, project=self.project
            ).exclude(id=self.id).exists()

            assert not duplicate_exists, "Duplicate project narrowing detected!"

        return super(MembershipNarrowing, self).save(*args, **kwargs)


class ApplicationInvalidException(Exception):
    pass

class ApplicationManager(models.Manager):

    def can_apply(self, team, user):
        """
        A user can apply either if he is not a member of the team yet, the
        team hasn't said no to the user (either application denied or removed the user'
        and if no applications are pending.
        """
        sour_application_exists =  self.filter(team=team, user=user, status__in=[
            Application.STATUS_MEMBER_REMOVED, Application.STATUS_DENIED,
            Application.STATUS_PENDING]).exists()
        if sour_application_exists:
            return False
        return  not team.is_member(user)

    def open(self, team=None, user=None):
        qs =  self.filter(status=Application.STATUS_PENDING)
        if team:
            qs = qs.filter(team=team)
        if user:
            qs = qs.filter(user=user)
        return qs


# Application
class Application(models.Model):
    team = models.ForeignKey(Team, related_name='applications')
    user = models.ForeignKey(User, related_name='team_applications')
    note = models.TextField(blank=True)
    # None -> not acted upon
    # True -> Approved
    # False -> Rejected
    STATUS_PENDING,STATUS_APPROVED, STATUS_DENIED, STATUS_MEMBER_REMOVED,\
        STATUS_MEMBER_LEFT = xrange(0, 5)
    STATUSES = (
        (STATUS_PENDING, u"Pending"),
        (STATUS_APPROVED, u"Approved"),
        (STATUS_DENIED, u"Denied"),
        (STATUS_MEMBER_REMOVED, u"Member Removed"),
        (STATUS_MEMBER_LEFT, u"Member Left"),
    )
    STATUSES_IDS = dict([choice[::-1] for choice in STATUSES])

    status = models.PositiveIntegerField(default=STATUS_PENDING, choices=STATUSES)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True)

    # free text keeping a log of changes to this application
    history = models.TextField(blank=True, null=True)

    objects = ApplicationManager()
    class Meta:
        unique_together = (('team', 'user', 'status'),)


    def approve(self, author, interface):
        """Approve the application.

        This will create an appropriate TeamMember if this application has
        not been already acted upon
        """
        if self.status not in (Application.STATUS_PENDING, Application.STATUS_MEMBER_LEFT):
            raise ApplicationInvalidException("")
        member, created = TeamMember.objects.get_or_create(team=self.team, user=self.user)
        if created:
            notifier.team_member_new.delay(member.pk)
        self.modified = datetime.datetime.now()
        self.status = Application.STATUS_APPROVED
        self.save(author=author, interface=interface)
        return self

    def deny(self, author, interface):
        """
        Marks the application as not approved, then
        Queue a Celery task that will handle properly denying this
        application.
        """
        if self.status != Application.STATUS_PENDING:
            raise ApplicationInvalidException("")
        self.modified = datetime.datetime.now()
        self.status = Application.STATUS_DENIED
        self.save(author=author, interface=interface)
        notifier.team_application_denied.delay(self.pk)
        return self

    def on_member_leave(self, author, interface):
        """
        Marks the appropriate status, but users can still
        reapply to a team if they so desire later.
        """
        self.status = Application.STATUS_MEMBER_LEFT
        self.save(author=author, interface=interface)

    def on_member_removed(self, author, interface):
        """
        Marks the appropriate status so that user's cannot reapply
        to a team after being removed.
        """
        self.status = Application.STATUS_MEMBER_REMOVED
        self.save(author=author, interface=interface)

    def _generate_history_line(self, new_status, author=None, interface=None):
        author = author or "?"
        interface = interface or "web UI"
        new_status = new_status if new_status != None else Application.STATUS_PENDING
        for value,name in Application.STATUSES:
            if value == new_status:
                status = name
        assert status
        return u"%s by %s from %s (%s)\n" % (status, author, interface, datetime.datetime.now())

    def save(self, dispatches_http_callback=True, author=None, interface=None, *args, **kwargs):
        """
        Saves the model, but also appends a line on the history for that
        model, like these:
           - CoolGuy Approved through the web UI.
           - Arthur Left team through the web UI.
        This way,we can keep one application per user per team, never
        delete them (so the messages stay current) and we still can
        track history
        """
        self.history = (self.history or "") + self._generate_history_line(self.status, author, interface)
        super(Application, self).save(*args, **kwargs)
        if dispatches_http_callback:
            from teams.signals import api_application_new
            api_application_new.send(self)

    def __unicode__(self):
        return "Application: %s - %s - %s" % (self.team.slug, self.user.username, self.get_status_display())


# Invites
class InviteExpiredException(Exception):
    pass

class InviteManager(models.Manager):
    def pending_for(self, team, user):
        return self.filter(team=team, user=user, approved=None)

    def acted_on(self, team, user):
        return self.filter(team=team, user=user, approved__notnull=True)

class Invite(models.Model):
    team = models.ForeignKey(Team, related_name='invitations')
    user = models.ForeignKey(User, related_name='team_invitations')
    note = models.TextField(blank=True, max_length=200)
    author = models.ForeignKey(User)
    role = models.CharField(max_length=16, choices=TeamMember.ROLES,
                            default=TeamMember.ROLE_CONTRIBUTOR)
    # None -> not acted upon
    # True -> Approved
    # False -> Rejected
    approved = models.NullBooleanField(default=None)

    objects = InviteManager()

    def accept(self):
        """Accept this invitation.

        Creates an appropriate TeamMember record, sends a notification and
        deletes itself.

        """
        if self.approved is not None:
            raise InviteExpiredException("")
        self.approved = True
        member, created = TeamMember.objects.get_or_create(
            team=self.team, user=self.user, role=self.role)
        if created:
            notifier.team_member_new.delay(member.pk)
        self.save()
        return True

    def deny(self):
        """Deny this invitation.

        Could be useful to send a notification here in the future.

        """
        if self.approved is not None:
            raise InviteExpiredException("")
        self.approved = False
        self.save()


    def message_json_data(self, data, msg):
        data['can-reply'] = False
        return data


# Settings
class SettingManager(models.Manager):
    use_for_related_fields = True

    def guidelines(self):
        """Return a QS of settings related to team guidelines."""
        keys = [key for key, name in Setting.KEY_CHOICES
                if name.startswith('guidelines_')]
        return self.get_query_set().filter(key__in=keys)

    def messages(self):
        """Return a QS of settings related to team messages."""
        keys = [key for key, name in Setting.KEY_CHOICES
                if name.startswith('messages_')]
        return self.get_query_set().filter(key__in=keys)

    def messages_guidelines(self):
        """Return a QS of settings related to team messages or guidelines."""
        keys = [key for key, name in Setting.KEY_CHOICES
                if name.startswith('messages_') or name.startswith('guidelines_')]
        return self.get_query_set().filter(key__in=keys)

class Setting(models.Model):
    KEY_CHOICES = (
        (100, 'messages_invite'),
        (101, 'messages_manager'),
        (102, 'messages_admin'),
        (103, 'messages_application'),
        (200, 'guidelines_subtitle'),
        (201, 'guidelines_translate'),
        (202, 'guidelines_review'),
        # 300s means if this team will block those notifications
        (300, 'block_invitation_sent_message'),
        (301, 'block_application_sent_message'),
        (302, 'block_application_denided_message'),
        (303, 'block_team_member_new_message'),
        (304, 'block_team_member_leave_message'),
        (305, 'block_task_assigned_message'),
        (306, 'block_reviewed_and_published_message'),
        (307, 'block_reviewed_and_pending_approval_message'),
        (308, 'block_reviewed_and_sent_back_message'),
        (309, 'block_approved_message'),
        (310, 'block_new_video_message'),
    )
    KEY_NAMES = dict(KEY_CHOICES)
    KEY_IDS = dict([choice[::-1] for choice in KEY_CHOICES])

    key = models.PositiveIntegerField(choices=KEY_CHOICES)
    data = models.TextField(blank=True)
    team = models.ForeignKey(Team, related_name='settings')

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    objects = SettingManager()

    class Meta:
        unique_together = (('key', 'team'),)

    def __unicode__(self):
        return u'%s - %s' % (self.team, self.key_name)

    @property
    def key_name(self):
        """Return the key name for this setting.

        TODO: Remove this and replace with get_key_display()?

        """
        return Setting.KEY_NAMES[self.key]


# TeamLanguagePreferences
class TeamLanguagePreferenceManager(models.Manager):
    def _generate_writable(self, team):
        """Return the set of language codes that are writeable for this team."""
        langs_set = set([x[0] for x in settings.ALL_LANGUAGES])

        unwritable = self.for_team(team).filter(allow_writes=False, preferred=False).values("language_code")
        unwritable = set([x['language_code'] for x in unwritable])

        return langs_set - unwritable

    def _generate_readable(self, team):
        """Return the set of language codes that are readable for this team."""
        langs = set([x[0] for x in settings.ALL_LANGUAGES])

        unreadable = self.for_team(team).filter(allow_reads=False, preferred=False).values("language_code")
        unreadable = set([x['language_code'] for x in unreadable])

        return langs - unreadable

    def _generate_preferred(self, team):
        """Return the set of language codes that are preferred for this team."""
        preferred = self.for_team(team).filter(preferred=True).values("language_code")
        return set([x['language_code'] for x in preferred])


    def for_team(self, team):
        """Return a QS of all language preferences for the given team."""
        return self.get_query_set().filter(team=team)

    def on_changed(cls, sender,  instance, *args, **kwargs):
        """Perform any necessary actions when a language preference changes.

        TODO: Refactor this out of the manager...

        """
        from teams.cache import invalidate_lang_preferences
        invalidate_lang_preferences(instance.team)


    def get_readable(self, team):
        """Return the set of language codes that are readable for this team.

        This value may come from memcache if possible.

        """
        from teams.cache import get_readable_langs
        return get_readable_langs(team)

    def get_writable(self, team):
        """Return the set of language codes that are writeable for this team.

        This value may come from memcache if possible.

        """
        from teams.cache import get_writable_langs
        return get_writable_langs(team)

    def get_preferred(self, team):
        """Return the set of language codes that are preferred for this team.

        This value may come from memcache if possible.

        """
        from teams.cache import get_preferred_langs
        return get_preferred_langs(team)

class TeamLanguagePreference(models.Model):
    """Represent language preferences for a given team.

    This model preresents language preferences for the old tasks-style
    workflow model.  For the new collaboration style, we use
    CollaborationLanguage.

    First, TLPs may mark a language as "preferred".  If that's the case then the
    other attributes of this model are irrelevant and can be ignored.
    "Preferred" languages will have translation tasks automatically created for
    them when subtitles are added.

    If preferred is False, the TLP describes a *restriction* on the language
    instead.  Writing in that language may be prevented, or both reading and
    writing may be prevented.

    (Note: "writing" means not only writing new subtitles but also creating
    tasks, etc)

    This is how the restriction settings should interact.  TLP means that we
    have created a TeamLanguagePreference for that team and language.

    | Action                                 | NO  | allow_read=True,  | allow_read=False, |
    |                                        | TLP | allow_write=False | allow_write=False |
    ========================================================================================
    | assignable as tasks                    | X   |                   |                   |
    | assignable as narrowing                | X   |                   |                   |
    | listed on the widget for viewing       | X   | X                 |                   |
    | listed on the widget for improving     | X   |                   |                   |
    | returned from the api read operations  | X   | X                 |                   |
    | upload / write operations from the api | X   |                   |                   |
    | show up on the start dialog            | X   |                   |                   |
    +----------------------------------------+-----+-------------------+-------------------+

    Remember, this table only applies if preferred=False.  If the language is
    preferred the "restriction" attributes are effectively garbage.  Maybe we
    should make the column nullable to make this more clear?

    allow_read=True, allow_write=True, preferred=False is invalid.  Just remove
    the row all together.

    """
    team = models.ForeignKey(Team, related_name="lang_preferences")
    language_code = models.CharField(max_length=16)

    allow_reads = models.BooleanField()
    allow_writes = models.BooleanField()
    preferred = models.BooleanField(default=False)

    objects = TeamLanguagePreferenceManager()

    class Meta:
        unique_together = ('team', 'language_code')


    def clean(self, *args, **kwargs):
        if self.allow_reads and self.allow_writes:
            raise ValidationError("No sense in having all allowed, just remove the preference for this language.")

        if self.preferred and (self.allow_reads or self.allow_writes):
            raise ValidationError("Cannot restrict a preferred language.")

        super(TeamLanguagePreference, self).clean(*args, **kwargs)

    def __unicode__(self):
        return u"%s preference for team %s" % (self.language_code, self.team)


post_save.connect(TeamLanguagePreference.objects.on_changed, TeamLanguagePreference)

class CollaborationLanguageManager(models.Manager):
    def for_team(self, team):
        """Get preferred languages for a team."""
        return self.filter(team=team, project=None)

    def update_for_team(self, team, language_codes):
        """Update preferred languages for a team."""
        (self.for_team(team)
         .exclude(language_code__in=language_codes)
         .delete())

        existing = set(self.for_team(team).values_list('language_code',
                                                       flat=True))
        to_create = [lc for lc in language_codes if lc not in existing]
        self.bulk_create([CollaborationLanguage(
            team=team, project=None, language_code=lc)
            for lc in to_create])
        Collaboration.objects.update_auto_created(team, language_codes)

    def languages_for_member(self, team_member):
        """Get preferred languages for a team member.

        This will limit the languages to those associated with the user (using
        the UserLanguage model), and those preferred by the team.

        If no CollaborationLanguage are set up for the team, then all user
        languages will be returned.

        :returns: list of language codes
        """
        user_langs = [l.language for l in team_member.user.get_languages()]
        team_langs = set(
            cl.language_code for cl in
            CollaborationLanguage.objects.for_team(team_member.team))
        if not team_langs:
            return user_langs
        else:
            return [code for code in user_langs if code in team_langs]

class CollaborationLanguage(models.Model):
    """Represent a language that a team wants subtitles for """

    team = models.ForeignKey(Team)
    project = models.ForeignKey(Project, null=True, blank=True)
    language_code = models.CharField(max_length=16)

    objects = CollaborationLanguageManager()

    class Meta:
        unique_together = ('team', 'language_code')

    def __unicode__(self):
        if self.project is None:
            return u"Preferred Language: %s for team %s" % (
                self.language_code, self.team)
        else:
            return u"Preferred Language: %s for team %s (project: %s)" % (
                self.language_code, self.team, self.project)

# TeamNotificationSettings
class TeamNotificationSettingManager(models.Manager):
    def notify_team(self, team_pk, event_name, **kwargs):
        """Notify the given team of a given event.

        Finds the matching notification settings for this team, instantiates
        the notifier class, and sends the appropriate notification.

        If the notification settings has an email target, sends an email.

        If the http settings are filled, then sends the request.

        This can be ran as a Celery task, as it requires no objects to be passed.

        """
        try:
            team = Team.objects.get(pk=team_pk)
        except Team.DoesNotExist:
            logger.error("A pk for a non-existent team was passed in.",
                         extra={"team_pk": team_pk, "event_name": event_name})
            return

        try:
            if team.partner:
                notification_settings = self.get(partner=team.partner)
            else:
                notification_settings = self.get(team=team)
        except TeamNotificationSetting.DoesNotExist:
            return

        notification_settings.notify(event_name, **kwargs)


class TeamNotificationSetting(models.Model):
    """Info on how a team should be notified of changes to its videos.

    For now, a team can be notified by having a http request sent with the
    payload as the notification information.  This cannot be hardcoded since
    teams might have different urls for each environment.

    Some teams have strict requirements on mapping video ids to their internal
    values, and also their own language codes. Therefore we need to configure
    a class that can do the correct mapping.

    TODO: allow email notifications

    """
    EVENT_VIDEO_NEW = "video-new"
    EVENT_VIDEO_EDITED = "video-edited"
    EVENT_LANGUAGE_NEW = "language-new"
    EVENT_LANGUAGE_EDITED = "language-edit"
    EVENT_LANGUAGE_DELETED = "language-deleted"
    EVENT_SUBTITLE_NEW = "subs-new"
    EVENT_SUBTITLE_APPROVED = "subs-approved"
    EVENT_SUBTITLE_REJECTED = "subs-rejected"
    EVENT_APPLICATION_NEW = 'application-new'

    team = models.OneToOneField(Team, related_name="notification_settings",
            null=True, blank=True)
    partner = models.OneToOneField('Partner',
        related_name="notification_settings",  null=True, blank=True)

    # the url to post the callback notifing partners of new video activity
    request_url = models.URLField(blank=True, null=True)
    basic_auth_username = models.CharField(max_length=255, blank=True, null=True)
    basic_auth_password = models.CharField(max_length=255, blank=True, null=True)

    # not being used, here to avoid extra migrations in the future
    email = models.EmailField(blank=True, null=True)

    # integers mapping to classes, see unisubs-integration/notificationsclasses.py
    notification_class = models.IntegerField(default=1,)

    objects = TeamNotificationSettingManager()

    def get_notification_class(self):
        try:
            from notificationclasses import NOTIFICATION_CLASS_MAP

            return NOTIFICATION_CLASS_MAP[self.notification_class]
        except ImportError:
            logger.exception("Apparently unisubs-integration is not installed")

    def notify(self, event_name,  **kwargs):
        """Resolve the notification class for this setting and fires notfications."""
        notification_class = self.get_notification_class()

        if not notification_class:
            logger.error("Could not find notification class %s" % self.notification_class)
            return

        notification = notification_class(self.team, self.partner,
                event_name,  **kwargs)

        if self.request_url:
            success, content = notification.send_http_request(
                self.request_url,
                self.basic_auth_username,
                self.basic_auth_password
            )
            return success, content
        # FIXME: spec and test this, for now just return
        return

    def __unicode__(self):
        if self.partner:
            return u'NotificationSettings for partner %s' % self.partner
        return u'NotificationSettings for team %s' % self.team


class BillingReport(models.Model):
    # use BillingRecords to signify completed work
    TYPE_BILLING_RECORD = 2
    # use approval tasks to signify completed work
    TYPE_APPROVAL = 3
    # Like TYPE_APPROVAL, but centered on the users who subtitle/review the
    # work
    TYPE_APPROVAL_FOR_USERS = 4
    TYPE_CHOICES = (
        (TYPE_BILLING_RECORD, 'Crowd sourced'),
        (TYPE_APPROVAL, 'Professional services'),
        (TYPE_APPROVAL_FOR_USERS, 'On-demand translators'),
    )
    teams = models.ManyToManyField(Team, related_name='billing_reports')
    start_date = models.DateField()
    end_date = models.DateField()
    csv_file = S3EnabledFileField(blank=True, null=True,
            upload_to='teams/billing/')
    processed = models.DateTimeField(blank=True, null=True)
    type = models.IntegerField(choices=TYPE_CHOICES,
                               default=TYPE_BILLING_RECORD)

    def __unicode__(self):
        if hasattr(self, 'id') and self.id is not None:
            team_count = self.teams.all().count()
        else:
            team_count = 0
        return "%s teams (%s - %s)" % (team_count,
                self.start_date.strftime('%Y-%m-%d'),
                self.end_date.strftime('%Y-%m-%d'))

    def _get_approved_tasks(self):
        return Task.objects.complete_approve().filter(
            approved=Task.APPROVED_IDS['Approved'],
            team__in=self.teams.all(),
            completed__range=(self.start_date, self.end_date))

    def _report_date(self, datetime):
        return datetime.strftime('%Y-%m-%d %H:%M:%S')

    def generate_rows_type_approval(self):
        header = (
            'Team',
            'Video Title',
            'Video ID',
            'Language',
            'Minutes',
            'Original',
            'Translation?',
            'Approver',
            'Date',
        )
        rows = [header]
        for approve_task in self._get_approved_tasks():
            video = approve_task.team_video.video
            version = approve_task.new_subtitle_version
            language = version.subtitle_language
            subtitle_task = (Task.objects.complete_subtitle_or_translate()
                             .filter(team_video=approve_task.team_video,
                                     language=approve_task.language)
                             .order_by('-completed'))[0]
            rows.append((
                approve_task.team.name,
                video.title_display(),
                video.video_id,
                approve_task.language,
                get_minutes_for_version(version, False),
                language.is_primary_audio_language(),
                subtitle_task.type==Task.TYPE_IDS['Translate'],
                unicode(approve_task.assignee),
                self._report_date(approve_task.completed),
            ))

        return rows

    def generate_rows_type_approval_for_users(self):
        header = (
            'User',
            'Task Type',
            'Team',
            'Video Title',
            'Video ID',
            'Language',
            'Minutes',
            'Original',
            'Approver',
            'Note',
            'Date',
            'Pay Rate',
        )
        data_rows = []
        for approve_task in self._get_approved_tasks():
            video = approve_task.team_video.video
            version = approve_task.new_subtitle_version
            language = version.subtitle_language

            all_tasks = []
            try:
                all_tasks.append((Task.objects.complete_subtitle_or_translate()
                                  .filter(team_video=approve_task.team_video,
                                          language=approve_task.language)
                                  .order_by('-completed'))[0])
            except IndexError:
                # no subtitling task, probably the review task was manually
                # created.
                pass
            try:
                all_tasks.append((Task.objects.complete_review()
                                  .filter(team_video=approve_task.team_video,
                                          language=approve_task.language)
                                  .order_by('-completed'))[0])
            except IndexError:
                # review not enabled
                pass

            for task in all_tasks:
                data_rows.append((
                    unicode(task.assignee),
                    task.get_type_display(),
                    approve_task.team.name,
                    video.title_display(),
                    video.video_id,
                    language.language_code,
                    get_minutes_for_version(version, False),
                    language.is_primary_audio_language(),
                    unicode(approve_task.assignee),
                    unicode(task.body),
                    self._report_date(task.completed),
                    task.assignee.pay_rate_code,
                ))

        data_rows.sort(key=lambda row: row[0])
        return [header] + data_rows

    def generate_rows_type_billing_record(self):
        rows = []
        for i,team in enumerate(self.teams.all()):
            rows = rows + BillingRecord.objects.csv_report_for_team(team,
                self.start_date, self.end_date, add_header=i == 0)
        return rows

    def generate_rows(self):
        if self.type == BillingReport.TYPE_BILLING_RECORD:
            rows = self.generate_rows_type_billing_record()
        elif self.type == BillingReport.TYPE_APPROVAL:
            rows = self.generate_rows_type_approval()
        elif self.type == BillingReport.TYPE_APPROVAL_FOR_USERS:
            rows = self.generate_rows_type_approval_for_users()
        else:
            raise ValueError("Unknown type: %s" % self.type)
        return rows

    def convert_unicode_to_utf8(self, rows):
        def _convert(value):
            if isinstance(value, unicode):
                return value.encode("utf-8")
            else:
                return value
        return [tuple(_convert(v) for v in row) for row in rows]

    def process(self):
        """
        Generate the correct rows (including headers), saves it to a tempo file,
        then set's that file to the csv_file property, which if , using the S3
        storage will take care of exporting it to s3.
        """
        try:
            rows = self.generate_rows()
        except StandardError:
            logger.error("Error generating billing report: (id: %s)", self.id)
            self.csv_file = None
        else:
            self.csv_file = self.make_csv_file(rows)
        self.processed = datetime.datetime.utcnow()
        self.save()

    def make_csv_file(self, rows):
        rows = self.convert_unicode_to_utf8(rows)
        fn = '/tmp/bill-%s-teams-%s-%s-%s-%s.csv' % (
            self.teams.all().count(),
            self.start_str, self.end_str,
            self.get_type_display(), self.pk)
        with open(fn, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        return File(open(fn, 'r'))

    @property
    def start_str(self):
        return self.start_date.strftime("%Y%m%d")

    @property
    def end_str(self):
        return self.end_date.strftime("%Y%m%d")

class BillingReportGenerator(object):
    def __init__(self, all_records, add_header=True):
        if add_header:
            self.rows = [self.header()]
        else:
            self.rows = []

        all_records = list(all_records)

        self.make_language_number_map(all_records)
        self.make_languages_without_records(all_records)

        for video, records in groupby(all_records, lambda r: r.video):
            records = list(records)
            for lang in self.languages_without_records.get(video.id, []):
                self.rows.append(
                    self.make_row_for_lang_without_record(video, lang))
            for r in records:
                self.rows.append(self.make_row(video, r))

    def header(self):
        return [
            'Video Title',
            'Video ID',
            'Language',
            'Minutes',
            'Original',
            'Language number',
            'Team',
            'Created',
            'Source',
            'User',
        ]

    def make_row(self, video, record):
        return [
            video.title_display(),
            video.video_id,
            record.new_subtitle_language.language_code,
            record.minutes,
            record.is_original,
            self.language_number_map[record.id],
            record.team.slug,
            record.created.strftime('%Y-%m-%d %H:%M:%S'),
            record.source,
            record.user.username,
        ]

    def make_language_number_map(self, records):
        self.language_number_map = {}
        videos = set(r.video for r in records)
        video_counts = dict((v.id, 0) for v in videos)
        qs = (BillingRecord.objects
              .filter(video__in=videos)
              .order_by('created'))
        for record in qs:
            vid = record.video.id
            video_counts[vid] += 1
            self.language_number_map[record.id] = video_counts[vid]

    def make_languages_without_records(self, records):
        self.languages_without_records = {}
        videos = [r.video for r in records]
        language_ids = [r.new_subtitle_language_id for r in records]
        no_billing_record_where = """\
NOT EXISTS (
    SELECT 1
    FROM teams_billingrecord br
    WHERE br.new_subtitle_language_id = subtitles_subtitlelanguage.id
)"""
        qs = (NewSubtitleLanguage.objects
              .filter(video__in=videos, subtitles_complete=True)
              .exclude(id__in=language_ids).
              extra(where=[no_billing_record_where]))
        for lang in qs:
            vid = lang.video_id
            if vid not in self.languages_without_records:
                self.languages_without_records[vid] = [lang]
            else:
                self.languages_without_records[vid].append(lang)

    def make_row_for_lang_without_record(self, video, language):
        return [
            video.title_display(),
            video.video_id,
            language.language_code,
            0,
            language.is_primary_audio_language(),
            0,
            'unknown',
            language.created.strftime('%Y-%m-%d %H:%M:%S'),
            'unknown',
            'unknown',
        ]

class BillingRecordManager(models.Manager):

    def data_for_team(self, team, start, end):
        return self.filter(team=team, created__gte=start, created__lte=end)

    def csv_report_for_team(self, team, start, end, add_header=True):
        all_records = self.data_for_team(team, start, end)
        generator = BillingReportGenerator(all_records, add_header)
        return generator.rows

    def insert_records_for_translations(self, billing_record):
        """
        IF you've translated from an incomplete language, and later on that
        language is completed, we must check if any translations are now
        complete and therefore should have billing records with them
        """
        translations = billing_record.new_subtitle_language.get_dependent_subtitle_languages()
        inserted = []
        for translation in translations:
            version = translation.get_tip(public=False)
            if version:
               inserted.append(self.insert_record(version))
        return filter(bool, inserted)

    def insert_record(self, version):
        """
        Figures out if this version qualifies for a billing record, and
        if so creates one. This should be self contained, e.g. safe to call
        for any version. No records should be created if not needed, and it
        won't create multiples.

        If this language has translations it will check if any of those are now
        eligible for BillingRecords and create one accordingly.
        """
        from teams.models import BillingRecord

        celery_logger.debug('insert billing record')

        language = version.subtitle_language
        video = language.video
        tv = video.get_team_video()

        if not tv:
            celery_logger.debug('not a team video')
            return

        if not language.is_complete_and_synced(public=False):
            celery_logger.debug('language not complete')
            return


        try:
            # we already have a record
            previous_record = BillingRecord.objects.get(video=video,
                            new_subtitle_language=language)
            # make sure we update it
            celery_logger.debug('a billing record for this language exists')
            previous_record.is_original = \
                video.primary_audio_language_code == language.language_code
            previous_record.save()
            return
        except BillingRecord.DoesNotExist:
            pass


        if NewSubtitleVersion.objects.filter(
                subtitle_language=language,
                created__lt=BILLING_CUTOFF).exclude(
                pk=version.pk).exists():
            celery_logger.debug('an older version exists')
            return

        is_original = language.is_primary_audio_language()
        source = version.origin
        team = tv.team

        new_record = BillingRecord.objects.create(
            video=video,
            new_subtitle_version=version,
            new_subtitle_language=language,
            is_original=is_original, team=team,
            created=version.created,
            source=source,
            user=version.author)
        from_translations = self.insert_records_for_translations(new_record)
        return new_record, from_translations


def get_minutes_for_version(version, round_up_to_integer):
    """
    Return the number of minutes the subtitles specified in version
    """
    subs = version.get_subtitles()

    if len(subs) == 0:
        return 0

    for sub in subs:
        if sub.start_time is not None:
            start_time = sub.start_time
            break
        # we shouldn't have an end time set without a start time, but handle
        # it just in case
        if sub.end_time is not None:
            start_time = sub.end_time
            break
    else:
        return 0

    for sub in reversed(subs):
        if sub.end_time is not None:
            end_time = sub.end_time
            break
        # we shouldn't have an end time not set, but check for that just in
        # case
        if sub.start_time is not None:
            end_time = sub.start_time
            break
    else:
        return 0

    duration_seconds =  (end_time - start_time) / 1000.0
    minutes = duration_seconds/60.0
    if round_up_to_integer:
        minutes = int(ceil(minutes))
    return minutes

class BillingRecord(models.Model):
    video = models.ForeignKey(Video)

    subtitle_version = models.ForeignKey(SubtitleVersion, null=True,
            blank=True)
    new_subtitle_version = models.ForeignKey(NewSubtitleVersion, null=True,
            blank=True)

    subtitle_language = models.ForeignKey(SubtitleLanguage, null=True,
            blank=True)
    new_subtitle_language = models.ForeignKey(NewSubtitleLanguage, null=True,
            blank=True)

    minutes = models.FloatField(blank=True, null=True)
    is_original = models.BooleanField()
    team = models.ForeignKey(Team)
    created = models.DateTimeField()
    source = models.CharField(max_length=255)
    user = models.ForeignKey(User)

    objects = BillingRecordManager()

    class Meta:
        unique_together = ('video', 'new_subtitle_language')


    def __unicode__(self):
        return "%s - %s" % (self.video.video_id,
                self.new_subtitle_language.language_code)

    def save(self, *args, **kwargs):
        if not self.minutes and self.minutes != 0.0:
            self.minutes = self.get_minutes()

        assert self.minutes is not None

        return super(BillingRecord, self).save(*args, **kwargs)

    def get_minutes(self):
        return get_minutes_for_version(self.new_subtitle_version, True)

class Partner(models.Model):
    name = models.CharField(_(u'name'), max_length=250, unique=True)
    slug = models.SlugField(_(u'slug'), unique=True)
    can_request_paid_captions = models.BooleanField(default=False)

    # The `admins` field specifies users who can do just about anything within
    # the partner realm.
    admins = models.ManyToManyField('auth.CustomUser',
            related_name='managed_partners', blank=True, null=True)

    def __unicode__(self):
        return self.name

    def is_admin(self, user):
        return user in self.admins.all()

class CollaborationManager(models.Manager):
    def for_dashboard(self, team_member, can_join_limit=None):
        """Get collaborations to show for a user's dashboard.

        Returns a dict with the following keys:

            joined - List of (Collaboration, Collaborator) models for
            collaborations the member has joined
            can_join - Collaborations the member can join

        If can_join_limit is given, we will only fetch that many
        Collaborations to join for each collaboration state (only N
        collaborations to subtitle, N to review, etc).
        """
        # calculate which collaborations the user is currently working on.
        # Since we're going to use this for the other querysets, it's more
        # efficeient to evaluate the querysets immediately.
        collaborator_qs = (Collaborator.objects
                           .filter(user=team_member.user,
                                   complete=False,
                                   collaboration__team=team_member.team)
                           .select_related('collaboration'))
        joined = [(collaborator.collaboration, collaborator)
                      for collaborator in collaborator_qs]

        return {
            'joined': joined,
            'can_join': self._can_join(team_member, joined, can_join_limit)
        }

    def _can_join(self, team_member, joined, limit):
        return (list(self._can_join_not_started(team_member, limit)) +
                list(self._can_join_started(team_member, joined, limit)))

    def _can_join_not_started(self, team_member, limit):
        projects = list(Project.objects.all_projects_for_team(
            team_member.team))
        return self.filter(
            state=Collaboration.NEEDS_SUBTITLER,
            project__in=projects,
            language_code__in=team_member.user.get_language_codes())[:limit]

    def _states_member_can_join(self, team_member):
        workflow = team_member.team.workflow
        if not workflow.only_1_subtitler:
            yield Collaboration.BEING_SUBTITLED
        yield Collaboration.NEEDS_REVIEWER
        if not workflow.only_1_reviewer:
            yield Collaboration.BEING_REVIEWED
        if workflow.member_can_approve(team_member):
            yield Collaboration.NEEDS_APPROVER
            if not workflow.only_1_reviewer:
                yield Collaboration.BEING_APPROVED

    def _can_join_started(self, team_member, joined, limit):
        rv = []
        # calculate which Collaboration states the user can join
        states = []
        workflow = team_member.team.workflow
        if not workflow.only_1_subtitler:
            states.append(Collaboration.BEING_SUBTITLED)
        states.append(Collaboration.NEEDS_REVIEWER)
        if not workflow.only_1_reviewer:
            states.append(Collaboration.BEING_REVIEWED)
        if workflow.member_can_approve(team_member):
            states.append(Collaboration.NEEDS_APPROVER)
            if not workflow.only_1_reviewer:
                states.append(Collaboration.BEING_APPROVED)
        # query Collaborations for each state
        user_languages = team_member.user.get_language_codes()
        join_qs = (self.
                   filter(team=team_member.team,
                          language_code__in=user_languages)
                   .exclude(id__in=[collab.id for (collab, _) in joined]))
        for state in states:
            if limit is None:
                rv.extend(join_qs.filter(state=state))
            else:
                rv.extend(join_qs.filter(state=state)[:limit])
        return rv

    def update_auto_created(self, team, language_codes):
        """Update the auto-created collaborations.

        This method ensures that we have the correct auto-created
        collaborations after the team's CollaborationLanguages change.

        For each team video/language code combination, we will ensure that
        there is a collaboration for it.

        Previously created collaborations for other languages will be deleted.
        """
        cursor = connection.cursor()
        self._delete_auto_created(cursor, team, language_codes)
        self._insert_auto_created(cursor, team, language_codes)
        transaction.commit_unless_managed()

    def _delete_auto_created(self, cursor, team, language_codes):
        # This is a fairly crazy query, mostly because mysql doesn't let you
        # use the table you're deleting from in the a subquery, unless you
        # alias it.  See stack overflow question #4429319
        sql = ("DELETE FROM teams_collaboration "
               "WHERE id IN (SELECT id FROM ("
               "SELECT collaboration.id "
               "FROM teams_collaboration collaboration "
               "LEFT JOIN teams_teamvideo tv "
               "ON collaboration.team_video_id=tv.id "
               "LEFT JOIN teams_collaborator collaborator "
               "ON collaborator.collaboration_id=collaboration.id "
               "WHERE tv.team_id=%s AND "
               "collaboration.language_code NOT IN ({0}) AND "
               "collaborator.id IS NULL) as foo)").format(
                   ", ".join("%s" for c in language_codes))
        cursor.execute(sql, (team.id,) + tuple(language_codes))

    def _insert_auto_created(self, cursor, team, language_codes):
        sql = ("INSERT INTO teams_collaboration(team_video_id, "
               "project_id, language_code, state, last_joined, team_id) "
               "SELECT tv.id, tv.project_id, %s, %s, NULL, NULL "
               " FROM teams_teamvideo tv "
               " LEFT JOIN teams_collaboration c "
               " ON c.team_video_id=tv.id AND c.language_code=%s "
               " WHERE tv.team_id=%s AND c.id IS NULL")
        for language_code in language_codes:
            values = (language_code, Collaboration.NEEDS_SUBTITLER,
                      language_code, team.id)
            cursor.execute(sql, values)

class Collaboration(models.Model):
    """Tracks subtitling work for a video language."""

    NEEDS_SUBTITLER = 's'
    BEING_SUBTITLED = 'S'
    NEEDS_REVIEWER = 'r'
    BEING_REVIEWED = 'R'
    NEEDS_APPROVER = 'a'
    BEING_APPROVED = 'A'
    COMPLETE = 'C'

    STATE_CHOICES = [
        (NEEDS_SUBTITLER, 'needs subtitler'),
        (BEING_SUBTITLED, 'being subtitled'),
        (NEEDS_REVIEWER, 'needs reviewer'),
        (BEING_REVIEWED, 'being reviewed'),
        (NEEDS_APPROVER, 'needs approver'),
        (BEING_APPROVED, 'being approved'),
        (COMPLETE, 'complete'),
    ]

    # video/language being worked on
    team_video = models.ForeignKey(TeamVideo)
    language_code = models.CharField(max_length=16, choices=ALL_LANGUAGES)
    state = models.CharField(max_length=1, choices=STATE_CHOICES,
                             default=NEEDS_SUBTITLER)
    last_joined = models.DateTimeField(null=True, blank=True, default=None,
                                       db_index=True)
    # team doing the work.  Note that the video can be owned by a different
    # team in the case of shared projects.  Use owning_team() to get the team
    # that owns the video.
    team = models.ForeignKey(Team, null=True)
    # project from our team video.  We denormalize the data to because we want
    # to index it.
    project = models.ForeignKey(Project)

    objects = CollaborationManager()

    class Meta:
        unique_together = ('team_video', 'language_code')

    def __init__(self, *args, **kwargs):
        if not args and 'team_video' in kwargs:
            kwargs['project_id'] = kwargs['team_video'].project_id
        return models.Model.__init__(self, *args, **kwargs)

    def __unicode__(self):
        return u'%s collaboration for %s' % (self.get_language_code_display(),
                                             self.team_video)

    def owning_team(self):
        return self.team_video.team

    def can_join(self, member):
        """Check if a team member can join this collaboration

        :param member: TeamMember object.
        :returns: True if the user can join this collaboration.
        """

        if self.team is not None:
            if member.team != self.team:
                return False
        else:
            member_teams = set([m.team_id for m in
                                member.user.team_members.all()])
            project_teams = set([self.team_video.project.team_id])
            project_teams.update(t.id for t in
                                 self.team_video.project.shared_teams.all())
            if not member_teams.intersection(project_teams):
                return False

        if self.state in (Collaboration.NEEDS_SUBTITLER,
                          Collaboration.NEEDS_REVIEWER):
            return True
        elif self.state == Collaboration.BEING_SUBTITLED:
            return not self.team.workflow.only_1_subtitler
        elif self.state == Collaboration.BEING_REVIEWED:
            return not self.team.workflow.only_1_reviewer
        elif self.state == Collaboration.NEEDS_APPROVER:
            return self.team.workflow.member_can_approve(member)
        elif self.state == Collaboration.BEING_APPROVED:
            return (self.team.workflow.member_can_approve(member) and
                    not self.team.workflow.only_1_approver)
        elif self.state == Collaboration.COMPLETE:
            return False
        else:
            raise ValueError("Unknown state: %s" % self.state)

    def _join_role(self):
        """Get the role that a new user should join as."""
        if self.state in (Collaboration.NEEDS_SUBTITLER,
                          Collaboration.BEING_SUBTITLED):
            return Collaborator.SUBTITLER
        elif self.state in (Collaboration.NEEDS_REVIEWER,
                          Collaboration.BEING_REVIEWED):
            return Collaborator.REVIEWER
        elif self.state in (Collaboration.NEEDS_APPROVER,
                          Collaboration.BEING_APPROVED):
            return Collaborator.APPROVER
        else:
            raise ValueError("Invalid state in _join_role: %s" % self.state)


    def join(self, team_member):
        """Add a new collaborator to this collaboration.

        This method creates the Collaborator and potentially updates our
        state.

        :returns: Collaborator object.
        """

        if not self.can_join(team_member):
            raise ValueError("%s can't join" % (team_member,))

        role = self._join_role()
        collaborator = Collaborator.objects.create(collaboration=self,
                                                   user=team_member.user,
                                                   role=role)
        # Create a lookup table that maps (old_state, role) -> new_state
        state_change_map = {
            (Collaboration.NEEDS_SUBTITLER,
             Collaborator.SUBTITLER): Collaboration.BEING_SUBTITLED,
            (Collaboration.NEEDS_REVIEWER,
             Collaborator.REVIEWER): Collaboration.BEING_REVIEWED,
            (Collaboration.NEEDS_APPROVER,
             Collaborator.APPROVER): Collaboration.BEING_APPROVED,
        }
        needs_save = False
        new_state = state_change_map.get((self.state, role))
        if new_state is not None:
            self.state = new_state
            needs_save = True
        if self.team is None:
            self.team = team_member.team
            needs_save = True
        if needs_save:
            self.save()
        return collaborator

    def mark_endorsed(self, team_member):
        """Mark this collaboration endorsed by a user."""
        collaborator = self.collaborators.get(user=team_member.user)
        collaborator.mark_endorsed()
        # Check if the endorsement changes our state
        new_state = None
        if self.state == Collaboration.BEING_SUBTITLED:
            if collaborator.role == Collaborator.SUBTITLER:
                if self.team.workflow.needs_review():
                    new_state = Collaboration.NEEDS_REVIEWER
                else:
                    new_state = Collaboration.COMPLETE
        elif self.state == Collaboration.BEING_REVIEWED:
            if collaborator.role == Collaborator.REVIEWER:
                if self.team.workflow.needs_approval():
                    new_state = Collaboration.NEEDS_APPROVER
                else:
                    new_state = Collaboration.COMPLETE
        elif self.state == Collaboration.BEING_APPROVED:
            if collaborator.role == Collaborator.APPROVER:
                new_state = Collaboration.COMPLETE
        if new_state is not None:
            self.state = new_state
            self.save()
            if new_state == Collaboration.COMPLETE:
                self.collaborators.update(complete=True)

class Collaborator(models.Model):
    """User who is part of a collaboration."""

    SUBTITLER = "S"
    REVIEWER = "R"
    APPROVER = "A"
    ROLE_CHOICES = [
        (SUBTITLER, _('Subtitler')),
        (REVIEWER, _('Reviewer')),
        (APPROVER, _('Approver')),
    ]

    collaboration = models.ForeignKey(Collaboration,
                                      related_name='collaborators')
    user = models.ForeignKey(User)
    role = models.CharField(max_length=1, choices=ROLE_CHOICES)
    start_date = models.DateTimeField()
    endorsement_date = models.DateTimeField(blank=True, null=True)
    # True when our collaboration has state COMPLETE.  We denormalize this
    # because we want create an index from it
    complete = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        if not args and 'start_date' not in kwargs:
            kwargs['start_date'] = Collaborator.now()
        return models.Model.__init__(self, *args, **kwargs)

    # Make now as a plain function so we can patch it in the unittests
    @staticmethod
    def now():
        return datetime.datetime.now()

    @property
    def endorsed(self):
        return self.endorsement_date is not None

    def mark_endorsed(self):
        self.endorsement_date = Collaborator.now()
        self.save()

class CollaborationHistory(models.Model):
    """Tracks changes to a collaboration."""

    ACTION_USER_JOINED = "J"
    ACTION_USER_ENDORSED = "E"
    ACTION_USER_UNENDORSED = "U"
    ACTION_USER_LEFT = "L"
    ACTION_USER_REMOVED = "R"
    ACTIONS = [
        (ACTION_USER_JOINED, _('User joined collaboration')),
        (ACTION_USER_ENDORSED, _('User endorsed collaboration')),
        (ACTION_USER_UNENDORSED, _('User unendorsed collaboration')),
        (ACTION_USER_LEFT, _('User left collaboration')),
        (ACTION_USER_REMOVED, _('User was removed from collaboration')),
    ]

    collaboration = models.ForeignKey(Collaboration)
    collaborator = models.ForeignKey(Collaborator, related_name='+')
    collaborator2 = models.ForeignKey(Collaborator, blank=True, null=True,
                                      related_name='+')
    action = models.CharField(max_length=1, choices=ACTIONS)
    date = models.DateTimeField()

# we know that models.py is always loaded, import signalhandlers to ensure it
# gets loaded as well
import teams.signalhandlers
