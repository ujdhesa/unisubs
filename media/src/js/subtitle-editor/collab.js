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

    var module = angular.module('amara.SubtitleEditor.collab', []);

    module.controller('CollabController', function($scope, $timeout, EditorData) {

        // Store the state of the current collaboration/task
        $scope.collab = {
            enabled: false,
            taskMode: false,
            currentNote: EditorData.savedNotes || "",
            collaborators: EditorData.collaborators || []
        };

        // If this is a task, set up the proper panels.
        if (EditorData.task_needs_pane) {
            $scope.collab.enabled = true;
            $scope.collab.taskMode = true;
        }
        else if (EditorData.collaboration_id &&
                EditorData.collaboration_state != 'being-subtitled') {
            $scope.collab.enabled = true;
        }

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
        $scope.notesChanged = function() {
            $scope.$root.$emit('notes-changed');
        };

        $scope.$root.$on('editing-done', function($event, $editScope) {
            if ($editScope.subtitleList.needsAnyTranscribed()) {
                $scope.error = 'You have empty subtitles.';
            } else {
                $scope.error = null;
            }
        });
    });
}).call(this);
