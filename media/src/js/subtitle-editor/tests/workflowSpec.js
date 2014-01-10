function insertSyncedAndCompletedSubtitle(subtitleList) {
    var sub = subtitleList.insertSubtitleBefore(null);
    subtitleList.updateSubtitleContent(sub, 'content');
    subtitleList.updateSubtitleTime(sub, 500, 1000);
}


describe('The Workflow class', function() {
    var subtitleList = null;
    var workflow = null;

    beforeEach(function() {
        module('amara.SubtitleEditor.subtitles.models');
        module('amara.SubtitleEditor.workflow');
        module('amara.SubtitleEditor.mocks');
    });

    beforeEach(inject(function(SubtitleList, Workflow) {
        subtitleList = new SubtitleList();
        subtitleList.loadXML(null);
        workflow = new Workflow(subtitleList);
    }));

    it('starts in the type stage', function() {
        expect(workflow.stage).toBe('type');
    });

    it('can move to the sync stage anytime', function() {
        workflow.switchStage('sync');
        expect(workflow.stage).toBe('sync');
    });

    it('can move to the the review stage once subs are complete and synced', function() {
        workflow.switchStage('sync');
        expect(workflow.canMoveToReview()).toBeFalsy();
        var sub = subtitleList.insertSubtitleBefore(null);
        expect(workflow.canMoveToReview()).toBeFalsy();
        subtitleList.updateSubtitleContent(sub, 'content');
        expect(workflow.canMoveToReview()).toBeFalsy();
        subtitleList.updateSubtitleTime(sub, 500, 1000);
        expect(workflow.canMoveToReview()).toBeTruthy();

        var sub2 = subtitleList.insertSubtitleBefore(null);
        expect(workflow.canMoveToReview()).toBeFalsy();
        subtitleList.updateSubtitleTime(sub2, 1500, 2000);
        expect(workflow.canMoveToReview()).toBeFalsy();
        subtitleList.updateSubtitleContent(sub2, 'content');
        expect(workflow.canMoveToReview()).toBeTruthy();
    });

    it('only switches to the the review stage when canMoveToReview() is true', function() {
        workflow.switchStage('sync');
        workflow.switchStage('review');
        expect(workflow.stage).toBe('sync');

        insertSyncedAndCompletedSubtitle(subtitleList);
        workflow.switchStage('review');
        expect(workflow.stage).toBe('review');
    });

    it('moves back to sync if new unsynced subs are added', function() {
        workflow.switchStage('sync');
        insertSyncedAndCompletedSubtitle(subtitleList);
        expect(workflow.canMoveToReview()).toBeTruthy();
        workflow.switchStage('review');
        expect(workflow.stage).toBe('review');

        subtitleList.insertSubtitleBefore(null);
        expect(workflow.stage).toBe('sync');
    });

    it('knows whichs stage are done', function() {
        expect(workflow.stageDone('type')).toBeFalsy();
        expect(workflow.stageDone('sync')).toBeFalsy();
        workflow.switchStage('sync');
        expect(workflow.stageDone('type')).toBeTruthy();
        expect(workflow.stageDone('sync')).toBeFalsy();
        insertSyncedAndCompletedSubtitle(subtitleList);
        workflow.switchStage('review');
        expect(workflow.stageDone('type')).toBeTruthy();
        expect(workflow.stageDone('sync')).toBeTruthy();
    });

    it('starts in the sync stage if we already have subs',
            inject(function(Workflow) {
        subtitleList.insertSubtitleBefore(null);
        workflow = new Workflow(subtitleList);
        expect(workflow.stage).toBe('sync');
    }));
});

