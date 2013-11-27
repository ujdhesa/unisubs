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

"""teams.workflow -- Code to handle team workflows

Team workflows control how subtitling work gets performed on videos.  They
handle a few things:

    * Access control for unpublished versions (both view/editing)
    * Tracking work that needs to be done
    * Review/approval
    * Communication for subtitlers/reviewers/approvers

Currently we have 3 systems for workflows:
    * Tasks (the old system)
    * Collaboration (the new system)
    * None (subtitling works as if the videos didn't belong to a team)

"""


import datetime
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from auth.models import CustomUser as User
from comments.models import Comment
from messages import tasks as notifier
from videos.tasks import upload_subtitles_to_original_service
from teams import tasks
from teams.permissions_const import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_CONTRIBUTOR
)
from subtitles.models import SubtitleVersion, SubtitleLanguage
from videos.models import SubtitleVersion as OldSubtitleVersion
from videos.models import VideoUrl

VALID_LANGUAGE_CODES = set(code for code, label in settings.ALL_LANGUAGES)

WORKFLOW_DEFAULT = "D"
WORKFLOW_TASKS = "T"
WORKFLOW_COLLABORATION = "C"

WORKFLOW_CHOICES = (
    (WORKFLOW_DEFAULT, "None"),
    (WORKFLOW_TASKS, "Tasks"),
    (WORKFLOW_COLLABORATION, "Collaboration"),
)

class TaskWorkflow(models.Model):
    """Workflow for teams that use tasks."""

    REVIEW_CHOICES = (
        (00, "Don't require review"),
        (10, 'Peer must review'),
        (20, 'Manager must review'),
        (30, 'Admin must review'),
    )
    REVIEW_NAMES = dict(REVIEW_CHOICES)
    REVIEW_IDS = dict([choice[::-1] for choice in REVIEW_CHOICES])

    APPROVE_CHOICES = (
        (00, "Don't require approval"),
        (10, 'Manager must approve'),
        (20, 'Admin must approve'),
    )
    APPROVE_NAMES = dict(APPROVE_CHOICES)
    APPROVE_IDS = dict([choice[::-1] for choice in APPROVE_CHOICES])

    team = models.ForeignKey('Team', unique=True)

    autocreate_subtitle = models.BooleanField(default=False)
    autocreate_translate = models.BooleanField(default=False)

    review_allowed = models.PositiveIntegerField(
            choices=REVIEW_CHOICES, verbose_name='reviewers', default=0)

    approve_allowed = models.PositiveIntegerField(
            choices=APPROVE_CHOICES, verbose_name='approvers', default=0)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        # this class used to just be called "Workflow", but was changed when
        # we added the collaboration workflow code.  We still use the old
        # table name though.
        db_table = 'teams_workflow'

    @classmethod
    def get_for_team_video(cls, team_video):
        '''Return the Workflow for the given team_video.

        NOTE: This function caches the workflow for performance reasons.  If the
        workflow changes within the space of a single request that
        _cached_workflow should be cleared.

        '''
        if not hasattr(team_video, '_cached_workflow'):
            team_video._cached_workflow = team_video.team.get_workflow()
        return team_video._cached_workflow

    def __unicode__(self):
        return u'Workflow for %s' % (self.team)

    # Convenience functions for checking if a step of the workflow is enabled.
    @property
    def review_enabled(self):
        """Return whether any form of review is enabled for this workflow."""
        return True if self.review_allowed else False

    @property
    def approve_enabled(self):
        """Return whether any form of approval is enabled for this workflow."""
        return True if self.approve_allowed else False

    @property
    def requires_review_or_approval(self):
        """Return whether a given workflow requires review or approval."""
        return self.approve_enabled or self.review_enabled

    @property
    def requires_tasks(self):
        """Return whether a given workflow requires the use of tasks."""
        return (self.requires_review_or_approval or self.autocreate_subtitle
                or self.autocreate_translate)

