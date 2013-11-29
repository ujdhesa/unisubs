import collections
import functools
import os
import urlparse

import mock
from celery.task import Task
from django.core.cache import cache
from django.conf import settings
from nose.plugins import Plugin
from nose.tools import assert_equal
import mock
import requests


REQUEST_CALLBACKS = []

class Response(dict):

    status = 200
    content = ""

    def __getitem__(self, key):
        return getattr(self, key)

def reset_requests():
    global REQUEST_CALLBACKS
    REQUEST_CALLBACKS = []

def reload_model(model_obj):
    return model_obj.__class__.objects.get(pk=model_obj.pk)

def store_request_call(url, **kwargs):
    method = kwargs.pop('method', None)
    data = urlparse.parse_qs(kwargs.pop("body", ""))
    for k,v in data.items():
        data[k] = v[0]
    global REQUEST_CALLBACKS
    if not '/solr' in url:
        REQUEST_CALLBACKS.append([url, method, data])
    return Response(), ""

class TestCaseMessagesMixin(object):
    def _getMessagesCount(self, response, level=None):
        messages =  response.context['messages']
        if level:
            actual_num = len([x for x in messages if x.level==level])
        else:
            actual_num = len(messages)

        return actual_num

    def assertMessageCount(self, response, expect_num, level=None):
        """
        Asserts that exactly the given number of messages have been sent.
        """
        actual_num = self._getMessagesCount(response, level=level)
        if actual_num != expect_num:
            self.fail('Message count was %d, expected %d' %
                    (actual_num, expect_num)
                )

    def assertMessageEqual(self, response, text):
        """
        Asserts that the response includes the message text.
        """

        messages = [m.message for m in response.context['messages']]

        if text not in messages:
            self.fail(
                'No message with text "%s", messages were: %s' % 
                    (text, messages)
                )

    def assertMessageNotEqual(self, response, text):
        """
        Asserts that the response does not include the message text.
        """

        messages = [m.message for m in response.context['messages']]

        if text in messages:
            self.fail(
                'Message with text "%s" found, messages were: %s' % 
                    (text, messages)
                )

save_thumbnail_in_s3 = mock.Mock()
update_team_video = mock.Mock()
update_search_index = mock.Mock()

