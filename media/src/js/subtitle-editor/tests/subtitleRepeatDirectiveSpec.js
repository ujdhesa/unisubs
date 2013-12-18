describe('Test the subtitle-repeat directive', function() {
    var subtitleList = null;
    var scope = null;
    var elm = null;
    var subtitles = null;

    beforeEach(function() {
        module('amara.SubtitleEditor.subtitles.directives');
        module('amara.SubtitleEditor.subtitles.models');
        module('amara.SubtitleEditor.dom');
    });

    beforeEach(inject(function(SubtitleList) {
        subtitles = [];
        subtitleList = new SubtitleList();
        subtitleList.loadXML(null);
        for(var i = 0; i < 5; i++) {
            var sub = subtitleList.insertSubtitleBefore(null);
            subtitleList.updateSubtitleContent(sub, 'subtitle ' + i);
            subtitleList.updateSubtitleTime(sub, i * 1000, i * 1000 + 500);
            subtitles.push(sub);
        }
        inject(function($rootScope, $compile) {
                elm = angular.element(
                '<div>' +
                '<ul>' +
                '<li subtitle-repeat="subtitleList" ' +
                'bind-to-edit="editingSub" ' +
             'conditional-class="subtitle.isEmpty():empty" ' +
             'edit-keydown="onEditKeyDown">' +
          '<span class="timing">{{ subtitle.startTime }}</span>' +
          '<span class="text">{{ subtitle.content() }}</span>' +
          '<a href="#" class="add" subtitle-click="add">add</a>' +
          '<a href="#" class="remove" subtitle-click="remove">remove</a>' +
          '<a href="#" class="no-subtitle-click">other</a>' +
        '</li>' +
      '</ul>' +
    '</div>');
            scope = $rootScope;
            // Temporary fix until me make it right
            scope.adjustReferenceSize = function() {};
            scope.subtitleList = subtitleList;
            $compile(elm)(scope);
            scope.$digest();
        })

        this.addMatchers({
            'toMatchSubtitle': function(subtitle) {
                var li = this.actual;
                if($('.text', li).html() != subtitle.content()) {
                    return false;
                }
                if($('.timing', li).html() != subtitle.startTime) {
                    return false;
                }
                return true;
            },
        });
    }));

    function childLIs() {
        return $('ul', elm).children();
    }

    it('creates an li for each subtitle', function() {
        expect(childLIs().length).toEqual(5);
    });

    it('interpolates strings', function() {
        lis = childLIs();
        for(var i=0; i < subtitles.length; i++) {
            expect(lis[i]).toMatchSubtitle(subtitles[i]);
        }
    });

    it('adds conditional classes', function() {
        for(var i=0; i < subtitles.length; i++) {
            expect(childLIs().eq(i).hasClass('empty')).toBeFalsy();
        }
        subtitleList.updateSubtitleContent(subtitles[0], '');
        expect(childLIs().eq(0).hasClass('empty')).toBeTruthy();
    });

    it('updates the DOM on changes', function() {
        // test remove
        subtitleList.removeSubtitle(subtitles[0]);
        expect(childLIs().length).toEqual(4);
        expect(childLIs()[0]).toMatchSubtitle(subtitles[1]);
        // test update
        subtitleList.updateSubtitleContent(subtitles[1], 'new content');
        expect(childLIs().length).toEqual(4);
        expect(childLIs()[0]).toMatchSubtitle(subtitles[1]);
        expect(childLIs().length).toEqual(4);
        subtitleList.updateSubtitleTime(subtitles[1], 500, 1500);
        expect(childLIs()[0]).toMatchSubtitle(subtitles[1]);
        // test insert
        var newSub = subtitleList.insertSubtitleBefore(subtitles[1]);
        expect(childLIs().length).toEqual(5);
        expect(childLIs()[0]).toMatchSubtitle(newSub);
        var newSubAtBack = subtitleList.insertSubtitleBefore(null);
        expect(childLIs().length).toEqual(6);
        expect(childLIs()[5]).toMatchSubtitle(newSubAtBack);
    });

    it('handles clicks', function() {
        var li = childLIs()[0];
        var sub = subtitles[0];
        // If there is no click handler, the click event shouldn't cause an
        // exception.
        $('a.add', li).click();
        // Test click handlers
        var clickActions = [];
        scope.onSubtitleClick = function(evt, subtitle, action) {
            expect(subtitle).toBe(sub);
            clickActions.push(action);
        }
        // Test clicks
        $('a.add', li).click();
        expect(clickActions).toEqual(['add']);
        $('a.remove', li).click();
        expect(clickActions).toEqual(['add', 'remove']);
        // Test clicking something without a handler
        $('a.no-subtitle-click', li).click();
        expect(clickActions).toEqual(['add', 'remove']);
    });

    it('adds/removes a textarea based on bind-to-edit', function() {
        scope.editingSub = subtitles[0].draftSubtitle();
        scope.$digest();
        expect($('textarea', childLIs()[0]).length).toEqual(1);
        expect($('textarea', childLIs()[0]).val())
            .toEqual(subtitles[0].markdown);
        scope.editingSub = subtitles[1].draftSubtitle();
        scope.$digest();
        expect($('textarea', childLIs()[0]).length).toEqual(0);
        expect($('textarea', childLIs()[1]).length).toEqual(1);
        expect($('textarea', childLIs()[1]).val())
            .toEqual(subtitles[1].markdown);
        scope.editingSub = null;
        scope.$digest();
        expect($('textarea', childLIs()[1]).length).toEqual(0);
    });

    it('sets the caret position to the end of the text',
            inject(function(DomUtil) {
        spyOn(DomUtil, 'setSelectionRange');
        scope.editingSub = subtitles[0].draftSubtitle();
        scope.$digest();
        var textarea = $('textarea', elm)[0];
        expect(DomUtil.setSelectionRange).toHaveBeenCalledWith(textarea,
            subtitles[0].markdown.length, subtitles[0].markdown.length);

    }));

    it('sets the caret position to initialCaretPos if set',
            inject(function(DomUtil) {
        spyOn(DomUtil, 'setSelectionRange');
        scope.editingSub = subtitles[0].draftSubtitle();
        scope.editingSub.initialCaretPos = 2;
        scope.$digest();
        var textarea = $('textarea', elm)[0];
        expect(DomUtil.setSelectionRange).
            toHaveBeenCalledWith(textarea, 2, 2);
    }));

    it('calls focus on edits', function() {
        spyOn($.fn, 'focus').andCallFake(function() {
            expect(this.length).toEqual(1);
            expect(this[0]).toEqual($('textarea', elm)[0]);
        });
        scope.editingSub = subtitles[0].draftSubtitle();
        scope.$digest();
        expect($.fn.focus.callCount).toEqual(1);
    });

    it('calls autosize on edits', function() {
        spyOn($.fn, 'autosize').andCallFake(function() {
            expect(this.length).toEqual(1);
            expect(this[0]).toEqual($('textarea', elm)[0]);
        });
        scope.editingSub = subtitles[0].draftSubtitle();
        scope.$digest();
        expect($.fn.autosize.callCount).toEqual(1);
    });

    it('adds the edit class based on bind-to-edit', function() {
        scope.editingSub = subtitles[0].draftSubtitle();
        scope.$digest();
        expect(childLIs().eq(0).hasClass('edit')).toBeTruthy();
        scope.editingSub = subtitles[1].draftSubtitle();
        scope.$digest();
        expect(childLIs().eq(0).hasClass('edit')).toBeFalsy();
        expect(childLIs().eq(1).hasClass('edit')).toBeTruthy();
        scope.editingSub = null;
        scope.$digest();
        expect(childLIs().eq(1).hasClass('edit')).toBeFalsy();
    });

    it('updates the bind-to-edit var on keyup', function() {
        scope.editingSub = subtitles[0].draftSubtitle();
        scope.$digest();
        var textarea = $('textarea', childLIs()[0]);
        textarea.val('new content');
        textarea.keyup();
        expect(scope.editingSub.markdown).toEqual('new content');
    });

    it('emits edit-keydown in edit-mode', function() {
        scope.editingSub = subtitles[0].draftSubtitle();
        scope.$digest();
        var textarea = $('textarea', childLIs()[0]);
        scope.onEditKeyDown = function(evt) {
            expect(evt.type).toEqual('keydown');
        };
        var spy = spyOn(scope, 'onEditKeyDown');
        textarea.keydown();
        expect(spy.callCount).toEqual(1);
    });

    it('fetches list items for subtitles', function() {
        expect(scope.getSubtitleRepeatItem(subtitles[0]).get(0)).
            toEqual(childLIs().get(0));
    });


});