class TaskManager(models.Manager):
    def not_deleted(self):
        """Return a QS of tasks that are not deleted."""
        return self.get_query_set().filter(deleted=False)


    def incomplete(self):
        """Return a QS of tasks that are not deleted or completed."""
        return self.not_deleted().filter(completed=None)

    def complete(self):
        """Return a QS of tasks that are not deleted, but are completed."""
        return self.not_deleted().filter(completed__isnull=False)

    def _type(self, types, completed=None, approved=None):
        """Return a QS of tasks that are not deleted and are one of the given types.

        types should be a list of strings matching a label in Task.TYPE_CHOICES.

        completed should be one of:

        * True (only show completed tasks)
        * False (only show incomplete tasks)
        * None (don't filter on completion status)

        approved should be either None or a string matching a label in
        Task.APPROVED_CHOICES.

        """
        type_ids = [Task.TYPE_IDS[type] for type in types]
        qs = self.not_deleted().filter(type__in=type_ids)

        if completed == False:
            qs = qs.filter(completed=None)
        elif completed == True:
            qs = qs.filter(completed__isnull=False)

        if approved:
            qs = qs.filter(approved=Task.APPROVED_IDS[approved])

        return qs


    def incomplete_subtitle(self):
        """Return a QS of subtitle tasks that are not deleted or completed."""
        return self._type(['Subtitle'], False)

    def incomplete_translate(self):
        """Return a QS of translate tasks that are not deleted or completed."""
        return self._type(['Translate'], False)

    def incomplete_review(self):
        """Return a QS of review tasks that are not deleted or completed."""
        return self._type(['Review'], False)

    def incomplete_approve(self):
        """Return a QS of approve tasks that are not deleted or completed."""
        return self._type(['Approve'], False)

    def incomplete_subtitle_or_translate(self):
        """Return a QS of subtitle or translate tasks that are not deleted or completed."""
        return self._type(['Subtitle', 'Translate'], False)

    def incomplete_review_or_approve(self):
        """Return a QS of review or approve tasks that are not deleted or completed."""
        return self._type(['Review', 'Approve'], False)


    def complete_subtitle(self):
        """Return a QS of subtitle tasks that are not deleted, but are completed."""
        return self._type(['Subtitle'], True)

    def complete_translate(self):
        """Return a QS of translate tasks that are not deleted, but are completed."""
        return self._type(['Translate'], True)

    def complete_review(self, approved=None):
        """Return a QS of review tasks that are not deleted, but are completed.

        If approved is given the tasks are further filtered on their .approved
        attribute.  It must be a string matching one of the labels in
        Task.APPROVED_CHOICES, like 'Rejected'.

        """
        return self._type(['Review'], True, approved)

    def complete_approve(self, approved=None):
        """Return a QS of approve tasks that are not deleted, but are completed.

        If approved is given the tasks are further filtered on their .approved
        attribute.  It must be a string matching one of the labels in
        Task.APPROVED_CHOICES, like 'Rejected'.

        """
        return self._type(['Approve'], True, approved)

    def complete_subtitle_or_translate(self):
        """Return a QS of subtitle or translate tasks that are not deleted, but are completed."""
        return self._type(['Subtitle', 'Translate'], True)

    def complete_review_or_approve(self, approved=None):
        """Return a QS of review or approve tasks that are not deleted, but are completed.

        If approved is given the tasks are further filtered on their .approved
        attribute.  It must be a string matching one of the labels in
        Task.APPROVED_CHOICES, like 'Rejected'.

        """
        return self._type(['Review', 'Approve'], True, approved)


    def all_subtitle(self):
        """Return a QS of subtitle tasks that are not deleted."""
        return self._type(['Subtitle'])

    def all_translate(self):
        """Return a QS of translate tasks that are not deleted."""
        return self._type(['Translate'])

    def all_review(self):
        """Return a QS of review tasks that are not deleted."""
        return self._type(['Review'])

    def all_approve(self):
        """Return a QS of tasks that are not deleted."""
        return self._type(['Approve'])

    def all_subtitle_or_translate(self):
        """Return a QS of subtitle or translate tasks that are not deleted."""
        return self._type(['Subtitle', 'Translate'])

    def all_review_or_approve(self):
        """Return a QS of review or approve tasks that are not deleted."""
        return self._type(['Review', 'Approve'])

