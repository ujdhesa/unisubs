// Amara, universalsubtitles.org
//
// Copyright (C) 2013 Participatory Culture Foundation
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see
// http://www.gnu.org/licenses/agpl-3.0.html.

(function() {

    var module = angular.module('amara.SubtitleEditor.collab', [
        'amara.SubtitleEditor.subtitles.services',
    ]);

    module.controller('CollabController', function($scope, $timeout, EditorData) {

        $scope.endorseDisabled = function() {
            return $scope.workingSubtitles.subtitleList.subtitles.length == 0;
        };

        $scope.approve = function() {
            $scope.$root.$emit('approve-task');
        };
        $scope.endorse = function() {
            $scope.$root.$emit('endorse-collaboration');
        };
        $scope.sendBack = function() {
            $scope.$root.$emit('send-back-task');
        };
        $scope.addNote = function() {
            $scope.collab.saveNote();
        };

        $scope.$root.$on('editing-done', function($event, $editScope) {
            if ($editScope.subtitleList.needsAnyTranscribed()) {
                $scope.error = 'You have empty subtitles.';
            } else {
                $scope.error = null;
            }
        });
    });

    module.factory('CollaborationStorage', function($http, AuthHeaders, EditorData) {
        function getTaskSaveAPIUrl(teamSlug, taskID) {
            return '/api2/partners/teams/' + teamSlug + '/tasks/' +
                taskID + '/';
        };

        function getEndorseAPIUrl(videoId, languageCode) {
            return '/api2/partners/videos/' + videoId +
                '/languages/' + languageCode + '/endorsements/';
        };

        function getCollaborationNotesAPIUrl(videoId, languageCode) {
            return '/api2/partners/videos/' + videoId +
                '/languages/' + languageCode + '/collaboration/notes/';
        };

        return {
            approveTask: function(versionNumber, notes) {

                var url = getTaskSaveAPIUrl(EditorData.team_slug,
                        EditorData.task_id);

                var promise = $http({
                    method: 'PUT',
                    url: url,
                    headers: AuthHeaders.headers(),
                    data:  {
                        complete: true,
                        body: notes,
                        version_number: versionNumber,
                    }
                });

                return promise;

            },
            sendBackTask: function(versionNumber, notes) {

                var url = getTaskSaveAPIUrl(EditorData.team_slug,
                        EditorData.task_id);

                var promise = $http({
                    method: 'PUT',
                    url: url,
                    headers: AuthHeaders.headers(),
                    data:  {
                        complete: true,
                        body: notes,
                        send_back: true,
                        version_number: versionNumber,
                    }
                });

                return promise;

            },
            updateTaskNotes: function(notes) {
                var url = getTaskSaveAPIUrl(EditorData.team_slug,
                        EditorData.task_id);

                var promise = $http({
                    method: 'PUT',
                    url: url,
                    headers: AuthHeaders.headers(),
                    data:  {
                        body: notes,
                    }
                });

                return promise;
            },
            endorseCollaboration: function(videoId, languageCode) {

                var url = getEndorseAPIUrl(videoId, languageCode);
                // To endorse the collaboration we post to the endorsements
                // URL.  We don't need to send any data, the only thing that's
                // important is the user endorsing it and that's already
                // specified by the auth headers.
                var promise = $http({
                    method: 'POST',
                    url: url,
                    headers: AuthHeaders.headers(),
                    data:  {},
                });

                return promise;

            },
            getCollaborationNotes: function(videoId, languageCode) {
                return $http({
                    method: 'GET',
                    url: getCollaborationNotesAPIUrl(videoId, languageCode),
                    headers: AuthHeaders.headers()
                }).then(function(result) {
                    return result.data;
                });
            },
            addCollaborationNote: function(videoId, languageCode, text) {
                return $http({
                    method: 'POST',
                    url: getCollaborationNotesAPIUrl(videoId, languageCode),
                    data: {'text': text},
                    headers: AuthHeaders.headers()
                }).then(function(result) {
                    return result.data;
                });
            },
        };
    });

    /* CollaborationManager manages tasks/collaborations for the entire app
     */
    module.factory('CollaborationManager', function($q, CollaborationStorage, EditorData) {
        function CollaborationManager() {
            this.currentNote = EditorData.savedNotes || "";
            if (EditorData.task_needs_pane) {
                this.enabled = true;
                this.mode = 'tasks';
                this.savedNote = this.currentNote;
            } else if (EditorData.collaboration_id &&
                    EditorData.collaboration_state != 'being-subtitled') {
                this.enabled = true;
                this.mode = 'collab';
                this.collaborators = EditorData.collaborators;
                this.notes = EditorData.collaborationNotes;
            } else {
                this.enabled = false;
                this.mode = null;
            }
            this.videoId = EditorData.video.id;
            this.languageCode = EditorData.editingVersion.languageCode;
        }

        CollaborationManager.prototype.chainPromiseToSaveNote = function(promise) {
            /*
             * This method is used when we have a promise that will update the
             * notes, for example we are approving/rejecting a task.  We
             * return a new promise that will update our note data if the
             * promise succeeeds.
             */
            var that = this;
            return promise.then(function(result) {
                if(that.mode == 'collab') {
                    that.notes.push(result);
                    that.currentNote = '';
                } else {
                    that.savedNote = that.currentNote;
                }
                return result;
            });
        }

        CollaborationManager.prototype.saveNote = function() {
            if(this.noteNeedsSave()) {
                var note = this.currentNote;
                switch(this.mode) {
                    case 'tasks':
                        return this.chainPromiseToSaveNote(
                                CollaborationStorage.updateTaskNotes(note));

                    case 'collab':
                        return this.chainPromiseToSaveNote(
                            CollaborationStorage.addCollaborationNote(this.videoId, this.languageCode, note));
                }
            }
            // Return a dummy promise to make the return value consistent.
            var deferred = $q.defer();
            deferred.resolve();
            return deferred.promise;
        }

        CollaborationManager.prototype.noteNeedsSave = function() {
            if(this.mode == 'tasks') {
                return this.currentNote != this.savedNote;
            } else if(this.mode == 'collab') {
                return this.currentNote != '';
            } else {
                return false;
            }
        }

        CollaborationManager.prototype.approveTask = function(versionNumber) {
            var note = this.currentNote;
            return this.chainPromiseToSaveNote(
                    CollaborationStorage.approveTask(versionNumber, note));

        }

        CollaborationManager.prototype.sendBackTask = function(versionNumber) {
            var note = this.currentNote;
            return this.chainPromiseToSaveNote(
                    CollaborationStorage.sendBackTask(versionNumber, note));
        }

        CollaborationManager.prototype.endorseCollaboration = function() {
            return CollaborationStorage.endorseCollaboration(this.videoId, this.languageCode);
        }

        CollaborationManager.prototype.enableSaveButton = function() {
            return this.mode == 'tasks' && this.noteNeedsSave();
        }

        return CollaborationManager;
    });

}).call(this);
