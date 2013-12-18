#!/usr/bin/env python

import time

from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementNotVisibleException
from apps.webdriver_testing.pages.site_pages import UnisubsPage

class EditorPage(UnisubsPage):
    """
     This is the NEW subtitle editor.
    """

    _URL = "subtitles/editor/{0}/{1}/"  # (video_id, lang_code)
    EXIT_BUTTON = 'div.exit'
    _EXIT = 'a.discard'

    
    #EXIT MODAL
    _BACK_TO_FULL = 'button.yes'
    _EXIT_BUTTON = 'button.no'
    _WAIT = 'button.last-chance'

    _SAVE = 'a.save'
    _SAVE_OPTIONS = 'div button'
    #SAVE ERROR MODAL
    
    _SAVE_ERROR = 'div.modal div h1'
    _SAVE_ERROR_TEXT = ("There was an error saving your subtitles. You'll "
                        "need to copy and save your subtitles below, and "
                        "upload them to the system later.")
    _SAVE_SUBS = 'div.download textarea'
    _CLOSE = 'button.no'
    _MAIN = 'section.main'

    #LEFT COLUMN
    _HELP_KEYS = 'div.help-panel ul li span.key'
    _FEEDBACK = 'div.preview a'
    _REFERENCE_SELECT = "div.language-selections div select[name='language']"
    _VERSION_SELECT = "div.language-selections select[name='version']"
    _REF_SUB_ITEM = 'div.reference ul li.subtitle-list-item'
    _REF_METADATA_EXPANDER = 'div.reference div.metadata a'

    #CENTER COLUMN
    _VIDEO_TITLE = "div.video-title a"
    _PLAYER = "div#player"
    _EMBEDDED_VIDEO = "div#video"
    _VIDEO_SUBTITLE = 'div.subtitle-overlay div'
    _WORKING_LANGUAGE = 'section.center div.subtitles-language'
    _ADD_SUBTITLE = 'a.add-subtitle'
    _SYNC_HELP = 'div.sync-help'
    _INFO_TRAY = 'div.info-tray'
    _INFO_DETAILS = 'div.info-tray tr'
    _ADD_SUB_TO_END = 'a.end'
    _TIMELINE_DISPLAY = 'a.show-timeline span'
    _WORKING_METADATA_EXPANDER = 'div.working div.metadata a'
    _COPY_TIMING = 'a.copyover'
    _TOOLS_MENU = 'div.toolbox-inside a'
    _PARAGRAPH_MARKER = '.paragraph-start'
    _REMOVE_SUBTITLE = '.remove-subtitle'

    #SUBTITLES
    _REFERENCE_LIST = ('div.reference ul[subtitle-list='
                       '"reference-subtitle-set"]')
    _WORKING_LIST = 'ul#working-subtitle-set'
    _SUBTITLE_ITEM = 'li.subtitle-list-item'
    _SUB_TIME = 'span.timing'
    _SUB_TEXT = 'span.subtitle-text'

    #METADATA
    _SPEAKER_FIELD = 'textarea[placeholder="Enter Speaker Name"]' 


    #RIGHT COLUMN

    _NEXT_STEP = 'div.substeps div button.next-step'
    _ENDORSE = 'div.substeps button.endorse'
    _SEND_BACK = 'button.send-back'
    _APPROVE = 'button.approve'
    _NOTES = 'textarea[ng-model="notes"]'

    def open_editor_page(self, video_id, lang, close_metadata=True):
        self.open_page(self._URL.format(video_id, lang))
        if close_metadata:
            self.close_metadata()


    def open_ed_with_base(self, video_id, lang, base_lang='en'):
        url = self._URL + '?base-language={2}'
        self.open_page(url.format(video_id, lang, base_lang))
        self.close_metadata()

    def keyboard_controls_help(self):
        pass

    def feedback_link(self):
        pass

    def default_ref_language(self):
        """return the value for the default reference language. """

        return self.get_element_attribute(self._REFERENCE_SELECT, 
                                        'initial-language-code')

    def default_ref_version(self):
        """Return the value for the default reference version. """

        return self.get_element_attribute(self._REFERENCE_SELECT, 
                                        'initial-version-number')

    def selected_ref_language(self):
        """Return the currently selected reference language. """

        return self.get_text_by_css(self._REFERENCE_SELECT + (' option'
                                    '[selected="selected"]'))

    def selected_ref_version(self):
        """Return the currently selected reference version number. """

        return self.get_text_by_css(self._VERSION_SELECT + (' option'))
                                   # '[selected="selected"]'))

    def select_ref_language(self, language):
        """Choose a reference language from the list. """

        self.select_option_by_text(self._REFERENCE_SELECT, language)
        time.sleep(2)

    def select_ref_version(self, version_no):
        """Choose a reference version from the list. """

        self.select_option_by_text(self._VERSION_SELECT, version_no)

    def sub_overlayed_text(self):
        """Return the text overlayed on the video. """

        self.wait_for_element_present(self._VIDEO_SUBTITLE, wait_time=20)
        return self.get_text_by_css(self._VIDEO_SUBTITLE)

    def save(self, save_option):
        """Click the save button and the choose one of the save options.

        Options are: Resume editing, Back to full editor, Exit

        """
        self.click_by_css(self._SAVE)
        self.wait_for_element_visible('div.modal')
        time.sleep(2)
        els = self.get_elements_list(self._SAVE_OPTIONS)
        for el in els:
            if el.text == save_option:
                el.click()
                return
        else:
            self.record_error('%s is not a save text option.' % save_option)
        self.handle_js_alert('accept')


    def save_disabled(self):
        """Return whether the Save button is disabled. """

        return ('disabled' in self.get_element_attribute(self._SAVE, 'class'))

    def reference_text(self, line_num=None):
        """Return the list of subtitles for the reference language."""
        els = self.get_elements_list(' '.join([self._REFERENCE_LIST,
                                               self._SUBTITLE_ITEM, 
                                                 self._SUB_TEXT]))
        if els is None:
            return None
        subs = []
        if line_num:
            self.logger.info('just getting 1 line of text') 
            return els[line_num-1].text
        else:
            for el in els:
                subs.append(el.text)
        return subs

    def close_metadata(self):
        self.logger.info('closing the metadata')
        work_el = self.is_element_present(self._WORKING_METADATA_EXPANDER)
        if work_el and 'collapsed' not in work_el.get_attribute('class'):
            work_el.click()

    def working_language(self):
        """Return the curren working language displayed. """

        return self.get_text_by_css(self._WORKING_LANGUAGE)

    def working_text(self, position=None):
        """Return the list of working subtitles. 

        If position is supplied, just return that line of text.
        """

        els = self.get_elements_list(' '.join([self._WORKING_LIST, 
                                               self._SUBTITLE_ITEM, 
                                               self._SUB_TEXT]))
        if position:
            return els[position].text
        else:
            subs = []
            for el in els:
                subs.append(el.text)
            return subs

    def working_text_elements(self):
        """Return the list of working subtitle text elements. 

        """

        els = self.get_elements_list(' '.join([self._WORKING_LIST, 
                                               self._SUBTITLE_ITEM, 
                                               self._SUB_TEXT]))
        return els


    def toggle_timeline(self, action):
        """Toggle the timeline display.  Action should be Show or Hide.

        """
        self.hover_tools_menu()
        els = self.get_elements_list(self._TIMELINE_DISPLAY)
        for el in els: 
            if action in el.text:
                el.click()


    def video_title(self):
        """Return the text displayed for the video title. """

        return self.get_element_attribute(self._VIDEO_TITLE, "title")

    def click_working_sub_line(self, line):
        """Click in a subline of the working text. """
        if line == 0:
            self.click_by_css(self._ADD_SUB_TO_END)
            position = 0
        else:
            position = line-1
        els = self.get_elements_list(' '.join([self._WORKING_LIST, 
                                               self._SUBTITLE_ITEM]))

        try:
            subline = els[position].find_element_by_css_selector(self._SUB_TEXT)
        except:
            self.record_error('subtitle text element not found')

        sub_text = subline.text
        subline.click()
        return sub_text, els[position]

    def remove_active_subtitle(self, position):
        """Click on a subtitle and delete it. """

        removed_text, el = self.click_working_sub_line(position)
        try:
            rem = el.find_element_by_css_selector(self._REMOVE_SUBTITLE)
        except:
            self.record_error('remove button not found')
        rem.click()
        return removed_text

    def hover_tools_menu(self):
        self.hover_by_css(self._TOOLS_MENU)

    def copy_timings(self):
        self.hover_tools_menu()
        try:
            self.click_by_css(self._COPY_TIMING)
            time.sleep(1)
        except ElementNotVisibleException:
            return "Element not displayed"
 
    def toggle_paragraph(self, position):
        """Toggles the paragraph marker on or off. """

        _, el = self.click_working_sub_line(position)
        try:
            para = el.find_element_by_css_selector(self._PARAGRAPH_MARKERS)
        except:
            self.record_error('paragraph button not found')
        para.click() 


    def _last_working_list_element(self):
        """return the last active element in the working list."""

        els = self.browser.find_elements_by_css_selector(' '.join(
                    [self._WORKING_LIST, self._SUBTITLE_ITEM, 'textarea']))
        el = els[-1]
        return el

        

    def add_subs_to_the_end(self, subs):
        """Click Add subtitles at the end and add new lines"""
        self.toggle_timeline('Show')
        for line in subs:
            self.browser.execute_script("window.location.hash='add-sub-at-end'")
            self.click_by_css(self._ADD_SUB_TO_END)
            self.type_by_css('textarea.subtitle-edit', '%s\n' % line)

    def add_new_lines(self, lines):
        self.browser.execute_script("window.location.hash='add-sub-at-end'")
        self.click_by_css(self._ADD_SUB_TO_END)
        for x in range(lines-1):
            self.type_by_css('span.subtitle-text', "\n")
            time.sleep(.5)


    def edit_sub_line(self, newtext, line, enter=True):
        old_text, el = self.click_working_sub_line(line)
        e = el.find_element_by_css_selector('textarea')
        e.click()
        e.clear()
        if not isinstance(newtext, basestring):
            for x in newtext:
                if x == 'br':
                    e.send_keys(getattr(Keys, "SHIFT") + getattr(Keys, "ENTER"))
                else:
                    e.send_keys(x)
        else:
            e.send_keys(newtext)
        if enter:
            e.send_keys(Keys.ENTER)
        else:
            return e

    def exit(self):
        """Exit out of editor. """

        self.click_by_css(self._EXIT)
        self.click_by_css(self._EXIT_BUTTON)
        self.handle_js_alert('accept')

    def approve_task(self):
        self.click_by_css(self._APPROVE)
        self.wait_for_element_not_present(self._APPROVE)



    def send_back_task(self): 
        self.click_by_css(self._SEND_BACK)
        self.wait_for_element_not_present(self._SEND_BACK)
       
    def add_note(self, note_text):
        self.type_by_css(self._NOTES, note_text)
    
    def current_notes(self):
        return self.get_text_by_css(self._NOTES)


    def exit_to_full_editor(self):
        """Click exit and return to the full editor. """

        self.click_by_css(self._EXIT)
        self.click_by_css(self._BACK_TO_FULL)

    def subtitle_info(self, position, active=False):
        """Return the info tray values of the selected subtitle. """
        if not active: 
            self.click_working_sub_line(position)
            self.wait_for_element_visible(self._INFO_TRAY)
        fields = {}
        els = self.get_elements_list(self._INFO_DETAILS)
        for el in els:
            th = el.find_element_by_css_selector('th')
            td = el.find_element_by_css_selector('td')
            fields[th.text] = td.text
        self.logger.info(fields)
        return fields

    def toggle_playback(self):
        self.wait_for_element_present(self._EMBEDDED_VIDEO)
        self.type_special_key('SPACE', modifier='SHIFT', element='body')

    def buffer_up_subs(self):
        self.toggle_playback()
        time.sleep(3)
        self.toggle_playback()
        self.logger.info('buffering video')
        time.sleep(10)

    def start_next_step(self):
        els = self.get_elements_list(self._NEXT_STEP)
        for el in els:
            if el.is_displayed():
                el.click()
                return

    def endorse_subs(self):
        self.click_by_css(self._ENDORSE, self._EXIT_BUTTON)
        self.click_by_css(self._EXIT_BUTTON)
        self.handle_js_alert('accept')


    def next_step(self):
        els = self.get_elements_list(self._NEXT_STEP)
        for el in els:
            if el.is_displayed():
                return el.text

        return self.get_text_by_css(self._NEXT_STEP)

    def sync(self, num_subs, sub_length=3, sub_space=None):
        """Sync subs a given number of times. """
        self.wait_for_element_visible(self._SYNC_HELP)
        for x in range(num_subs):
            self.type_special_key('ARROW_DOWN', element='body')
            time.sleep(sub_length)
            if sub_space:
                self.type_special_key('ARROW_UP', element='body')
                time.sleep(sub_space)

    def start_times(self, position=None):
        """Return a list of the start times of the working subs. 

        If position is supplied, just return that sub time.
        """

        els = self.get_elements_list(' '.join([self._WORKING_LIST, 
                                               self._SUBTITLE_ITEM, 
                                               self._SUB_TIME]))
        if position:
            return els[position].text
        else:
            times = []
            for el in els:
                times.append(el.text)
            return times

    def reference_times(self, position=None):
        """Return a list of the start times of the reference subs. 

        If position is supplied, just return that sub time.
        """

        els = self.get_elements_list(' '.join([self._REFERENCE_LIST,
                                               self._SUBTITLE_ITEM,
                                               self._SUB_TIME]))
        if position:
            return els[position].text
        else:
            times = []
            for el in els:
                times.append(el.text)
            return times


    def sync_help_displayed(self):
        return self.is_element_visible(self._SYNC_HELP)