class Task(models.Model):
    TYPE_CHOICES = (
        (10, 'Subtitle'),
        (20, 'Translate'),
        (30, 'Review'),
        (40, 'Approve'),
    )
    TYPE_NAMES = dict(TYPE_CHOICES)
    TYPE_IDS = dict([choice[::-1] for choice in TYPE_CHOICES])

    APPROVED_CHOICES = (
        (10, 'In Progress'),
        (20, 'Approved'),
        (30, 'Rejected'),
    )
    APPROVED_NAMES = dict(APPROVED_CHOICES)
    APPROVED_IDS = dict([choice[::-1] for choice in APPROVED_CHOICES])
    APPROVED_FINISHED_IDS = (20, 30)

    type = models.PositiveIntegerField(choices=TYPE_CHOICES)

    team = models.ForeignKey('Team')
    team_video = models.ForeignKey('TeamVideo')
    language = models.CharField(max_length=16, choices=settings.ALL_LANGUAGES,
                                blank=True, db_index=True)
    assignee = models.ForeignKey(User, blank=True, null=True)
    subtitle_version = models.ForeignKey(OldSubtitleVersion, blank=True,
                                         null=True)
    new_subtitle_version = models.ForeignKey(SubtitleVersion,
                                             blank=True, null=True)

    # The original source version being reviewed or approved.
    #
    # For example, if person A creates two versions while working on a subtitle
    # task:
    #
    #  v1  v2
    # --o---o
    #   s   s
    #
    # and then the reviewer and approver make some edits
    #
    #  v1  v2  v3  v4  v5
    # --o---o---o---o---o
    #   s   s   r   r   a
    #       *
    #
    # the review_base_version will be v2.  Once approved, if an edit is made it
    # needs to be approved as well, and the same thing happens:
    #
    #  v1  v2  v3  v4  v5  v6  v7
    # --o---o---o---o---o---o---o
    #   s   s   r   r   a   e   a
    #                       *
    #
    # This is used when rejecting versions, and may be used elsewhere in the
    # future as well.
    review_base_version = models.ForeignKey(OldSubtitleVersion, blank=True,
                                            null=True,
                                            related_name='tasks_based_on')
    new_review_base_version = models.ForeignKey(SubtitleVersion, blank=True,
                                                null=True,
                                                related_name='tasks_based_on_new')

    deleted = models.BooleanField(default=False)

    # TODO: Remove this field.
    public = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)
    completed = models.DateTimeField(blank=True, null=True)
    expiration_date = models.DateTimeField(blank=True, null=True)

    # Arbitrary priority for tasks. Some teams might calculate this
    # on complex criteria and expect us to be able to sort tasks on it.
    # Higher numbers mean higher priority
    priority = models.PositiveIntegerField(blank=True, default=0, db_index=True)
    # Review and Approval -specific fields
    approved = models.PositiveIntegerField(choices=APPROVED_CHOICES,
                                           null=True, blank=True)
    body = models.TextField(blank=True, default="")

    objects = TaskManager()

    def __unicode__(self):
        return u'Task %s (%s) for %s' % (self.id or "unsaved",
                                         self.get_type_display(),
                                         self.team_video)

    @staticmethod
    def now():
        """datetime.datetime.now as a method

        This lets us patch it in the unittests.
        """
        return datetime.datetime.now()

    @property
    def workflow(self):
        '''Return the most specific workflow for this task's TeamVideo.'''
        return TaskWorkflow.get_for_team_video(self.team_video)

    @staticmethod
    def add_cached_video_urls(tasks):
        """Add the cached_video_url attribute to a list of atkss

        cached_video_url is the URL as a string for the video.
        """
        team_video_pks = [t.team_video_id for t in tasks]
        video_urls = (VideoUrl.objects
                      .filter(video__teamvideo__id__in=team_video_pks)
                      .filter(primary=True))
        video_url_map = dict((vu.video_id, vu.effective_url)
                             for vu in video_urls)
        for t in tasks:
            t.cached_video_url = video_url_map.get(t.team_video.video_id)


    def _add_comment(self):
        """Add a comment on the SubtitleLanguage for this task with the body as content."""
        if self.body.strip():
            lang_ct = ContentType.objects.get_for_model(SubtitleLanguage)
            comment = Comment(
                content=self.body,
                object_pk=self.new_subtitle_version.subtitle_language.pk,
                content_type=lang_ct,
                submit_date=self.completed,
                user=self.assignee,
            )
            comment.save()
            notifier.send_video_comment_notification.delay(
                comment.pk, version_pk=self.new_subtitle_version.pk)

    def future(self):
        """Return whether this task expires in the future."""
        return self.expiration_date > self.now()

    # Functions related to task completion.
    def _send_back(self, sends_notification=True):
        """Handle "rejection" of this task.

        This will:

        * Create a new task with the appropriate type (translate or subtitle).
        * Try to reassign it to the previous assignee, leaving it unassigned
          if that's not possible.
        * Send a notification unless sends_notification is given as False.

        NOTE: This function does not modify the *current* task in any way.

        """
        # when sending back, instead of always sending back
        # to the first step (translate/subtitle) go to the
        # step before this one:
        # Translate/Subtitle -> Review -> Approve
        # also, you can just send back approve and review tasks.
        if self.type == Task.TYPE_IDS['Approve'] and self.workflow.review_enabled:
            type = Task.TYPE_IDS['Review']
        else:
            is_primary = (self.new_subtitle_version
                              .subtitle_language
                              .is_primary_audio_language())
            if is_primary:
                type = Task.TYPE_IDS['Subtitle']
            else:
                type = Task.TYPE_IDS['Translate']

        # let's guess which assignee should we use
        # by finding the last user that did this task type
        previous_task = Task.objects.complete().filter(
            team_video=self.team_video, language=self.language, team=self.team, type=type
        ).order_by('-completed')[:1]

        if previous_task:
            assignee = previous_task[0].assignee
        else:
            assignee = None

        # The target assignee may have left the team in the mean time.
        if not self.team.members.filter(user=assignee).exists():
            assignee = None

        task = Task(team=self.team, team_video=self.team_video,
                    language=self.language, type=type,
                    assignee=assignee)

        task.new_subtitle_version = self.new_subtitle_version

        task.set_expiration()

        task.save()

        if sends_notification:
            # notify original submiter (assignee of self)
            notifier.reviewed_and_sent_back.delay(self.pk)
        return task

    def complete_approved(self, user):
        """Mark a review/approve task as Approved and complete it.

        :param user: user who is approving he task
        :returns: next task in the workflow.
        """
        self.assignee = user
        self.approved = Task.APPROVED_IDS['Approved']
        return self.complete()

    def complete_rejected(self, user):
        """Mark a review/approve task as Rejected and complete it.

        :param user: user who is approving he task
        :returns: next task in the workflow.
        """
        self.assignee = user
        self.approved = Task.APPROVED_IDS['Rejected']
        return self.complete()

    def complete(self):
        '''Mark as complete and return the next task in the process if applicable.'''

        self.completed = self.now()
        self.save()

        return { 'Subtitle': self._complete_subtitle,
                 'Translate': self._complete_translate,
                 'Review': self._complete_review,
                 'Approve': self._complete_approve,
        }[Task.TYPE_NAMES[self.type]]()

    def _can_publish_directly(self, subtitle_version):
        from teams.permissions import can_publish_edits_immediately

        type = {10: 'Review',
                20: 'Review',
                30: 'Approve'}.get(self.type)

        tasks = (Task.objects._type([type], True, 'Approved')
                             .filter(language=self.language))

        return (can_publish_edits_immediately(self.team_video,
                                                    self.assignee,
                                                    self.language) and
                subtitle_version and
                subtitle_version.previous_version() and
                subtitle_version.previous_version().is_public() and
                subtitle_version.subtitle_language.is_complete_and_synced() and
                tasks.exists())

    def _find_previous_assignee(self, type):
        """Find the previous assignee for a new review/approve task for this video.

        NOTE: This is different than finding out the person to send a task back
              to!  This is for saying "who reviewed this task last time?".

        For now, we'll assign the review/approval task to whomever did it last
        time (if it was indeed done), but only if they're still eligible to
        perform it now.

        """
        from teams.permissions import can_review, can_approve

        if type == 'Approve':
            # Check if this is a post-publish edit.
            # According to #1039 we don't wanna auto-assign the assignee
            version = self.get_subtitle_version()
            if version and version.subtitle_language.is_complete_and_synced():
                return None

            type = Task.TYPE_IDS['Approve']
            can_do = can_approve
        elif type == 'Review':
            type = Task.TYPE_IDS['Review']
            can_do = partial(can_review, allow_own=True)
        else:
            return None

        last_task = self.team_video.task_set.complete().filter(
            language=self.language, type=type
        ).order_by('-completed')[:1]

        if last_task:
            candidate = last_task[0].assignee
            if candidate and can_do(self.team_video, candidate, self.language):
                return candidate

    def _complete_subtitle(self):
        """Handle the messy details of completing a subtitle task."""
        sv = self.get_subtitle_version()

        # TL;DR take a look at #1206 to know why i did this
        if self.workflow.requires_review_or_approval and not self._can_publish_directly(sv):

            if self.workflow.review_enabled:
                task = Task(team=self.team, team_video=self.team_video,
                            new_subtitle_version=sv,
                            new_review_base_version=sv,
                            language=self.language, type=Task.TYPE_IDS['Review'],
                            assignee=self._find_previous_assignee('Review'))
                task.set_expiration()
                task.save()
            elif self.workflow.approve_enabled:
                task = Task(team=self.team, team_video=self.team_video,
                            new_subtitle_version=sv,
                            new_review_base_version=sv,
                            language=self.language, type=Task.TYPE_IDS['Approve'],
                            assignee=self._find_previous_assignee('Approve'))
                task.set_expiration()
                task.save()
        else:
            # Subtitle task is done, and there is no approval or review
            # required, so we mark the version as approved.
            sv.publish()

            # We need to make sure this is updated correctly here.
            from apps.videos import metadata_manager
            metadata_manager.update_metadata(self.team_video.video.pk)

            if self.workflow.autocreate_translate:
                # TODO: Switch to autocreate_task?
                _create_translation_tasks(self.team_video, sv)

            upload_subtitles_to_original_service.delay(sv.pk)
            task = None
        return task

    def _complete_translate(self):
        """Handle the messy details of completing a translate task."""
        sv = self.get_subtitle_version()

        # TL;DR take a look at #1206 to know why i did this
        if self.workflow.requires_review_or_approval and not self._can_publish_directly(sv):

            if self.workflow.review_enabled:
                task = Task(team=self.team, team_video=self.team_video,
                            new_subtitle_version=sv,
                            new_review_base_version=sv,
                            language=self.language, type=Task.TYPE_IDS['Review'],
                            assignee=self._find_previous_assignee('Review'))
                task.set_expiration()
                task.save()
            elif self.workflow.approve_enabled:
                # The review step may be disabled.  If so, we check the approve step.
                task = Task(team=self.team, team_video=self.team_video,
                            new_subtitle_version=sv,
                            new_review_base_version=sv,
                            language=self.language, type=Task.TYPE_IDS['Approve'],
                            assignee=self._find_previous_assignee('Approve'))
                task.set_expiration()
                task.save()
        else:
            sv.publish()

            # We need to make sure this is updated correctly here.
            from apps.videos import metadata_manager
            metadata_manager.update_metadata(self.team_video.video.pk)
            upload_subtitles_to_original_service.delay(sv.pk)

            task = None

        return task

    def _complete_review(self):
        """Handle the messy details of completing a review task."""
        approval = self.approved == Task.APPROVED_IDS['Approved']
        sv = self.get_subtitle_version()

        self._add_comment()

        task = None
        if self.workflow.approve_enabled:
            # Approval is enabled, so...
            if approval:
                # If the reviewer thought these subtitles were good we create
                # the next task.
                task = Task(team=self.team, team_video=self.team_video,
                            new_subtitle_version=sv,
                            new_review_base_version=sv,
                            language=self.language, type=Task.TYPE_IDS['Approve'],
                            assignee=self._find_previous_assignee('Approve'))
                task.set_expiration()
                task.save()

                # Notify the appropriate users.
                notifier.reviewed_and_pending_approval.delay(self.pk)
            else:
                # Otherwise we send the subtitles back for improvement.
                task = self._send_back()
        else:
            # Approval isn't enabled, so the ruling of this Review task
            # determines whether the subtitles go public.
            if approval:
                # Make these subtitles public!
                self.new_subtitle_version.publish()

                # If the subtitles are okay, go ahead and autocreate translation
                # tasks if necessary.
                if self.workflow.autocreate_translate:
                    _create_translation_tasks(self.team_video, sv)

                # Notify the appropriate users and external services.
                notifier.reviewed_and_published.delay(self.pk)
                upload_subtitles_to_original_service.delay(sv.pk)
            else:
                # Send the subtitles back for improvement.
                task = self._send_back()

        # Before we go, we need to record who reviewed these subtitles, so if
        # necessary we can "send back" to them later.
        if self.assignee:
            sv.set_reviewed_by(self.assignee)

        return task

    def _complete_approve(self):
        """Handle the messy details of completing an approve task."""
        approval = self.approved == Task.APPROVED_IDS['Approved']
        sv = self.get_subtitle_version()

        self._add_comment()

        if approval:
            # The subtitles are acceptable, so make them public!
            self.new_subtitle_version.publish()

            # Create translation tasks if necessary.
            if self.workflow.autocreate_translate:
                _create_translation_tasks(self.team_video, sv)

            # And send them back to the original service.
            upload_subtitles_to_original_service.delay(sv.pk)
            task = None
        else:
            # Send the subtitles back for improvement.
            task = self._send_back()

        # Before we go, we need to record who approved these subtitles, so if
        # necessary we can "send back" to them later.
        if self.assignee:
            sv.set_approved_by(self.assignee)

        # Notify the appropriate users.
        notifier.approved_notification.delay(self.pk, approval)
        return task

    def get_perform_url(self):
        """Return a URL for whatever dialog is used to perform this task."""
        return reverse('teams:perform_task', args=(self.team.slug, self.id))

    def get_widget_url(self):

        mode = Task.TYPE_NAMES[self.type].lower()

        if self.get_subtitle_version():
            sl = self.get_subtitle_version().subtitle_language
            base_url = shims.get_widget_url(sl, mode=mode, task_id=self.pk)
        else:
            video = self.team_video.video

            if self.language:
                sl = video.subtitle_language(language_code=self.language)

                if sl:
                    base_url = reverse("videos:translation_history", kwargs={
                        "video_id": video.video_id,
                        "lang": sl.language_code,
                        "lang_id": sl.pk,
                    })
                else:
                    # The subtitleLanguage may not exist (yet).
                    base_url = video.get_absolute_url()
            else:
                # Subtitle tasks might not have a language.
                base_url = video.get_absolute_url()

        return base_url + "?t=%s" % self.pk

    def needs_start_dialog(self):
        """Check if this task needs the start dialog.

        The only time we need it is when a user is starting a
        transcribe/translate task.  We don't need it for review/approval, or
        if the task is being resumed.
        """
        # We use the start dialog for select several things:
        #   - primary audio language
        #   - language of the subtitles
        #   - language to translate from
        # If we have a SubtitleVersion to use, then we have all the info we
        # need and can skip the dialog.
        return (self.new_review_base_version is None and
                self.get_subtitle_version() is None)

    def get_reviewer(self):
        """For Approve tasks, return the last user to Review these subtitles.

        May be None if this task is not an Approve task, or if we can't figure
        out the last reviewer for any reason.

        """
        if self.get_type_display() == 'Approve':
            previous = Task.objects.complete().filter(
                team_video=self.team_video,
                language=self.language,
                team=self.team,
                type=Task.TYPE_IDS['Review']).order_by('-completed')[:1]

            if previous:
                return previous[0].assignee

    def set_expiration(self):
        """Set the expiration_date of this task.  Does not save().

        Requires that self.team and self.assignee be set correctly.

        """
        if not self.assignee or not self.team.task_expiration:
            self.expiration_date = None
        else:
            limit = datetime.timedelta(days=self.team.task_expiration)
            self.expiration_date = self.now() + limit

    def get_subtitle_version(self):
        """ Gets the subtitle version related to this task.
        If the task has a subtitle_version attached, return it and
        if not, try to find it throught the subtitle language of the video.

        Note: we need this since we don't attach incomplete subtitle_version
        to the task (and if we do we need to set the status to unmoderated and
        that causes the version to get published).
        """

        # autocreate sets the subtitle_version to another
        # language's subtitle_version and that was breaking
        # not only the interface but the new upload method.
        if (self.new_subtitle_version and
            self.new_subtitle_version.language_code == self.language):
            return self.new_subtitle_version

        if not hasattr(self, "_subtitle_version"):
            language = self.team_video.video.subtitle_language(self.language)
            self._subtitle_version = (language.get_tip(public=False)
                                      if language else None)
        return self._subtitle_version

    def is_blocked(self):
        """Return whether this task is "blocked".
        "Blocked" means that it's a translation task but the source language
        isn't ready to be translated yet.
        """
        subtitle_version = self.get_subtitle_version()
        if not subtitle_version:
            return False
        source_language = subtitle_version.subtitle_language.get_translation_source_language()
        if not source_language:
            return False
        can_perform = (source_language and
                       source_language.is_complete_and_synced())

        if self.get_type_display() != 'Translate':
            if self.get_type_display() in ('Review', 'Approve'):
                # review and approve tasks will be blocked if they're
                # a translation and they have a draft and the source
                # language no longer  has published version
                if not can_perform or source_language.language_code == self.language:
                    return True
        return not can_perform

    def save(self, update_team_video_index=True, *args, **kwargs):
        is_review_or_approve = self.get_type_display() in ('Review', 'Approve')

        if self.language:
            assert self.language in VALID_LANGUAGE_CODES, \
                "Subtitle Language should be a valid code."

        result = super(Task, self).save(*args, **kwargs)

        if update_team_video_index:
            tasks.update_one_team_video.delay(self.team_video.pk)

        return result

