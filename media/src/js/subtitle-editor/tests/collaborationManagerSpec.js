describe('Test the CollaborationManager class', function() {
    var CollaborationManager;
    var CollaborationStorage;
    var EditorData;
    var videoId = 'abcdef';
    var languageCode = 'en';

    beforeEach(function() {
        module('amara.SubtitleEditor.collab');
        module('amara.SubtitleEditor.mocks');
        module('amara.SubtitleEditor.mocks.CollaborationStorage');
    });

    beforeEach(inject(function($injector) {
        CollaborationManager = $injector.get('CollaborationManager');
        CollaborationStorage = $injector.get('CollaborationStorage');
        EditorData = $injector.get('EditorData');
        EditorData.video.id = videoId;
        EditorData.editingVersion.languageCode = languageCode;
    }));

    function makeCollaborationManager(editorDataToSet) {
        var keysToClear = [
            'task_id',
            'task_needs_pane',
            'collaboration_id',
            'collaboration_state',
            'collaborationNotes',
            'collaborators'
        ];
        _.each(keysToClear, function(key) {
            EditorData[key] = undefined;
        });
        _.each(_.keys(editorDataToSet), function(key) {
            EditorData[key] = editorDataToSet[key];
        });
        return new CollaborationManager();
    }

    function makeCollaborationManagerTasks() {
        return makeCollaborationManager({
            task_id: 123,
            task_needs_pane: true
        });
    }

    function makeCollaborationManagerCollab() {
        return makeCollaborationManager({
            collaboration_id: 123,
            collaboration_state: 'being-reviewed',
            collaborators: [],
            collaborationNotes: [],
        });
    }

    function checkCollaborationManagerState(mode) {
        var collab = new CollaborationManager();
        if(mode === null) {
            expect(collab.enabled).toBe(false);
        } else {
            expect(collab.enabled).toBe(true);
        }
        expect(collab.mode).toBe(mode);
    }

    it('is disabled if neither tasks nor collaborations are active', function() {
        // If neither task_id nor collaboration_id is present, the mode
        // should be null.
        checkCollaborationManagerState(null);
    });

    it('is enabled when a task is active if task_needs_pane is true', function() {
        EditorData.task_id = 123;
        EditorData.task_needs_pane = false;
        checkCollaborationManagerState(null);

        EditorData.task_needs_pane = true;
        checkCollaborationManagerState('tasks');
    });

    if('is enabled when a collaboration is active and we are in the review or approve stage', function() {
        EditorData.collaboration = 123;
        EditorData.collaboration_state = 'being-subtitled';
        checkCollaborationManagerState(null);

        EditorData.collaboration_state = 'being-reviewed';
        checkCollaborationManagerState('collab');

        EditorData.collaboration_state = 'being-approved';
        checkCollaborationManagerState('collab');
    });

    it('Fetches the collaborators', function() {
        var collaborators = [ 'alice', 'bob' ];
        var collab = makeCollaborationManager({
            collaboration_id: 123,
            collaboration_state: 'being-reviewed',
            collaborators: collaborators
        });
        expect(collab.collaborators).toEqual(collaborators);
    });

    it('Fetches the initial note', function() {
        var collab = makeCollaborationManager({
            collaboration_id: 123,
            collaboration_state: 'being-reviewed',
            savedNotes: 'my note'
        });
        expect(collab.currentNote).toEqual('my note');
        // default to an empty string if savedNotes is not present
        var collab = makeCollaborationManager({
            collaboration_id: 123,
            collaboration_state: 'being-reviewed',
            savedNotes: undefined
        });
        expect(collab.currentNote).toEqual('');
    });

    it('Fetches collaboration notes', function() {
        var noteData = [
            {
                datetime: '2012-01-01T00:00:00',
                datetime_display: 'Sun Jan 01 2012 12:00am',
                user: 'ben',
                text: 'note1'
            },
            {
                datetime: '2012-01-01T12:00:00',
                datetime_display: 'Sun Jan 01 2012 12:00pm',
                user: 'ben',
                text: 'note2'
            }
        ];

        var collab = makeCollaborationManager({
            collaboration_id: 123,
            collaboration_state: 'being-reviewed',
            collaborators: [],
            collaborationNotes: noteData
        });
        expect(collab.notes).toEqual(noteData);
    });


    it('Can save notes in tasks mode', function() {
        var collab = makeCollaborationManagerTasks();
        collab.currentNote = 'new note';
        var promise = collab.saveNote();
        expect(CollaborationStorage.updateTaskNotes).toHaveBeenCalledWith('new note');
    });

    it('Can save notes in collab mode', function() {
        var collab = makeCollaborationManagerCollab();
        collab.currentNote = 'new note';
        var returnValue = collab.saveNote();
        expect(CollaborationStorage.addCollaborationNote).toHaveBeenCalledWith(videoId, languageCode, 'new note');
        var noteData = {
            datetime: '2012-01-01T00:00:00',
            datetime_display: 'Sun Jan 01 2012 12:00am',
            user: 'ben',
            text: 'note1'
        };
        CollaborationStorage.resolveDeferred('addCollaborationNote', noteData);
        expect(collab.notes).toEqual([noteData]);
        expect(collab.currentNote).toEqual('');
    });

    it('Does not save notes if no changes were made', function() {
        var collab = makeCollaborationManagerCollab();
        expect(collab.noteNeedsSave()).toBe(false);
        var returnValue = collab.saveNote();
        expect(CollaborationStorage.addCollaborationNote).not.toHaveBeenCalled();
        // Even though saveNote is not changing anything, it should still
        // return a dummy promise
        expect(returnValue.then).not.toBe(undefined);
        // Change the note
        collab.currentNote = 'new note';
        expect(collab.noteNeedsSave()).toBe(true);
        // After the note is saved, noteNeedsSave() should return false again
        collab.saveNote();
        CollaborationStorage.resolveDeferred('addCollaborationNote');
        expect(collab.noteNeedsSave()).toBe(false);
    });

    it('Can approve tasks', function() {
        var collab = makeCollaborationManagerTasks();
        collab.currentNote = 'new note';
        collab.approveTask(123);
        expect(CollaborationStorage.approveTask).toHaveBeenCalledWith(123,
            'new note');
        // Once the task is approved, we should update savedNote
        CollaborationStorage.resolveDeferred('approveTask');
        expect(collab.savedNote).toEqual('new note');
    });

    it('Can send back tasks', function() {
        var collab = makeCollaborationManagerTasks();
        collab.currentNote = 'new note';
        collab.sendBackTask(123);
        expect(CollaborationStorage.sendBackTask).toHaveBeenCalledWith(123,
            'new note');
        // Once the task is approved, we should update savedNote
        CollaborationStorage.resolveDeferred('sendBackTask');
        expect(collab.savedNote).toEqual('new note');
    });

    it('Can endorse collaborations', function() {
        var collab = makeCollaborationManagerCollab();
        collab.endorseCollaboration();
        expect(CollaborationStorage.endorseCollaboration).toHaveBeenCalledWith(videoId, languageCode);
    });

    it('Should enable the save button when the notes are changed in tasks mode', function() {
        var collab = makeCollaborationManagerTasks();
        expect(collab.enableSaveButton()).toEqual(false);
        collab.currentNote = 'new note';
        expect(collab.enableSaveButton()).toEqual(true);
        // In collab mode, we never enable the save button because of the note
        // state since we have the add note button
        collab = makeCollaborationManagerCollab();
        expect(collab.enableSaveButton()).toEqual(false);
        collab.currentNote = 'new note';
        expect(collab.enableSaveButton()).toEqual(false);
    });
});


