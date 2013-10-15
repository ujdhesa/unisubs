import datetime
import factory
from apps.videos.models import Video 
from apps.videos.models import VideoUrl
from apps.teams.models import Team
from apps.teams.models import Partner
from apps.teams.models import TeamMember
from apps.teams.models import MembershipNarrowing
from apps.teams.models import Task
from apps.teams.models import TeamVideo
from apps.teams.models import Invite
from apps.teams.models import Application
from apps.teams.models import Project
from apps.teams.models import TeamLanguagePreference
from apps.teams.models import TaskWorkflow 
from apps.teams.models import BillingReport
from apps.auth.models import CustomUser as User
from apps.auth.models import UserLanguage
from apps.messages.models import Message

class TeamManagerLanguageFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = MembershipNarrowing


class VideoFactory(factory.django.DjangoModelFactory):
    """Creates a video using a sequence.

    """
    FACTORY_FOR = Video
    title = factory.Sequence(lambda n: 'Test Video %d'  %n)
    created = datetime.datetime.now()
    factory.PostGeneration(lambda obj, create, extracted, **kwargs: VideoUrlFactory.create(video=obj))

class VideoUrlFactory(factory.django.DjangoModelFactory):
    """Create a video url to use in creating a video.

    """
    FACTORY_FOR = VideoUrl
    url = factory.Sequence(lambda n: 'http://unisubs.example.com/%d.mp4' % n)
    primary=True
    original=True
    type = 'H'
    video = factory.SubFactory(VideoFactory)

class UserLangFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = UserLanguage


class UserFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = User
    username = factory.Sequence(lambda n: 'TestUser_%d' % n)
    email = factory.LazyAttribute(lambda a: '{0}@example.com'.format(a.username).lower())
    notify_by_email = True
    valid_email = True 
    password = factory.PostGenerationMethodCall('set_password',
                                                'password')
    


class PartnerFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Partner


class TeamFactory(factory.django.DjangoModelFactory):
    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        # Set the interval notification.
        try:
            kwargs['notify_interval'] = getattr(Team, kwargs['notify_interval'])
        except:
            kwargs['notify_interval'] = Team.NOTIFY_HOURLY
        return kwargs


    FACTORY_FOR = Team
    name = factory.Sequence(lambda n: 'Test Team%d' % n)
    slug = factory.Sequence(lambda n: 'test-team-%d' % n)

class TeamMemberFactory(factory.django.DjangoModelFactory):
    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        # Set the user's role for the team, default is owner.
        try:
            kwargs['role'] = getattr(TeamMember, kwargs['role'])
        except:
            kwargs['role'] = TeamMember.ROLE_OWNER
        return kwargs

    FACTORY_FOR = TeamMember
    team = factory.SubFactory(TeamFactory)
    user = factory.SubFactory(UserFactory)


class TeamVideoFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = TeamVideo
    team = factory.SubFactory(TeamFactory)
    video = factory.SubFactory(VideoFactory)
    added_by = factory.SubFactory(UserFactory)
    created = datetime.datetime.now()

class TeamProjectFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Project
    team = factory.SubFactory(TeamFactory)
    created = datetime.datetime.now()
    name = factory.Sequence(lambda n: 'TestProject%d' % n)


class TeamInviteFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Invite


class ApplicationFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Application
    created = datetime.datetime.now()
    pk = factory.Sequence(lambda n: 100+n)


class TeamLangPrefFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = TeamLanguagePreference
    team = factory.SubFactory(TeamFactory)

class WorkflowFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = TaskWorkflow
    
class TaskFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = Task 
    team_video = factory.SubFactory(TeamVideoFactory)

class BillingFactory(factory.django.DjangoModelFactory):
    FACTORY_FOR = BillingReport 
    type = 2