describe('WorkflowProgressionController', function() {
    var $scope = null;
    var subtitleList = null;

    beforeEach(function() {
        module('amara.SubtitleEditor.subtitles.models');
        module('amara.SubtitleEditor.workflow');
        module('amara.SubtitleEditor.mocks');
    });

    beforeEach(inject(function ($controller, $rootScope, SubtitleList, Workflow) {
        subtitleList = new SubtitleList();
        $scope = $rootScope;
        $scope.timelineShown = false;
        $scope.toggleTimelineShown = jasmine.createSpy();
        subtitleList.loadXML(null);
        $scope.workingSubtitles = { subtitleList: subtitleList };
        $scope.workflow = new Workflow(subtitleList);
        spyOn($scope, '$emit');
        $controller('WorkflowProgressionController', {
            $scope: $scope,
        });
    }));

    describe('The endorse() method', function() {
        it('normally marks the work complete and saves', function() {
            expect($scope.$emit).not.toHaveBeenCalled();
            $scope.endorse();
            // should send the false paramater to not allow resuming after an
            // endoresment
            expect($scope.$emit).toHaveBeenCalledWith('save', {
                'markComplete': true,
                'allowResume': false
            });
        });

        it('approves a task if we have one', inject(function(EditorData) {
            EditorData.task_id = 123

            expect($scope.$emit).not.toHaveBeenCalled();
            $scope.endorse();
            expect($scope.$emit).toHaveBeenCalledWith('approve-task');
        }));

        it('endorses a collaboration if we have one', inject(function(EditorData) {
            EditorData.collaborationID = 123

            expect($scope.$emit).not.toHaveBeenCalled();
            $scope.endorse();
            expect($scope.$emit).toHaveBeenCalledWith('endorse-collaboration');
        }));
    });

    describe('The click handling', function() {
        it('changes the workflow stage', function() {
            var evt = {
                preventDefault: jasmine.createSpy(),
            };
            $scope.onNextClicked(evt);
            expect($scope.workflow.stage).toBe('sync')
            expect(evt.preventDefault).toHaveBeenCalled();
            insertSyncedAndCompletedSubtitle(subtitleList);
            $scope.onNextClicked(evt);
            expect($scope.workflow.stage).toBe('review')
        });

        it('shows the timeline for the sync step', inject(function(MockEvents) {
            expect($scope.toggleTimelineShown.callCount).toBe(0);
            $scope.onNextClicked(MockEvents.click());
            expect($scope.workflow.stage).toBe('sync')
            expect($scope.toggleTimelineShown.callCount).toBe(1);
        }));

        it('restarts video playback when switching steps', inject(function(MockEvents, VideoPlayer) {
            $scope.onNextClicked(MockEvents.click());
            expect(VideoPlayer.pause).toHaveBeenCalled();
            expect(VideoPlayer.seek).toHaveBeenCalledWith(0);
        }));
    });
});

describe('when up and down sync subtitles', function() {
    var $scope;

    beforeEach(function() {
        module('amara.SubtitleEditor');
        module('amara.SubtitleEditor.subtitles.models');
        module('amara.SubtitleEditor.mocks');
    });

    beforeEach(inject(function($rootScope, $controller, Workflow) {
        $scope = $rootScope;
        $scope.timelineShown = false;
        $controller("AppControllerEvents", {
            $scope: $scope,
        });
        spyOn($scope, '$emit');
    }));

    it('syncs when the timeline is shown', inject(function(MockEvents) {
        $scope.handleAppKeyDown(MockEvents.keydown(40));
        expect($scope.$root.$emit).not.toHaveBeenCalled();
        $scope.handleAppKeyDown(MockEvents.keydown(38));
        expect($scope.$root.$emit).not.toHaveBeenCalled();

        $scope.timelineShown = true;
        $scope.handleAppKeyDown(MockEvents.keydown(40));
        expect($scope.$root.$emit).toHaveBeenCalledWith("sync-next-start-time");
        $scope.handleAppKeyDown(MockEvents.keydown(38));
        expect($scope.$root.$emit).toHaveBeenCalledWith("sync-next-end-time");
    }));
});

