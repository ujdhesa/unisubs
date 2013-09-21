var compareSubtitleLists = function(subtitleList1, subtitleList2) {
    if (subtitleList1.length != subtitleList2.length)
	return false;
    for(var i = 0; i < subtitleList1.length; i++) {
	var sub1 = subtitleList1[i];
	var sub2 = subtitleList2[i];
	if ((sub1.startTime != sub2.startTime) ||
	    (sub1.endTime != sub2.endTime) ||
	    (sub1.markdown != sub2.markdown))
	{
	    //console.log("Differ with " + JSON.stringify(sub1) + " and " + JSON.stringify(sub2));
	    return false;
	}
    }
    return true;
}


describe('Test the SubtitleList class', function() {
    var subtitleList = null;

    beforeEach(function() {
        module('amara.SubtitleEditor.subtitles.models');
    });

    beforeEach(inject(function(SubtitleList) {
        subtitleList = new SubtitleList();
        subtitleList.loadXML(null);

        this.addMatchers({
            'toHaveTimes': function(startTime, endTime) {
                return (this.actual.startTime == startTime &&
                    this.actual.endTime == endTime);
            },
        });
    }));

    it('should start empty', function() {
        expect(subtitleList.subtitles).toEqual([]);
    });

    it('should properly undo when empty', function() {
	expect(subtitleList.canUndo()).toEqual(false);
	subtitleList.Undo();
        expect(subtitleList.subtitles).toEqual([]);
    });

    it('should properly redo when empty', function() {
	expect(subtitleList.canRedo()).toEqual(false);
	subtitleList.Redo();
        expect(subtitleList.subtitles).toEqual([]);
    });

    it('should support insertion and removal', function() {
        var sub1 = subtitleList.insertSubtitleBefore(null);
        var sub2 = subtitleList.insertSubtitleBefore(sub1);
        var sub3 = subtitleList.insertSubtitleBefore(null);
        expect(subtitleList.subtitles).toEqual([sub2, sub1, sub3]);
        subtitleList.removeSubtitle(sub1);
        expect(subtitleList.subtitles).toEqual([sub2, sub3]);
        subtitleList.removeSubtitle(sub2);
        expect(subtitleList.subtitles).toEqual([sub3]);
        subtitleList.removeSubtitle(sub3);
        expect(subtitleList.subtitles).toEqual([]);
    });

    it('should support undoing insertion and removal', function() {
        var sub1 = subtitleList.insertSubtitleBefore(null);
	expect(subtitleList.subtitles).toEqual([sub1]);
	subtitleList.Undo();
	expect(subtitleList.subtitles).toEqual([]);
        var sub2 = subtitleList.insertSubtitleBefore(null);
        var sub3 = subtitleList.insertSubtitleBefore(sub2);
	subtitleList.Undo();
	expect(subtitleList.subtitles).toEqual([sub2]);
    });

    it('should support redoing insertion and removal', function() {
        var sub1 = subtitleList.insertSubtitleBefore(null);
	expect(subtitleList.subtitles).toEqual([sub1]);
	subtitleList.Undo();
	expect(subtitleList.subtitles).toEqual([]);
	subtitleList.Redo();
	expect(compareSubtitleLists(subtitleList.subtitles, [sub1])).toEqual(true);
    });

    it('should support redoing editions', function() {
        var sub = subtitleList.insertSubtitleBefore(null);
        var subclone1 = JSON.parse(JSON.stringify(sub));
	subtitleList.updateSubtitleContent(sub, 'test');
	var subclone2 = JSON.parse(JSON.stringify(sub));
	expect(compareSubtitleLists(subtitleList.subtitles, [subclone1])).toEqual(false);
	expect(compareSubtitleLists(subtitleList.subtitles, [subclone2])).toEqual(true);
	subtitleList.Undo();
	expect(compareSubtitleLists(subtitleList.subtitles, [subclone1])).toEqual(true);
	expect(compareSubtitleLists(subtitleList.subtitles, [subclone2])).toEqual(false);
	subtitleList.Redo();
	expect(compareSubtitleLists(subtitleList.subtitles, [subclone1])).toEqual(false);
	expect(compareSubtitleLists(subtitleList.subtitles, [subclone2])).toEqual(true);
    });

    it('should not propose any redo after any operation', function() {
	expect(subtitleList.canRedo()).toEqual(false);
        var sub1 = subtitleList.insertSubtitleBefore(null);
	subtitleList.Undo();
	expect(subtitleList.canRedo()).toEqual(true);
        var sub2 = subtitleList.insertSubtitleBefore(null);
	expect(subtitleList.canRedo()).toEqual(false);
    });

    it('should update content', function() {
        var sub1 = subtitleList.insertSubtitleBefore(null);
        expect(sub1.content()).toEqual('');
        subtitleList.updateSubtitleContent(sub1, 'test');
        expect(sub1.content()).toEqual('test');
        subtitleList.updateSubtitleContent(sub1, '*test*');
        expect(sub1.content()).toEqual('<i>test</i>');
        subtitleList.updateSubtitleContent(sub1, '**test**');
        expect(sub1.content()).toEqual('<b>test</b>');
        subtitleList.updateSubtitleContent(sub1, '_test_');
        expect(sub1.content()).toEqual('<u>test</u>');
    });

    it('should update timing', function() {
        var sub1 = subtitleList.insertSubtitleBefore(null);
        var sub2 = subtitleList.insertSubtitleBefore(null);
        expect(subtitleList.syncedCount).toEqual(0);
        subtitleList.updateSubtitleTime(sub1, 500, 1500);
        expect(sub1).toHaveTimes(500, 1500);
        expect(subtitleList.syncedCount).toEqual(1);
        subtitleList.updateSubtitleTime(sub1, 1000, 1500);
        expect(sub1).toHaveTimes(1000, 1500);
        expect(subtitleList.syncedCount).toEqual(1);
        subtitleList.updateSubtitleTime(sub2, 2000, 2500);
        expect(sub2).toHaveTimes(2000, 2500);
        expect(subtitleList.syncedCount).toEqual(2);
    });

    it('should invoke change callbacks', function() {
        var handler = jasmine.createSpyObj('handler', ['onChange']);
        subtitleList.addChangeCallback(handler.onChange);

        var sub = subtitleList.insertSubtitleBefore(null);
        expect(handler.onChange.callCount).toEqual(1);
	
	//TODO: fix this
	return;

        expect(handler.onChange).toHaveBeenCalledWith({
            type: 'insert',
            subtitle: sub,
            before: null,
        });
        subtitleList.updateSubtitleTime(sub, 500, 1500);
        expect(handler.onChange.callCount).toEqual(2);
        expect(handler.onChange).toHaveBeenCalledWith({
            type: 'update',
            subtitle: sub,
        });

        subtitleList.updateSubtitleContent(sub, 'content');
        expect(handler.onChange.callCount).toEqual(3);
        expect(handler.onChange).toHaveBeenCalledWith({
            type: 'update',
            subtitle: sub,
        });

        subtitleList.removeSubtitle(sub);
        expect(handler.onChange.callCount).toEqual(4);
        expect(handler.onChange).toHaveBeenCalledWith({
            type: 'remove',
            subtitle: sub,
        });

        subtitleList.removeChangeCallback(handler.onChange);
        var sub2 = subtitleList.insertSubtitleBefore(null);
        subtitleList.updateSubtitleTime(sub2, 500, 1500);
        subtitleList.updateSubtitleContent(sub2, 'content');
        subtitleList.removeSubtitle(sub2);
        expect(handler.onChange.callCount).toEqual(4);
    });
});