def mock_youtube_get_entry(video_id):
    # map video ids to (title, description, author, duration) tuples
    video_id_map = {
        'e4MSN6IImpI': ('Doodling in Math Class: Binary Trees',
                        'Vihart', '228'),
        '2tP_NU9a5pE': ('Universal Subtitles Overview video',
                        'universalsubtitles', '236'),
        'cvAZQZa9iWM': ('\xce\x91mara Test Video 1', 'amaratestuser', '4'),
        'q26umaF242I': ('Amara Test Video 2', 'amaratestuser', '4'),
        '1GAIwV7eRNQ': ('Amara Test Video 3', 'amaratestuser', '4'),
        'i_0DXxNeaQ0': ('What is up with Noises? (The Science and Mathematics'
                        ' of Sound, Frequency, and Pitch)', 'Vihart', '769'),
        'pQ9qX8lcaBQ': ('The Sea Organ of Zadar', 'M0narchs', '128'),
        'L4XpSM87VUk': ("Tour of darren's rabbit-centric room.",
                        'amaratestchannel', '41'),
        '_ShmidkrcY0': ('\xd0\xa8\xd1\x80\xd0\xb5\xd0\xba 4 HD '
                        '(\xd1\x80\xd1\x83\xd1\x81\xd1\x81\xd0\xba\xd0\xb8\xd0\xb5 '
                         '\xd1\x81\xd1\x83\xd0\xb1\xd1\x82\xd0\xb8\xd1\x82\xd1\x80\xd1\x8b)',
                        'QAZRUS', '79'),
        'heKK95DAKms': ('Doodling in Math Class: Snakes + Graphs', 'Vihart',
                        '265'),
        'iizcw0Sgces': ('Arrasou Viado!', 'Fernando Takai', '9'),
        'WqJineyEszo': ('X Factor Audition - '
                        'Stop Looking At My Mom Rap - Brian Bradley',
                        'clowntownhonkhonk', '121'),
        'z2U_jf0urVQ': ('Single_Ladies_-_katylene_Ft._Vaness\xc3\xa3o_.wmv',
                        'Lauragusta', '25'),
        'zXjPQYgT25Q': ('Shming swimming', 'ChrisSunHwa', '390'),
        'OFaWxcH6I9E': ('Isogenic Engine: HTML5 Canvas - 250,000 '
                        'tiles on the map at 93fps...', 'coolbloke1324',
                        '29'),
        'Hhgfz0zPmH4': ('Google Goggles', 'Google', '123'),
        'KXcdfxeeG2w': ('My Video', 'Fernando Takai', '56'),
        'Cf06WJQ4FnE': ('Evil Hamster', 'DeefHimSelf', '87'),
        'sXUeO3auRZg': ('\xd0\x9f\xd0\xb5\xd1\x82\xd1\x83\xd1\x85 \xd0\xbe\xd1\x82\xd0\xb6\xd0\xb8\xd0\xb3\xd0\xb0\xd0\xb5\xd1\x82!!!', 'SRPRS3978', '59'),
        'bNQB7_nJ4Wk': ('Testing', 'Fernando Takai', '518'),
        '61LB3qfRK1I': ('Testing', 'Fernando Takai', '55'),
        'z1lbFNXX1ks': ('My Video', 'Fernando Takai', '278'),
        'g_0lX7aVAL8': ('Teste Nova Ficha', 'Fernando Takai', '137'),
        'VChlH2KQf0A': ('Amazonia \xc3\xa9 Agora!', 'Fernando Takai', '137'),
        'ObM9y_tIdXE': ('0', 'Fernando Takai', '137'),
        'X2YPkjL8fv4': ('Teste: Mais um V\xc3\xaddeo Legal', 'Fernando Takai',
                        '278'),
        'rIYAziWA9Zg': ('Teste de video grande', 'Fernando Takai', '278'),
        'EKSRnuzdJfU': ('V\xc3\xaddeo de Teste', 'Fernando Takai', '55'),
        'OJC58_mPwZ4': ('Teste de video mov', 'Fernando Takai', '137'),
        'a2Hn2hNPbX4': ('Teste de video com Library 8', 'Fernando Takai',
                        '55'),
        'vrSoZwcyyG8':  ('Teste Reis 3', 'Fernando Takai', '55'),
        'lgBRD3Hqggw': ('@alvarofreitas e o juramento dos lanternas verdes.',
                        'Fernando Takai', '75'),
        '_ZUywElGFLk': ('Ok go - here it goes again', 'Fernando Takai',
                        '275'),
        '_9RAPBfZby0': ('Rodrigo Teaser - Smooth Criminal', 'Fernando Takai',
                         '209'),
        'sWgyQjh5k7s': ('Status', 'Fernando Takai', '20'),
        'MJRF8xGzvj4': ('David Bowie/Pat Metheny - This Is Not America '
                        '(Promo Clip)', 'skytrax1', '214'),
        'po0jY4WvCIc': ('Michael Jackson Pepsi Generation', 'GiraldiMedia',
                        '92'),
        'UOtJUmiUZ08': ('The YouTube Interview with Katy Perry',
                        'KatyPerryMusic', '1892'),
        'HaAVZ2yXDBo': ("Breakfast at Ginger's- golden retriever dog eats "
                        "with hands", 'sawith65', '83'),
        'woobL2yAxD4': ('Goat yelling like a man', 'latestvideoss', '25'),
        'tKTZoB2Vjuk': ('Google Python Class Day 1 Part 1',
                        'GoogleDevelopers', '3097'),
        'osexbB_hX4g': ('DO YOU SEE THAT??!!', 'otherijustine', '90'),
        'hPbYnNRw4UM': ('ONN | Documentary - Beginning',
                        'OccupyNewsNetworkUK', '1971'),
    }
    try:
        title, author, duration = video_id_map[video_id]
    except KeyError:
        # We should have data stored for video_id, but we don't.  Run a quick
        # query so that it's easy to add.
        from videos.types import youtube, VideoTypeError
        from gdata.service import RequestError
        try:
            entry = youtube.yt_service.GetYouTubeVideoEntry(video_id=str(video_id))
        except RequestError as e:
            err = e[0].get('body', 'Undefined error')
            raise VideoTypeError('Youtube error: %s' % err)
        raise ValueError("Don't know how to handle youtube video: %s\n"
                         "query result: (%r, %r, %r)" %
                         (video_id, entry.media.title.text,
                          entry.author[0].name.text,
                          entry.media.duration.seconds))
    # Youtube descriptions can be very long, just use a mock one for testing
    # purposes
    description = "Test Description"

    entry = mock.Mock()
    mock_author = mock.Mock()
    mock_author.name.text = author
    mock_author.uri.text = author
    entry.author = [mock_author]
    entry.media.title.text = title
    entry.media.description.text = description
    entry.media.duration.seconds = duration
    entry.media.thumbnail = []
    for i in range(4):
        thumb = mock.Mock()
        thumb.url = 'http://i.ytimg.com/vi/%s/%s.jpg' % (video_id, i)
        thumb.width = i * 100
        thumb.height = i * 75
        entry.media.thumbnail.append(thumb)
    return entry