class CollaborationWorkflow(models.Model):
    """Workflow for teams that use the collaboration model."""
    team = models.ForeignKey('Team', unique=True)

    COMPLETION_ANYONE = "A"
    COMPLETION_REVIEWER = "R"
    COMPLETION_APPROVER = "P"
    COMPLETION_POLICY_CHOICES = (
        (COMPLETION_ANYONE, 'Anyone'),
        (COMPLETION_REVIEWER, 'Reviewer'),
        (COMPLETION_APPROVER, 'Approver'),
    )

    completion_policy = models.CharField(max_length=1,
                                         default=COMPLETION_ANYONE,
                                         choices=COMPLETION_POLICY_CHOICES)
    on_complete_publish_latest = models.BooleanField(default=False)
    on_complete_publish_all = models.BooleanField(default=False)
    on_complete_notify_managers = models.BooleanField(default=False)
    only_1_subtitler = models.BooleanField(default=True)
    only_1_reviewer = models.BooleanField(default=True)
    only_1_approver = models.BooleanField(default=True)
    limit_open_tasks = models.IntegerField(default=0)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    def needs_review(self):
        return self.completion_policy in (self.COMPLETION_REVIEWER,
                                          self.COMPLETION_APPROVER)

    def needs_approval(self):
        return self.completion_policy == self.COMPLETION_APPROVER

    def member_can_approve(self, member):
        return member.role in (ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER)

class DefaultWorkflow(object):
    """Workflow for teams that use the default model.

    Unlike TaskWorkflow or CollaborationWorkflow, DefaultWorkflow is a plain
    python object, not a django model.
    """
    def __init__(self, team):
        self.team = team

def get_team_workflow(team):
    """Get a workflow object for a team.

    This function is used by the Team.workflow property.
    """
    if team.workflow_style == WORKFLOW_TASKS:
        return TaskWorkflow.objects.get_or_create(team=team)[0]
    elif team.workflow_style == WORKFLOW_COLLABORATION:
        return CollaborationWorkflow.objects.get_or_create(team=team)[0]
    elif team.workflow_style == WORKFLOW_DEFAULT:
        return DefaultWorkflow(team)
    else:
        raise ValueError("Unknown workflow_style: %s" % team.workflow_style)
