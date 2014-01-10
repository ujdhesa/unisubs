describe('Test the collaboration service', function() {
    var $httpBackend, CollaborationStorage;
    var videoId = 'abcdef';
    var languageCode = 'en';
    var teamSlug = 'my-team';
    var taskID = 123;
    var versionNumber = 1;
    var username = 'ben';
    var collaborationNotesUrl = ('/api2/partners/videos/' + videoId +
        '/languages/' + languageCode + '/collaboration/notes/');
    var endorsementResourceUrl = ('/api2/partners/videos/' + videoId +
        '/languages/' + languageCode + '/endorsements/');
    var removeEndorsementResourceUrl = ('/api2/partners/videos/' + videoId +
        '/languages/' + languageCode + '/endorsements/ben/');
    var taskSaveUrl = ('/api2/partners/teams/' + teamSlug + '/tasks/' +
        taskID + '/');
    var authHeaders = {
        'x-api-username': 'ben',
        'x-apikey': '123456'
    }

    beforeEach(function() {
        module('amara.SubtitleEditor.collab');
        module('amara.SubtitleEditor.mocks');
    });
    beforeEach(inject(function($http, $injector, EditorData) {
        $httpBackend = $injector.get('$httpBackend');
        CollaborationStorage = $injector.get('CollaborationStorage');
        EditorData.authHeaders = authHeaders;
        EditorData.team_slug = teamSlug;
        EditorData.task_id = taskID;
        EditorData.username = username;
        // make the $http service not add extra headers to the requests.
        $http.defaults.headers.common = {};
        $http.defaults.headers.post = {};
        $http.defaults.headers.put = {};
    }));

    it('Can approve tasks', function() {
        var expectedData = {
            complete: true,
            body: 'note',
            version_number: versionNumber,
        };
        $httpBackend.expectPUT(taskSaveUrl, expectedData, authHeaders).respond(200, '');
        CollaborationStorage.approveTask(versionNumber, 'note');
        $httpBackend.verifyNoOutstandingExpectation();
    });

    it('Can reject tasks', function() {
        var expectedData = {
            complete: true,
            body: 'note',
            send_back: true,
            version_number: versionNumber,
        };
        $httpBackend.expectPUT(taskSaveUrl, expectedData, authHeaders).respond(200, '');
        CollaborationStorage.sendBackTask(versionNumber, 'note');
        $httpBackend.verifyNoOutstandingExpectation();
    });

    it('Can save task notes', function() {
        $httpBackend.expectPUT(taskSaveUrl, {'body': 'note text'}, authHeaders).respond(200, '');
        CollaborationStorage.updateTaskNotes('note text');
        $httpBackend.verifyNoOutstandingExpectation();
    });

    it('Can mark subtitles as endorsed', function() {
        $httpBackend.expectPOST(endorsementResourceUrl, {}, authHeaders).respond(201, '');
        CollaborationStorage.endorseCollaboration(videoId, languageCode);
        $httpBackend.verifyNoOutstandingExpectation();
    });

    it('Can remove endorsements', function() {
        $httpBackend.expectPUT(removeEndorsementResourceUrl, {'remove': true}, authHeaders).respond(202, '');
        CollaborationStorage.removeEndorsement(videoId, languageCode);
        $httpBackend.verifyNoOutstandingExpectation();
    });


    it('Can fetch collaboration notes', function() {
        var url = collaborationNotesUrl;
        var noteData = [
            {
                'datetime': '2012-01-01T00:00:00',
                'datetime_display': 'Sun Jan 01 2012 12:00am',
                'user': 'ben',
                'text': 'note1'
            },
            {
                'datetime': '2012-01-01T12:00:00',
                'datetime_display': 'Sun Jan 01 2012 12:00pm',
                'user': 'ben',
                'text': 'note2'
            }
        ];
        var response = null;

        $httpBackend.expectGET(url, authHeaders)
            .respond(200, noteData);
        CollaborationStorage.getCollaborationNotes(videoId, languageCode)
            .then(function(responseData) {
            // CollaborationStorage should return the JSON data sent back from
            // the server.
            expect(responseData).toEqual(noteData);
        });
        $httpBackend.verifyNoOutstandingExpectation();
    });

    it('Can add collaboration notes', function() {
        var url = collaborationNotesUrl;
        var noteResponse = {
            'datetime': '2012-01-01T00:00:00',
            'datetime_display': 'Sun Jan 01 2012 12:00am',
            'user': 'ben',
            'text': 'note text'
        };
        var response = null;

        $httpBackend.expectPOST(url, {'text': 'note text'}, authHeaders)
            .respond(201, noteResponse);
        CollaborationStorage.addCollaborationNote(videoId, languageCode, 'note text')
            .then(function(responseData) {
            // CollaborationStorage should return the JSON data sent back from
            // the server.
            expect(responseData).toEqual(noteResponse);
        });
        $httpBackend.verifyNoOutstandingExpectation();
    });
});

