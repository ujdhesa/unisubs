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

var angular = angular || null;
var LOCK_EXPIRATION = 25;
var USER_IDLE_MINUTES = 15;

(function() {

    var module = angular.module('amara.SubtitleEditor.subtitles.directives', []);

    module.directive('subtitleEditor', function() {
        return function link(scope, elm, attrs) {
            // For some reason using ng-keydown at the HTML tag doesn't work.
            // Use jquery instead.
            $(document).keydown(function(evt) {
                scope.$apply(function(scope) {
                    scope.handleAppKeyDown(evt);
                });
            });
        };
    });
    module.directive('workingSubtitles', function() {
        return function link(scope, elem, attrs) {
            var startHelper = $('div.sync-help.begin', elem);
            var endHelper = $('div.sync-help.end', elem);
            var infoTray = $('div.info-tray', elem);
            var subtitleList = $('.subtitles ul', elem);
            var currentArrow = undefined;
            var wrapper = $(elem);

            function getSubtitleTop(index) {
                var li = $('li', subtitleList).eq(index);
                var top = li.offset().top - wrapper.offset().top;
                if(top < 0 || top + startHelper.height() >= wrapper.height()) {
                    return null;
                }
                return top;
            }

            var lastSyncStartIndex = null;
            var lastSyncEndIndex = null;

            scope.positionSyncHelpers = function(startIndex, endIndex) {
                if(!scope.timelineShown) {
                    startHelper.hide();
                    endHelper.hide();
                    return;
                }
                if(startIndex === undefined) {
                    startIndex = lastSyncStartIndex;
                }
                if(endIndex === undefined) {
                    endIndex = lastSyncEndIndex;
                }
                var startTop = null;
                var endTop = null;
                if(startIndex !== null) {
                    startTop = getSubtitleTop(startIndex);
                }
                if(endIndex !== null) {
                    endTop = getSubtitleTop(endIndex);
                }
                if(startTop !== null) {
                    startHelper.css('top', startTop + 'px');
                    startHelper.show();
                } else {
                    startHelper.hide();
                }
                if(endTop !== null) {
                    endHelper.css('top', endTop + 'px');
                    endHelper.show();
                } else {
                    endHelper.hide();
                }
                lastSyncStartIndex = startIndex;
                lastSyncEndIndex = endIndex;
            }

            scope.positionInfoTray = function() {
                var BUFFER = 22;
                var subtitle = scope.currentEdit.storedSubtitle();
                if(subtitle === null) {
                    infoTray.hide();
                    return;
                }
                var li = scope.getSubtitleRepeatItem(subtitle);
                if(li) {
                    currentArrow = li.find(".arrow");
                    var top = li.offset().top - wrapper.offset().top;
                    var bottom = top + li.height();

                    var infoTrayBottom = infoTray.height() + top;
                    var willTrim = wrapper.height() < infoTrayBottom;
                    if (willTrim) {
                        var adjustedTop = top - (infoTrayBottom - wrapper.height());
                        if (adjustedTop + BUFFER < bottom && adjustedTop - BUFFER > top - infoTray.height()) {
                            top = adjustedTop;
                        }
                    }
                    if(top + BUFFER >= 0 && top + BUFFER < wrapper.height()) {
                        infoTray.css('top', top + 'px');
                        infoTray.show();
                        currentArrow.show();
                    } else {
                        infoTray.hide();
                        currentArrow.hide();
                    }
                }
            }

            scope.$watch("currentEdit.draft", function() {
                if (currentArrow) {
                    currentArrow.hide(); // Kinda hate this, i think it would be cleaner to give each line its own controller
                }
                scope.positionInfoTray();
            });

            scope.$watch("timelineShown", function() {
                scope.positionSyncHelpers();
            });

            scope.$root.$on('working-subtitles-scrolled', function() {
                scope.positionSyncHelpers();
                scope.positionInfoTray();
            });
        };
    });

    module.directive('subtitleList', function($window) {
        var window = $($window);
	var scrollingPrevious = [];
	$('div.subtitles').each(function(index) {
	    scrollingPrevious[index] = $(this).scrollTop();
	});
        return function link(scope, elem, attrs) {
            var scroller = $(elem).parent();
            var isWorkingSet = (attrs.subtitleList == "working-subtitle-set");
            // Handle scroll.
            scroller.scroll(function() {
                // If scroll sync is locked.
                if (scope.scrollingSynced) {
                    var delta = 0;
                    var index_scrolled = -1;
                    $('div.subtitles').each(function(index) {
                        var newScrollTop = $(this).scrollTop();
                        if (newScrollTop != scrollingPrevious[index]) {
                            delta = newScrollTop - scrollingPrevious[index];
                            index_scrolled = index;
                        }
                    });
                    if (index_scrolled != -1) {
                        $('div.subtitles').each(function(index) {
                            if (index != index_scrolled) {
                                var newScrollTop = $(this).scrollTop() + delta;
                                $(this).scrollTop(newScrollTop);
                                var updatedScrollTop = $(this).scrollTop();
                                if ((updatedScrollTop != newScrollTop) && (updatedScrollTop != 0)) {
                                    $(this).children().last().height($(this).children().last().height() + newScrollTop - updatedScrollTop);
                                    $(this).scrollTop(newScrollTop);
                                }
                            }
                        });
                    }
                }
		$('div.subtitles').each(function(index) {
		    scrollingPrevious[index] = $(this).scrollTop();
		});

                if(isWorkingSet) {
                    scope.$root.$emit("working-subtitles-scrolled");
                }
            });

            function resizeScroller() {
                if (scope.timelineShown) {
                    var scrollerTop = 398;
                } else {
                    var scrollerTop = 327;
                }
                scroller.height(window.height() - scrollerTop);
            }

            scope.$watch('timelineShown', resizeScroller);
            window.on('resize', resizeScroller);
            resizeScroller();

            if (isWorkingSet) {
                scope.$root.$on('scroll-to-subtitle', function(evt, subtitle) {
                    if(scope.currentEdit.inProgress()) {
                        return;
                    }
                    var target = scope.getSubtitleRepeatItem(subtitle);
                    var prev = target.prev();
                    if(prev.length > 0) {
                        target = prev;
                    }
                    if(target) {
                        scroller.scrollTop(scroller.scrollTop() +
                                target.offset().top - scroller.offset().top);
                    }
                });
            }
        }
    });

    module.directive('subtitleRepeat', function($interpolate, $parse, DomUtil) {
        /* Specialized repeat directive to work with subtitleList
         *
         * Because we need to deal potentially thousands of subtitles,
         * ng-repeat is not ideal.  subtitleRepeat does a couple things to
         * speed up performance:
         *
         *   - it hooks up to the change callback of subtitleList to calculate
         *   changes quickly.
         *
         *   - it doesn't create a child scope for each subtitle.  This means
         *   that it doesn't support the full angular templating language.
         *   However simple string interpolation is supported.
         */
        return function link($scope, elm, attrs) {
            function createNodeForSubtitle(subtitle) {
                var context = {
                    subtitle: subtitle
                };
                for(var i=0; i < updateFuncs.length; i++) {
                    updateFuncs[i](context);
                }
                if(attrs.currentSubtitleClass) {
                    if($scope.timeline.shownSubtitle === subtitle) {
                        elm.addClass(attrs.currentSubtitleClass);
                    } else {
                        elm.removeClass(attrs.currentSubtitleClass);
                    }
                }
                var rv = elm.clone();
                subtitleMap[subtitle.id] = rv;
                rv.data('subtitle', subtitle);
                return rv;
            }

            function interpolateFunc(node, func) {
                return function(context) {
                    node.textContent = func(context);
                }
            }

            function conditionalClassFunc(expr, className) {
                var condition = $parse(expr);
                return function(context) {
                    if(condition(context)) {
                        elm.addClass(className);
                    } else {
                        elm.removeClass(className);
                    }
                }
            }

            function findInterpolations() {
                // Jquery doesn't have a great way of finding text nodes, use
                // the plain DOM API instead
                var toSearch = [elm[0]];
                var rv = [];
                while(toSearch.length > 0) {
                    var node = toSearch.pop();
                    if(node.nodeType == 3) {
                        // Text node
                        var func = $interpolate(node.textContent, true);
                        if(func != null) {
                            updateFuncs.push(interpolateFunc(node, func));
                        }
                    } else {
                        toSearch.push.apply(toSearch, node.childNodes);
                    }
                }
                return rv;
            }

            function findSubtitleClickValue(node) {
                // Find the value of the subtitle-click attribute, starting
                // with node and moving up the DOM tree
                var parentNode = parent[0];
                while(node && node != parentNode) {
                    if(node.hasAttribute("subtitle-click")) {
                        return node.getAttribute("subtitle-click");
                    } else {
                        node = node.parentNode;
                    }
                }
                return null;
            }
            function findSubtitleData(node) {
                // Find the value of the subtitle-click attribute, starting
                // with node and moving up the DOM tree
                var parentNode = parent[0];
                while(node && node != parent) {
                    var subtitle = $(node).data('subtitle');
                    if(subtitle) {
                        return subtitle;
                    } else {
                        node = node.parentNode;
                    }
                }
                return null;
            }

            function updateSubtitle(subtitle) {
                var node = subtitleMap[subtitle.id];
                node.replaceWith(createNodeForSubtitle(subtitle));
            }

            function onChange(change) {
                var subtitle = change.subtitle;
                switch(change.type) {
                    case 'remove':
                        var node = subtitleMap[subtitle.id];
                        node.remove();
                        delete subtitleMap[subtitle.id];
                        break;
                    case 'update':
                        updateSubtitle(subtitle);
                        break;
                    case 'insert':
                        if(change.before !== null) {
                            var node = subtitleMap[change.before.id];
                            node.before(createNodeForSubtitle(subtitle));
                        } else {
                            parent.append(createNodeForSubtitle(subtitle));
                        }
                        break;
                    case 'reload':
                        reloadSubtitles();
                }
            }

            function startEditOn(draft) {
                var li = subtitleMap[draft.storedSubtitle.id];
                li.addClass('edit');
                var textarea = $('<textarea class="subtitle-edit" />');
                textarea.val(draft.markdown);
                li.append(textarea);
                textarea.autosize();
                textarea.focus();
                if(draft.initialCaretPos === undefined) {
                    var caretPos = draft.markdown.length;
                } else {
                    var caretPos = draft.initialCaretPos;
                }
                DomUtil.setSelectionRange(textarea[0], caretPos, caretPos);
                textarea.on('keyup', function(evt) {
                    $scope.$apply(function() {
                        draft.markdown = textarea.val();
                    });
                });
                if(attrs.editKeydown) {
                    textarea.on('keydown', function(evt) {
                        $scope.$apply(function() {
                            var handler = $scope[attrs.editKeydown];
                            handler(evt);
                        });
                    });
                }
            }
            function stopEditOn(draft) {
                var li = subtitleMap[draft.storedSubtitle.id];
                if(li) {
                    li.removeClass('edit');
                    $('textarea.subtitle-edit', li).remove();
                }
            }

            function reloadSubtitles() {
                parent.empty();
                subtitleMap = {}
                for(var i=0; i < subtitleList.length(); i++) {
                    var subtitle = subtitleList.subtitles[i];
                    parent.append(createNodeForSubtitle(subtitle));
                }
                // Probably not great to have it here
                // We need to adjust the sizes to look nicer while scrolling
                $scope.adjustReferenceSize();
            }
            $scope.getSubtitleRepeatItem = function(subtitle) {
                var rv = subtitleMap[subtitle.id];
                if(rv !== undefined) {
                    return rv;
                } else {
                    return null;
                }
            }

            // On our first pass we remove the element from its parent, then
            // add a copy for each subtitle
            var subtitleList = $scope.$eval(attrs.subtitleRepeat);
            var parent = elm.parent();
            var updateFuncs = []
            findInterpolations();
            // Map subtitle ID to node for that subtitle
            var subtitleMap = {};

            if(attrs.conditionalClass) {
		attrs.conditionalClass.split(',').forEach(function(pattern) {
		    var split = pattern.split(":", 2);
                    updateFuncs.push(conditionalClassFunc(split[0], split[1]));
		});
            }

            elm.remove();
            reloadSubtitles();

            subtitleList.addChangeCallback(onChange);

            if(attrs.bindToEdit) {
                $scope.$watch(attrs.bindToEdit, function(newValue, oldValue) {
                    if(oldValue) {
                        stopEditOn(oldValue);
                    }
                    if(newValue) {
                        startEditOn(newValue);
                    }
                });
            }
            // We connect to the click event of the parent element.  If we
            // have many subtitles, creating a handler for each <li> isn't
            // good.
            parent.on('click', function(evt) {
                if(!$scope.onSubtitleClick) {
                    return;
                }
                var action = findSubtitleClickValue(evt.target);
                var subtitle = findSubtitleData(evt.target);
                if(action !== null) {
                    $scope.$apply(function() {
                        $scope.onSubtitleClick(evt, subtitle, action);
                    });
                }
            });

            if(attrs.currentSubtitleClass) {
                $scope.$watch('timeline.shownSubtitle', function(newSub, oldSub) {
                    if(newSub) {
                        updateSubtitle(newSub);
                    }
                    if(oldSub) {
                        updateSubtitle(oldSub);
                    }
                });
            }
        }
    });

    module.directive('languageSelector', function(SubtitleStorage) {
        return {
            compile: function compile(elm, attrs, transclude) {
                return {
                    post: function post(scope, elm, attrs) {
                        /* For some reason, if we use ng-select angular
                         * creates an extra option because it thinks
                         * scope.versionNumber is an invalid value for the
                         * options, even though it isn't.  I think it has to
                         * do with the fact that we manually create options
                         * with ng-repeat.  In any case, we handle the
                         * select ourself.
                         */
                        $('select.version-select', elm).change(function(evt) {
                            scope.versionNumber = this.value;
                            scope.$digest();
                        });
                        scope.setInitialDisplayLanguage(SubtitleStorage.getLanguages());
                    }
                };
            }
        };
    });
})();
