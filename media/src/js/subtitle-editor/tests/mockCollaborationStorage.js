(function() {

    var module = angular.module('amara.SubtitleEditor.mocks.CollaborationStorage', []);

    module.factory('CollaborationStorage', function($q, $rootScope) {
        // List of functions that return a deferred promise.
        var deferredFunctionsToMock = [
            'updateTaskNotes',
            'approveTask',
            'sendBackTask',
            'addCollaborationNote',
            'endorseCollaboration',
            'removeEndorsement',
        ];

        var deferreds = {};

        var mockCollaborationStorage = {
            resolveDeferred: function(name, result) {
                deferreds[name].resolve(result);
                $rootScope.$apply();
            }
        }

        _.each(deferredFunctionsToMock, function(name) {
            var deferred = $q.defer();
            deferreds[name] = deferred;
            mockCollaborationStorage[name] = function() {
                return deferred.promise;
            }
            spyOn(mockCollaborationStorage, name).andCallThrough();
        });

        return mockCollaborationStorage;
    });
}).call(this);