youtube_get_entry = mock.Mock(side_effect=mock_youtube_get_entry)
youtube_get_subtitled_languages = mock.Mock(return_value=[])
_add_amara_description_credit_to_youtube_vurl = mock.Mock()

current_locks = set()
acquire_lock = mock.Mock(
    side_effect=lambda c, name: current_locks.add(name))
release_lock = mock.Mock(
    side_effect=lambda c, name: current_locks.remove(name))
invalidate_widget_video_cache = mock.Mock()
update_subtitles = mock.Mock()
delete_subtitles = mock.Mock()
update_all_subtitles = mock.Mock()

class MonkeyPatcher(object):
    """Replace a functions with mock objects for the tests.
    """
    def patch_functions(self):
        # list of (function, mock object tuples)
        patch_info = [
            ('videos.tasks.save_thumbnail_in_s3', save_thumbnail_in_s3),
            ('teams.tasks.update_one_team_video', update_team_video),
            ('utils.celery_search_index.update_search_index',
             update_search_index),
            ('videos.types.youtube.YoutubeVideoType._get_entry',
             youtube_get_entry),
            ('videos.types.youtube.YoutubeVideoType.get_subtitled_languages',
             youtube_get_subtitled_languages),
            ('videos.tasks._add_amara_description_credit_to_youtube_vurl',
             _add_amara_description_credit_to_youtube_vurl),
            ('utils.applock.acquire_lock', acquire_lock),
            ('utils.applock.release_lock', release_lock),
            ('widget.video_cache.invalidate_cache',
             invalidate_widget_video_cache),
            ('externalsites.tasks.update_subtitles', update_subtitles),
            ('externalsites.tasks.delete_subtitles', delete_subtitles),
            ('externalsites.tasks.update_all_subtitles', update_all_subtitles),
        ]
        self.patches = []
        self.mock_object_initial_data = {}
        for func_name, mock_obj in patch_info:
            self.start_patch(func_name, mock_obj)

    def start_patch(self, func_name, mock_obj):
        patch = mock.patch(func_name, mock_obj)
        mock_obj = patch.start()
        self.setup_run_original(mock_obj, patch)
        self.mock_object_initial_data[mock_obj] = mock_obj.__dict__.copy()
        self.patches.append(patch)

        if (not func_name.startswith("apps.") and
            not func_name.startswith("utils")):
            # Ugh have to patch the function twice since some modules use
            # app and some don't
            self.start_patch('apps.' + func_name, mock_obj)

    def setup_run_original(self, mock_obj, patch):
        mock_obj.original_func = patch.temp_original
        mock_obj.run_original = functools.partial(self.run_original,
                                                  mock_obj)
        mock_obj.run_original_for_test = functools.partial(
            self.run_original_for_test, mock_obj)

    def run_original(self, mock_obj):
        rv = [mock_obj.original_func(*args, **kwargs)
                for args, kwargs in mock_obj.call_args_list]
        if isinstance(mock_obj.original_func, Task):
            # for celery tasks, also run the delay() and apply() methods
            rv.extend(mock_obj.original_func.delay(*args, **kwargs)
                      for args, kwargs in mock_obj.delay.call_args_list)
            rv.extend(mock_obj.original_func.apply(*args, **kwargs)
                      for args, kwargs in mock_obj.apply.call_args_list)

        return rv

    def run_original_for_test(self, mock_obj):
        # set side_effect to be the original function.  We will undo this when
        # reset_mocks() is called at the end of the test
        mock_obj.side_effect = mock_obj.original_func

    def unpatch_functions(self):
        for patch in self.patches:
            patch.stop()

    def reset_mocks(self):
        for mock_obj, initial_data in self.mock_object_initial_data.items():
            # we used to call reset_mock() here, but this works better.  It
            # also resets the things like return_value and side_effect to
            # their initial value.
            mock_obj.__dict__ = initial_data.copy()

