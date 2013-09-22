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

(function() {
    /*
     * amara.subtitles.models
     *
     * Define model classes that we use for subtitles
     */

    var module = angular.module('amara.SubtitleEditor.subtitles.models', []);

    function emptyDFXP() {
        /* Get a DFXP string for an empty subtitle set */
        return '<tt xmlns="http://www.w3.org/ns/ttml" xmlns:tts="http://www.w3.org/ns/ttml#styling" xml:lang="en">\
        <head>\
            <metadata xmlns:ttm="http://www.w3.org/ns/ttml#metadata">\
                <ttm:title/>\
                <ttm:description/>\
                <ttm:copyright/>\
            </metadata>\
            <styling xmlns:tts="http://www.w3.org/ns/ttml#styling">\
                <style xml:id="amara-style" tts:color="white" tts:fontFamily="proportionalSansSerif" tts:fontSize="18px" tts:textAlign="center"/>\
            </styling>\
            <layout xmlns:tts="http://www.w3.org/ns/ttml#styling">\
                <region xml:id="amara-subtitle-area" style="amara-style" tts:extent="560px 62px" tts:padding="5px 3px" tts:backgroundColor="black" tts:displayAlign="after"/>\
            </layout>\
        </head>\
        <body region="amara-subtitle-area">\
            <div></div>\
        </body>\
    </tt>';
    };

    function Subtitle(startTime, endTime, markdown) {
        /* Represents a subtitle in our system
         *
         * Subtitle has the following properties:
         *   - startTime -- start time in seconds
         *   - endTime -- end time in seconds
         *   - markdown -- subtitle content in our markdown-style format
         */
        this.startTime = startTime;
        this.endTime = endTime;
        this.markdown = markdown;
    }

    Subtitle.prototype.duration = function() {
        if(this.isSynced()) {
            return this.endTime - this.startTime;
        } else {
            return -1;
        }
    }

    Subtitle.prototype.content = function() {
        /* Get the content of this subtitle as HTML */
        return dfxp.markdownToHTML(this.markdown);
    }

    Subtitle.prototype.isEmpty = function() {
        return this.markdown == '';
    }

    Subtitle.prototype.characterCount = function() {
        return dfxp.markdownToPlaintext(this.markdown).length;
    }

    Subtitle.prototype.characterRate = function() {
        if(this.isSynced()) {
            return (this.characterCount() * 1000 / this.duration()).toFixed(1);
        } else {
            return "0.0";
        }
    }

    Subtitle.prototype.lineCount = function() {
        return this.markdown.split("\n").length;
    }

    Subtitle.prototype.characterCountPerLine = function() {
        var lines = this.markdown.split("\n");
        var counts = [];
        for(var i = 0; i < lines.length; i++) {
            counts.push(dfxp.markdownToPlaintext(lines[i]).length);
        }
        return counts;
        
    }

    Subtitle.prototype.isSynced = function() {
        return this.startTime >= 0 && this.endTime >= 0;
    }

    Subtitle.prototype.isAt = function(time) {
        return this.isSynced() && this.startTime <= time && this.endTime > time;
    }

    Subtitle.prototype.startTimeSeconds = function() {
        if(this.startTime >= 0) {
            return this.startTime / 1000;
        } else {
            return -1;
        }
    }

    Subtitle.prototype.endTimeSeconds = function() {
        if(this.endTime >= 0) {
            return this.endTime / 1000;
        } else {
            return -1;
        }
    }

    function StoredSubtitle(parser, node, id) {
        /* Subtitle stored in a SubtitleList
         *
         * You should never change the proporties on a stored subtitle directly.
         * Instead use the updateSubtitleContent() and updateSubtitleTime()
         * methods of SubtitleList.
         *
         * If you want a subtitle object that you can change the times/content
         * without saving them to the DFXP store, use the draftSubtitle() method
         * to get a DraftSubtitle.
         * */
        Subtitle.call(this, parser.startTime(node), parser.endTime(node),
                $(node).text().trim());
        this.node = node;
        this.id = id;
    }

    StoredSubtitle.prototype = Object.create(Subtitle.prototype);
    StoredSubtitle.prototype.draftSubtitle = function() {
        return new DraftSubtitle(this);
    }
    StoredSubtitle.prototype.isDraft = false;

    function DraftSubtitle(storedSubtitle) {
        /* Subtitle that we are currently changing */
        Subtitle.call(this, storedSubtitle.startTime, storedSubtitle.endTime,
                storedSubtitle.markdown);
        this.storedSubtitle = storedSubtitle;
    }

    DraftSubtitle.prototype = Object.create(Subtitle.prototype);
    DraftSubtitle.prototype.isDraft = true;

    var History = function(params) {
	/*
	 * History keeps track of operations
	 * in a circular buffer manner, keeping
	 * track of available number of possible
	 * redo and undo operations
	 *
	 */
	this.history = [];
	this.historyLength = params.historyLength || 10;
	this.numUndo = 0;
	this.numRedo = 0;
	this.currIndex = 0;
    };

    History.prototype.append = function(changeObj) {
	/*
	 * Appends an operation to the history, this resets
	 * possible redos
	 */
	this.history[this.currIndex] = changeObj;
	this.currIndex = (this.currIndex + 1) % this.historyLength;
	this.numUndo = Math.min(this.numUndo + 1, this.historyLength);
	this.numRedo = 0;
    };

    History.prototype.reset = function() {
	this.numUndo = 0;
	this.numRedo = 0;
	this.currIndex = 0;
    }

    History.prototype.hasRedo = function() {
	return this.numRedo > 0;
    };

    History.prototype.hasUndo = function() {
	return this.numUndo > 0;
    };

    History.prototype.getUndo = function() {
	/*
	 * Retrieves the operation for an undo
	 * and updates the history accordingly
	 */
	if (this.hasUndo()) {
	    var newIndex = this.currIndex - 1;
	    if (newIndex == -1) newIndex = this.historyLength - 1;
	    var output = this.history[newIndex];
	    this.currIndex = newIndex;
	    this.numUndo = Math.max(0, this.numUndo - 1);
	    this.numRedo++;
	    return output;
	} else {
	    return null;
	}
    };
    
    History.prototype.getRedo = function() {
	/*
	 * Retrieves the operation for a redo
	 * and updates the history accordingly
	 */
	if (this.hasRedo()) {
	    var output = this.history[this.currIndex];
	    this.currIndex = (this.currIndex + 1) % this.historyLength;
	    this.numUndo = Math.min(this.numUndo + 1, this.historyLength);
	    this.numRedo--;
	    return output;
	} else
	    return null;
    };

    var SubtitleList = function() {
        /*
         * Manages a list of subtitles.
         *
         * For functions that return subtitle items, each item is a dict with the
         * following properties:
         *   - startTime -- start time in seconds
         *   - endTime -- end time in seconds
         *   - content -- string of html for the subtitle content
         *   - node -- DOM node from the DFXP XML
         *
         */

        this.parser = new AmaraDFXPParser();
	this.history = new History({});
        this.idCounter = 0;
        this.subtitles = [];
        this.syncedCount = 0;
        this.changeCallbacks = [];
    }

    SubtitleList.prototype.canUndo = function() {
	return this.history.hasUndo();
    }

    SubtitleList.prototype.undo = function() {
	/*
	 * To undo, we retrieve an operation from the history
	 * and do the inverted operation
	 *
	 */
	if(this.canUndo()) {
	    var changeObj = this.history.getUndo();
	    var pos = changeObj.pos;
	    switch(changeObj.type) {
	    case "update":
		var newObj = {};
		changeObj.hasOwnProperty('fromContent') &&
		    (newObj.content = changeObj.fromContent);
		changeObj.hasOwnProperty('fromStartTime') &&
		    (newObj.startTime = changeObj.fromStartTime);
		changeObj.hasOwnProperty('fromEndTime') &&
		    (newObj.endTime = changeObj.fromEndTime);
		this._updateSubtitleByPos(pos, newObj);
		break;
	    case "insert":
		var newObj = {};
		changeObj.hasOwnProperty('previousTiming') &&
		    (newObj.previousTiming = changeObj.previousTiming);
		this._removeSubtitleByPos(pos, newObj);
		break;
	    case "remove":
		var newObj = {};
		changeObj.hasOwnProperty('content') &&
		    (newObj.content = changeObj.content);
		changeObj.hasOwnProperty('startTime') &&
		    (newObj.startTime = changeObj.startTime);
		changeObj.hasOwnProperty('endTime') &&
		    (newObj.endTime = changeObj.endTime);
		this._insertSubtitleByPos(pos, newObj);
		break;
	    }
	}
	return this;
    }

    SubtitleList.prototype.canRedo = function() {
	return this.history.hasRedo();
    }

    SubtitleList.prototype.redo = function() {
	/*
	 * To redo, we get an operation from the history
	 * and... redo it
	 *
	 */
	if(this.canRedo()) {
	    var changeObj = this.history.getRedo();
	    var pos = changeObj.pos;
	    switch(changeObj.type) {
	    case "update":
		var newObj = {};
		changeObj.hasOwnProperty('toContent') &&
		    (newObj.content = changeObj.toContent);
		changeObj.hasOwnProperty('toStartTime') &&
		    (newObj.startTime = changeObj.toStartTime);
		changeObj.hasOwnProperty('toEndTime') &&
		    (newObj.endTime = changeObj.toEndTime);
		this._updateSubtitleByPos(pos, newObj);
		break;
	    case "remove":
		var newObj = {};
		this._removeSubtitleByPos(pos, newObj);
		break;
	    case "insert":
		var newObj = {};
		changeObj.hasOwnProperty('content') &&
		    (newObj.content = changeObj.content);
		changeObj.hasOwnProperty('startTime') &&
		    (newObj.startTime = changeObj.startTime);
		changeObj.hasOwnProperty('endTime') &&
		    (newObj.endTime = changeObj.endTime);
		this._insertSubtitleByPos(pos, newObj);
		break;
	    }
	}
	return this;
    }

    SubtitleList.prototype.contentForMarkdown = function(markdown) {
        return dfxp.markdownToHTML(markdown);
    }

    SubtitleList.prototype.loadXML = function(subtitlesXML) {
        if(subtitlesXML === null) {
            subtitlesXML = emptyDFXP();
        }
        this.parser.init(subtitlesXML);
        var syncedSubs = [];
        var unsyncedSubs = [];
        // Needed because each() changes the value of this
        var self = this;
        this.parser.getSubtitles().each(function(index, node) {
            var subtitle = self.makeItem(node);
            if(subtitle.isSynced()) {
                syncedSubs.push(subtitle);
            } else {
                unsyncedSubs.push(subtitle);
            }
        });
        syncedSubs.sort(function(s1, s2) {
            return s1.startTime - s2.startTime;
        });
        this.syncedCount = syncedSubs.length;
        // Start with synced subs to the list
        this.subtitles = syncedSubs;
        // append all unsynced subs to the list
        this.subtitles.push.apply(this.subtitles, unsyncedSubs);
        this.emitChange('reload', null);
    }

    SubtitleList.prototype.addSubtitlesFromBaseLanguage = function(xml) {
        /*
         * Used when we are translating from one language to another.
         * It loads the latest subtitles for xml and inserts blank subtitles
         * with the same timings into our subtitle list.
         */
        var baseLanguageParser = new AmaraDFXPParser();
        baseLanguageParser.init(xml);
        var timings = [];
        baseLanguageParser.getSubtitles().each(function(index, node) {
            startTime = baseLanguageParser.startTime(node);
            endTime = baseLanguageParser.endTime(node);
            if(startTime >= 0 && endTime >= 0) {
                timings.push({
                    'startTime': startTime,
                    'endTime': endTime,
                });
            }
        });
        timings.sort(function(s1, s2) {
            return s1.startTime - s2.startTime;
        });
        var that = this;
        _.forEach(timings, function(timing) {
            var node = that.parser.addSubtitle(null, {
                begin: timing.startTime,
                end: timing.endTime,
            });
            that.subtitles.push(that.makeItem(node));
            that.syncedCount++;
        });
    }

    SubtitleList.prototype.addChangeCallback = function(callback) {
        this.changeCallbacks.push(callback);
    }

    SubtitleList.prototype.removeChangeCallback = function(callback) {
        var pos = this.changeCallbacks.indexOf(callback);
        if(pos >= 0) {
            this.changeCallbacks.splice(pos, 1);
        }
    }

    SubtitleList.prototype.emitChange = function(type, subtitle, extraProps) {
	/*
	 * Used to emit callbacks and append items to the history
	 *
	 */
        var changeObj = { type: type, subtitle: subtitle };
	// We keep two objects with data just to keep the exact
	// same objects passed to callbacks. It's probably not
	// necessary but helps tests pass!
        var historyObj = { type: type, subtitle: subtitle };
	var updateHistory = true;
        if(extraProps) {
            for(key in extraProps) {
		if (key == 'updateHistory')
		    updateHistory = extraProps[key];
                historyObj[key] = extraProps[key];
		if(['type', 'subtitle', 'before'].indexOf(key) > -1)
                    changeObj[key] = extraProps[key];
            }
        }
	if(updateHistory) {
	    if (["remove", "update", "insert"].indexOf(type) > -1)
		this.history.append(historyObj);
	    // Reloading invalidates the history
	    if (["reload"].indexOf(type) > -1)
		this.history.reset();
	}
        for(var i=0; i < this.changeCallbacks.length; i++) {
            this.changeCallbacks[i](changeObj);
        }
    }

    SubtitleList.prototype.makeItem = function(node) {
        var idKey = (this.idCounter++).toString(16);

        return new StoredSubtitle(this.parser, node, idKey);
    }

    SubtitleList.prototype.length = function() {
        return this.subtitles.length;
    }

    SubtitleList.prototype.needsAnyTranscribed = function() {
        for(var i=0; i < this.length(); i++) {
            if(this.subtitles[i].markdown == '') {
                return true;
            }
        }
        return false;
    }

    SubtitleList.prototype.needsAnySynced = function() {
        return this.syncedCount < this.length();
    }

    SubtitleList.prototype.toXMLString = function() {
        return this.parser.xmlToString(true, true);
    }

    SubtitleList.prototype.getIndex = function(subtitle) {
        // Maybe a binary search would be faster, but I think Array.indexOf should
        // be pretty optimized on most browsers.
        return this.subtitles.indexOf(subtitle);
    }

    SubtitleList.prototype.nextSubtitle = function(subtitle) {
        if(subtitle === this.subtitles[this.length() - 1]) {
            return null;
        } else {
            return this.subtitles[this.getIndex(subtitle) + 1];
        }
    }

    SubtitleList.prototype.prevSubtitle = function(subtitle) {
        if(subtitle === this.subtitles[0]) {
            return null;
        } else {
            return this.subtitles[this.getIndex(subtitle) - 1];
        }
    }

    SubtitleList.prototype._updateSubtitleTime = function(subtitle, startTime, endTime) {
        var wasSynced = subtitle.isSynced();
        if(subtitle.startTime != startTime) {
            this.parser.startTime(subtitle.node, startTime);
            subtitle.startTime = startTime;
        }
        if(subtitle.endTime != endTime) {
            this.parser.endTime(subtitle.node, endTime);
            subtitle.endTime = endTime;
        }
        if(subtitle.isSynced() && !wasSynced) {
            this.syncedCount++;
        }
    }

    SubtitleList.prototype.updateSubtitleTime = function(subtitle, startTime, endTime) {
	var changeObj = {
	    pos: this.getIndex(subtitle),
	    fromStartTime: subtitle.startTime,
	    fromEndTime: subtitle.endTime,
	    toStartTime: startTime,
	    toEndTime: endTime
	};
        this._updateSubtitleTime(subtitle, startTime, endTime);
        this.emitChange('update', subtitle, changeObj);
    }

    SubtitleList.prototype._updateSubtitleContent = function(subtitle, content) {
        /* Update subtilte content
         *
         * content is a string in our markdown-style format.
         */
        this.parser.content(subtitle.node, content);
        subtitle.markdown = content;
    }

    SubtitleList.prototype._updateSubtitleByPos = function(pos, changeObj) {
	changeObj.startTime && changeObj.endTime &&
	    (this._updateSubtitleTime(this.subtitles[pos],
						changeObj.startTime,
						changeObj.endTime));
	changeObj.hasOwnProperty('content') && (this._updateSubtitleContent(this.subtitles[pos],
								    changeObj.content));
        this.emitChange('update', this.subtitles[pos], {'updateHistory': false});
    }

    SubtitleList.prototype.updateSubtitleContent = function(subtitle, content) {
	var changeObj = {
	    pos: this.getIndex(subtitle),
	    fromContent: subtitle.content(),
	    toContent: content
	};
        this._updateSubtitleContent(subtitle, content);
        this.emitChange('update', subtitle, changeObj);
    }

    SubtitleList.prototype._insertSubtitleByPos = function(pos, changeObj) {
        if(pos > 0) {
            var after = this.subtitles[pos-1].node;
        } else {
            var after = -1;
        }
	var otherSubtitle = (pos == this.subtitles.length - 1) ? null : this.subtitles[pos+1];
        var node = this.parser.addSubtitle(after, {begin: changeObj.startTime, end: changeObj.endTime});
        var subtitle = this.makeItem(node);
	if (changeObj.hasOwnProperty('content'))
	    this._updateSubtitleContent(subtitle, changeObj.content);
	if (pos < this.subtitles.length) {
            this.subtitles.splice(pos, 0, subtitle);
        } else {
            this.subtitles.push(subtitle);
        }
        if(subtitle.isSynced()) {
            this.syncedCount++;
        }
        this.emitChange('insert', subtitle, { 'before': otherSubtitle, 'updateHistory': false});
    }

    SubtitleList.prototype.insertSubtitleBefore = function(otherSubtitle) {
        if(otherSubtitle !== null) {
            var pos = this.getIndex(otherSubtitle);
        } else {
            var pos = this.subtitles.length;
        }
        // We insert the subtitle before the reference point, but AmaraDFXPParser
        // wants to insert it after, so we need to adjust things a bit.
        if(pos > 0) {
            var after = this.subtitles[pos-1].node;
        } else {
            var after = -1;
        }
	var changeObj = {
	    before: otherSubtitle,
	    pos: pos
	};
	var previousTiming = {};
        if(otherSubtitle && otherSubtitle.isSynced()) {
            // If we are inserting between 2 synced subtitles, then we can set the
            // time
            if(pos > 0) {
                // Inserting a subtitle between two others.  Make it so each
                // subtitle takes up 1/3 of the time available
                var firstSubtitle = this.prevSubtitle(otherSubtitle);
                var totalTime = otherSubtitle.endTime - firstSubtitle.startTime;
                var durationSplit = Math.floor(totalTime / 3);
                var startTime = firstSubtitle.startTime + durationSplit;
		previousTiming.firstSubtitleStartTime = firstSubtitle.startTime;
                var endTime = startTime + durationSplit;
		changeObj.startTime = startTime;
		changeObj.endTime = endTime;
                this._updateSubtitleTime(firstSubtitle, firstSubtitle.startTime,
                        startTime);
                this._updateSubtitleTime(otherSubtitle, endTime, otherSubtitle.endTime);
            } else {
                // Inserting a subtitle as the start of the list.  position the
                // subtitle to start at time=0 and take up half the space
                // available to the two subtitles
                var startTime = 0;
                var endTime = Math.floor(otherSubtitle.endTime / 2);
		changeObj.startTime = startTime;
		changeObj.endTime = endTime;
		previousTiming.otherSubtitleEndTime = otherSubtitle.endTime;
                this._updateSubtitleTime(otherSubtitle, endTime, otherSubtitle.endTime);
            }
            attrs = {
                begin: startTime,
                end: endTime,
            }
        } else {
            attrs = {}
        }
        var node = this.parser.addSubtitle(after, attrs);
        var subtitle = this.makeItem(node);
        if(otherSubtitle != null) {
            this.subtitles.splice(pos, 0, subtitle);
        } else {
            this.subtitles.push(subtitle);
        }
        if(subtitle.isSynced()) {
            this.syncedCount++;
        }
	changeObj.previousTiming = previousTiming;
        this.emitChange('insert', subtitle, changeObj);
        //this.emitChange('insert', subtitle, { 'before': otherSubtitle, 'pos': pos, 'previousTiming': previousTiming});
        return subtitle;
    }

    SubtitleList.prototype.removeSubtitle = function(subtitle) {
        var pos = this.getIndex(subtitle);
	var changeObj = {
	    pos: pos,
	    endTime: subtitle.endTime,
	    startTime: subtitle.startTime
	};
	if (subtitle.hasOwnProperty('markdown'))
	    changeObj.content = subtitle.content();
        this.parser.removeSubtitle(subtitle.node);
        this.subtitles.splice(pos, 1);
        if(subtitle.isSynced()) {
            this.syncedCount--;
        }
        this.emitChange('remove', subtitle, changeObj);
    }

    SubtitleList.prototype._removeSubtitleByPos = function(pos, changeObj) {
	var subtitle = this.subtitles[pos];
        this.parser.removeSubtitle(subtitle.node);
        if(subtitle.isSynced()) {
            this.syncedCount--;
        }
	(pos < this.subtitles.length - 1) &&
	    changeObj.hasOwnProperty('previousTiming') &&
	    changeObj.previousTiming.hasOwnProperty('firstSubtitleStartTime') &&
	    this._updateSubtitleTime(this.subtitles[pos], changeObj.previousTiming.firstSubtitleStartTime, this.subtitles[pos].endTime);
	(pos >0) &&
	    changeObj.hasOwnProperty('previousTiming') &&
	    changeObj.previousTiming.hasOwnProperty('otherSubtitleEndTime') &&
	    this._updateSubtitleTime(this.subtitles[pos-1], this.subtitles[pos].startTime, changeObj.previousTiming.otherSubtitleEndTime);
        this.subtitles.splice(pos, 1);
        this.emitChange('remove', subtitle, {'updateHistory': false});
    }

    SubtitleList.prototype.lastSyncedSubtitle = function() {
        if(this.syncedCount > 0) {
            return this.subtitles[this.syncedCount - 1];
        } else {
            return null;
        }
    }

    SubtitleList.prototype.firstUnsyncedSubtitle = function() {
        if(this.syncedCount < this.subtitles.length) {
            return this.subtitles[this.syncedCount];
        } else {
            return null;
        }
    }

    SubtitleList.prototype.secondUnsyncedSubtitle = function() {
        if(this.syncedCount + 1 < this.subtitles.length) {
            return this.subtitles[this.syncedCount + 1];
        } else {
            return null;
        }
    }

    SubtitleList.prototype.indexOfFirstSubtitleAfter = function(time) {
        /* Get the first subtitle whose end is after time
         *
         * returns index of the subtitle, or -1 if none are found.
         */

        // Do a binary search to find the sub
        var left = 0;
        var right = this.syncedCount-1;
        // First check that we are going to find any subtitle
        if(right < 0 || this.subtitles[right].endTime <= time) {
            return -1;
        }
        // Now do the binary search
        while(left < right) {
            var index = Math.floor((left + right) / 2);
            if(this.subtitles[index].endTime > time) {
                right = index;
            } else {
                left = index + 1;
            }
        }
        return left;
    }

    SubtitleList.prototype.subtitleAt = function(time) {
        /* Find the subtitle that occupies a given time.
         *
         * returns a StoredSubtitle, or null if no subtitle occupies the time.
         */
        var i = this.indexOfFirstSubtitleAfter(time);
        if(i == -1) {
            return null;
        }
        var subtitle = this.subtitles[i];
        if(subtitle.isAt(time)) {
            return subtitle;
        } else {
            return null;
        }
    }

    SubtitleList.prototype.getSubtitlesForTime = function(startTime, endTime) {
        var rv = [];
        var i = this.indexOfFirstSubtitleAfter(startTime);
        if(i == -1) {
            return rv;
        }
        for(; i < this.syncedCount; i++) {
            var subtitle = this.subtitles[i];
            if(subtitle.startTime < endTime) {
                rv.push(subtitle);
            } else {
                break;
            }
        }
        return rv;
    }

    /* CurrentEditManager manages the current in-progress edit
     */
    CurrentEditManager = function() {
        this.draft = null;
        this.LI = null;
    }

    CurrentEditManager.prototype = {
        start: function(subtitle, LI) {
            this.draft = subtitle.draftSubtitle();
            this.LI = LI;
        },
        finish: function(commitChanges, subtitleList) {
            var updateNeeded = (commitChanges && this.changed());
            if(updateNeeded) {
                subtitleList.updateSubtitleContent(this.draft.storedSubtitle,
                        this.currentMarkdown());
            }
            this.draft = this.LI = null;
            return updateNeeded;
        },
        storedSubtitle: function() {
            if(this.draft !== null) {
                return this.draft.storedSubtitle;
            } else {
                return null;
            }
        },
        sourceMarkdown: function() {
            return this.draft.storedSubtitle.markdown;
        },
        currentMarkdown: function() {
            return this.draft.markdown;
        },
        changed: function() {
            return this.sourceMarkdown() != this.currentMarkdown();
        },
         update: function(markdown) {
            if(this.draft !== null) {
                this.draft.markdown = markdown;
            }
         },
         isForSubtitle: function(subtitle) {
            return (this.draft !== null && this.draft.storedSubtitle == subtitle);
         },
         inProgress: function() {
            return this.draft !== null;
         },
         lineCounts: function() {
             if(this.draft === null || this.draft.lineCount() < 2) {
                 // Only show the line counts if there are 2 or more lines
                 return null;
             } else {
                 return this.draft.characterCountPerLine();
             }
         },
    };

    /*
     * SubtitleVersionManager: handle the active subtitle version for the
     * reference and working subs.
     *
     */

    SubtitleVersionManager = function(video, SubtitleStorage) {
        this.video = video;
        this.SubtitleStorage = SubtitleStorage;
        this.subtitleList = new SubtitleList();
        this.versionNumber = null;
        this.language = null;
        this.title = null;
        this.description = null;
        this.state = 'waiting';
        this.metadata = {};
    }

    SubtitleVersionManager.prototype = {
        getSubtitles: function(languageCode, versionNumber) {
            this.setLanguage(languageCode);
            this.versionNumber = versionNumber;
            this.state = 'loading';

            var that = this;

            this.SubtitleStorage.getSubtitles(languageCode, versionNumber,
                    function(subtitleData) {
                that.state = 'loaded';
                that.title = subtitleData.title;
                debugger;
                that.initMetadataFromVideo()
                for(key in subtitleData.metadata) {
                    that.metadata[key] = subtitleData.metadata[key];
                }
                that.description = subtitleData.description;
                that.subtitleList.loadXML(subtitleData.subtitles);
            });
        },
        initEmptySubtitles: function(languageCode, baseLanguage) {
            this.setLanguage(languageCode);
            this.versionNumber = null;
            this.title = '';
            this.description = '';
            this.subtitleList.loadXML(null);
            this.state = 'loaded';
            this.initMetadataFromVideo()
            if(baseLanguage) {
                this.addSubtitlesFromBaseLanguage(baseLanguage);
            }
        },
        initMetadataFromVideo: function() {
            this.metadata = {};
            for(key in this.video.metadata) {
                this.metadata[key] = '';
            }
        },
        addSubtitlesFromBaseLanguage: function(baseLanguage) {
            var that = this;
            this.SubtitleStorage.getSubtitles(baseLanguage, null,
                    function(subtitleData) {
                that.subtitleList.addSubtitlesFromBaseLanguage(
                    subtitleData.subtitles);
            });
        },
        setLanguage: function(code) {
            this.language = this.SubtitleStorage.getLanguage(code);
        },
        getTitle: function() {
            return this.title || this.video.title;
        },
        getDescription: function() {
            return this.description || this.video.description;
        },
    };

    /* Export modal classes as values.  This makes testing and dependency
     * injection easier.
     */

    module.value('CurrentEditManager', CurrentEditManager);
    module.value('SubtitleVersionManager', SubtitleVersionManager);
    module.value('SubtitleList', SubtitleList);
}(this));