describe('when the enter key creates a new subtitle', function() {
    var keyCodeForEnter = 13;
    var subtitleList;
    var $scope;

    beforeEach(function() {
        module('amara.SubtitleEditor.subtitles.controllers');
        module('amara.SubtitleEditor.subtitles.models');
        module('amara.SubtitleEditor.mocks');
    });

    beforeEach(inject(function($rootScope, $controller, CurrentEditManager, SubtitleList) {
        $scope = $rootScope;
        subtitleList = new SubtitleList();
        subtitleList.loadXML(null);
        $scope.workingSubtitles = {
            subtitleList: subtitleList,
        }
        $scope.timelineShown = false;
        $scope.currentEdit = new CurrentEditManager();
        $scope.getSubtitleRepeatItem = function() {
            return null;
        }
        subtitleList.insertSubtitleBefore(null);
        // FIXME: we should mock window, but that's tricky to do.  Especially
        // since we wrap it in jquery.
        $controller('WorkingSubtitlesController', {
            $scope: $scope,
        });
        spyOn(subtitleList, 'insertSubtitleBefore').andCallThrough();
    }));

    it('creates a new subtitle when the timeline is hidden',
            inject(function(MockEvents) {
        $scope.currentEdit.start(subtitleList.subtitles[0]);
        var evt = MockEvents.keydown(keyCodeForEnter);
        $scope.onEditKeydown(evt);
        expect(subtitleList.insertSubtitleBefore).toHaveBeenCalled();
        expect(evt.preventDefault).toHaveBeenCalled();

        $scope.timelineShown = true;
        $scope.onEditKeydown(MockEvents.keydown(keyCodeForEnter));
        expect(subtitleList.insertSubtitleBefore.callCount).toBe(1);
    }));
});

describe('when enter creates a new subtitle', function() {
    var keyCodeForEnter = 13;
    var $scope;
    var subtitleList;
    var MockEvents;

    beforeEach(function() {
        module('amara.SubtitleEditor');
        module('amara.SubtitleEditor.subtitles.models');
        module('amara.SubtitleEditor.mocks');
    });

    beforeEach(inject(function($rootScope, $controller, $injector,
                CurrentEditManager, SubtitleList) {
        MockEvents = $injector.get('MockEvents');
        $scope = $rootScope;
        $scope.timelineShown = false;
        $scope.currentEdit = new CurrentEditManager();
        subtitleList = new SubtitleList();
        subtitleList.loadXML(null);
        $scope.workingSubtitles = { subtitleList: subtitleList };
        $controller("AppControllerEvents", {
            $scope: $scope,
        });
        spyOn(subtitleList, 'insertSubtitleBefore').andCallThrough();
    }));

    it('creates a new subtitle', function() {
        $scope.handleAppKeyDown(MockEvents.keydown(keyCodeForEnter));
        expect(subtitleList.insertSubtitleBefore).toHaveBeenCalled();
    });

    it('calls preventDefault', function() {
        var evt = MockEvents.keydown(keyCodeForEnter);
        $scope.handleAppKeyDown(evt);
        expect(evt.preventDefault).toHaveBeenCalled();
    });

    it('starts editing the new subtitle', function() {
        $scope.handleAppKeyDown(MockEvents.keydown(keyCodeForEnter));
        expect($scope.currentEdit.draft).not.toBe(null);
    });

    it('does not creates a new subtitle if its inside a textarea', function() {
        $scope.handleAppKeyDown(MockEvents.keydown(keyCodeForEnter, {
            'target': {
                'type': 'textarea',
            },
        }));
        expect(subtitleList.insertSubtitleBefore).not.toHaveBeenCalled();
    });

    it('does not creates a new subtitle if the timeline is shown', function() {
        $scope.timelineShown = true;
        $scope.handleAppKeyDown(MockEvents.keydown(keyCodeForEnter));
        expect(subtitleList.insertSubtitleBefore).not.toHaveBeenCalled();
    });
});
