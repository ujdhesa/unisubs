describe('Test the SubtitleStorage service', function() {
    var $httpBackend, SubtitleStorage;
    var videoId = 'abcdef';
    var languageCode = 'en';
    var subtitleResourceUrl = ('/api2/partners/videos/' + videoId +
        '/languages/' + languageCode + '/subtitles/');
    var endorsementResourceUrl = ('/api2/partners/videos/' + videoId +
        '/languages/' + languageCode + '/endorsements/');
    var authHeaders = {
        'x-api-username': 'ben',
        'x-apikey': '123456'
    }

    beforeEach(function() {
        module('amara.SubtitleEditor.subtitles.services');
        module('amara.SubtitleEditor.mocks');
    });
    beforeEach(inject(function($http, $injector, EditorData) {
        $httpBackend = $injector.get('$httpBackend');
        SubtitleStorage = $injector.get('SubtitleStorage');
        EditorData.authHeaders = authHeaders;
        // make the $http service not add extra headers to the requests.
        $http.defaults.headers.common = {};
        $http.defaults.headers.post = {};
        $http.defaults.headers.put = {};
    }));

    it('can save subtitles', function() {
        var url = '/api2/partners/videos/';
        // Define a bunch of fake data that we will be trying to save
        var dfxpString = 'dfxp data';
        var title = 'title';
        var description = 'description';
        var metadata = {
            'speaker-name': 'speaker name'
        }
        var isComplete = true;
        var saveData =  {
            video: videoId,
            language: languageCode,
            subtitles: dfxpString,
            sub_format: 'dfxp',
            title: title,
            description: description,
            metadata: metadata,
            is_complete: isComplete,
        }

        function checkSaveSubtitlesCall() {
            $httpBackend.expectPOST(subtitleResourceUrl, saveData, authHeaders).respond(201, '');
            SubtitleStorage.saveSubtitles(videoId, languageCode, dfxpString,
                title, description, metadata, isComplete);
            $httpBackend.verifyNoOutstandingExpectation();
        }
        checkSaveSubtitlesCall();
        // Try again with isComplete=false
        saveData['is_complete'] = isComplete = false;
        checkSaveSubtitlesCall();
        // Try again with isComplete=undefined
        isComplete = undefined;
        saveData['is_complete'] = null;
        checkSaveSubtitlesCall();
    });

    it('Can mark subtitles as endorsed', function() {
        $httpBackend.expectPOST(endorsementResourceUrl, {}, authHeaders).respond(201, '');
        SubtitleStorage.endorseCollaboration(videoId, languageCode);
    });


});