class UnisubsTestPlugin(Plugin):
    name = 'Amara Test Plugin'

    def __init__(self):
        Plugin.__init__(self)
        self.patcher = MonkeyPatcher()
        self.directories_to_skip = set([
            os.path.join(settings.PROJECT_ROOT, 'libs'),
        ])

    def configure(self, options, conf):
        super(UnisubsTestPlugin, self).configure(options, conf)
        # force enabled to always be True.  This only gets loaded because we
        # manually specify the plugin in the dev_settings_test.py file.  So
        # it's pretty safe to assume the user wants us enabled.
        self.enabled = True

    def begin(self):
        self.patcher.patch_functions()

    def finalize(self, result):
        self.patcher.unpatch_functions()

    def afterTest(self, test):
        self.patcher.reset_mocks()
        cache.clear()

    def wantDirectory(self, dirname):
        if dirname in self.directories_to_skip:
            return False
        return None

def patch_for_test(spec):
    """Use mock to patch a function for the test case.

    Use this to decorate a TestCase test or setUp method.  It will call
    TestCase.addCleanup() so that the the patch will stop at the once the test
    is complete.  It will pass in the mock object used for the patch to the
    function.

    Example:

    class FooTest(TestCase):
        @patch_for_test('foo.bar')
        def setUp(self, mock_foo):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            mock_obj = mock.Mock()
            patcher = mock.patch(spec, mock_obj)
            patcher.start()
            self.addCleanup(patcher.stop)
            return func(self, mock_obj, *args, **kwargs)
        return wrapper
    return decorator
patch_for_test.__test__ = False

ExpectedRequest = collections.namedtuple(
    "ExpectedRequest", "method url params data body status_code")

class RequestsMocker(object):
    """Mock code that uses the requests module

    This object patches the various network functions of the requests module
    (get, post, put, delete) with mock functions.  You tell it what requests
    you expect, and what responses to return.

    Example:

    mocker = RequestsMocker()
    mocker.expect_request('get', 'http://example.com/', body="foo")
    mocker.expect_request('post', 'http://example.com/form',
        data={'foo': 'bar'}, body="Form OK")
    with mocker:
        function_to_test()
    """

    def __init__(self):
        self.expected_requests = []

    def expect_request(self, method, url, params=None, data=None, body='',
                       status_code=200):
        self.expected_requests.append(
            ExpectedRequest(method, url, params, data, body, status_code))

    def __enter__(self):
        self.setup_patchers()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unpatch()
        if exc_type is None:
            self.check_no_more_expected_calls()

    def setup_patchers(self):
        self.patchers = []
        for method in ('get', 'post', 'put', 'delete'):
            mock_obj = mock.Mock()
            mock_obj.side_effect = getattr(self, 'mock_%s' % method)
            patcher = mock.patch('requests.%s' % method, mock_obj)
            patcher.start()
            self.patchers.append(patcher)

    def unpatch(self):
        for patcher in self.patchers:
            patcher.stop()
        self.patchers = []

    def mock_get(self, url, params=None, data=None):
        return self.check_request('get', url, params, data)

    def mock_post(self, url, params=None, data=None):
        return self.check_request('post', url, params, data)

    def mock_put(self, url, params=None, data=None):
        return self.check_request('put', url, params, data)

    def mock_delete(self, url, params=None, data=None):
        return self.check_request('delete', url, params, data)

    def check_request(self, method, url, params, data):
        try:
            expected = self.expected_requests.pop(0)
        except IndexError:
            raise AssertionError("RequestsMocker: No more calls expected, "
                                 "but got %s %s %s %s" % 
                                 (method, url, params, data))

        assert_equal(method, expected.method)
        assert_equal(url, expected.url)
        assert_equal(params, expected.params)
        assert_equal(data, expected.data)
        return self.make_response(expected.status_code, expected.body)

    def make_response(self, status_code, body):
        response = requests.Response()
        response._content = body
        response.status_code = status_code
        return response

    def check_no_more_expected_calls(self):
        if self.expected_requests:
            raise AssertionError(
                "leftover expected calls:\n" +
                "\n".join('%s %s %s' % (er.method, er.url, er.params)
                          for er in self.expected_requests))
