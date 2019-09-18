#!/usr/bin/env python
# coding: utf-8

import math
import re
import Levenshtein

from typing import List, Dict

class RegexUtil():
    def __init__(self, index=None, first_occurence=False, last_occurence=False, retain = True):
        self.index = index
        self.first_occurence = first_occurence
        self.last_occurence = last_occurence
        self.retain = retain

    def extract_partial_strings(self, input_text, match_string, threshold=0.8):
        """Return the matches where the match_string is in the input_text
        Args:
            input_text The string in which we have to look for
            match_string
        Return:
            self.get_occurence(matches).
        """
        words = input_text.split()
        matches = []
        for ind,word in enumerate(words):
            if Levenshtein.ratio(word, match_string) > self.threshold:
                matches.append((ind, word))
        return self.get_occurence(matches)


    def get_occurence(self, text_words, matches):
        """Ocuurence conditions on the matches
        Args:
            text_words The words of the text string
            matches Matches we got
        Notes:
            1) If index is None and retain is true...then return return all the matches
            2) If index is None and retain is false...then return the text string other than
                the matches
            3) If index and first occurence or last occurence...prioritize...Ashyam please document

        """
        match_words = text_words
        match_indices = [match[0] for match in matches]
        # check for validations
        if not match_words:
            return "EMPTY MATCHES"
        if not self.index and self.retain:
            return match_words
        if not self.index and not self.retain:
            return " ".join([word for ind,word in enumerate(match_words) if ind not in match_indices])
        if len(match_words)-1 < self.index:
            return "INDEX OUT OF BOUND"
        if not text_words:
            return  "EMPTY TEXT WORDS"
        if self.retain:
            # return the occurence
            if self.last_occurence:
                return match_words[-1]
            if self.first_occurence:
                return match_words[0]
        return match_words[self.index]

    def extract_digits(self, text, len_digits=math.inf, include_commas=True,
            include_decimals=True, low=0, range_=True):
        """
        Return all the matching len_digits from the text

        Args:
            text (str): The text in which we look for the digits.
            len_digits (int): The length of digits we have to search. (defalut=inf)
            include_commas (bool): Flag to include commas or not. (defalut=True)
            include_decimals (bool): Flag to include decimals or not. (defalut=True)
            low (int): Minimum length of the digits to be presenet. (default=0)
            range_ (bool): Flag to include whether to look for range. (default=False)

        Returns:
            (list) List of all the matching digits based on the criteria.
        """
        if not text or len_digits == 0:
            return [] # handle edge case

        words = text.split() # hoping no numbers are sepearated by space. if so we are not handling.
        matches = []
        for ind,word in enumerate(words):
            try:
                process_word = word.strip(',') # sometimes sentences might have commas. eg. amount is 234, etc...
                # handle flags
                if include_commas:
                    process_word = process_word.replace(',', '')

                float(process_word) # check for float

                process_word_length  = len(process_word)
                if include_decimals:
                    process_word_length = process_word.split(".")[0]
                    process_word = process_word.replace('.', '')


                if range_:
                    if low <= len(process_word_length) <= len_digits:
                        matches.append((ind, word))
                else:
                    if len(process_word) == len_digits:
                        matches.append((ind, word))
            except Exception as e:
                pass
        return self.get_occurence(words, matches)

    def extract_pattern(self, text, pattern, ignore_case=True):
        """
        Extract the custom pattern from the text.

        Args:
            text (str): The text from which we are extracting the patterns.
            pattern (str): The raw pattern that we have to match against.
            ignore_case (bool): Flag to check for the case-sensitivity.

        Returns:
            (list) List of all the matches.

        Cases Covered:
            This covers the PAN, GSTIN, DATE  etc as we have to pass the respective pattern.
            For eg:
                GST - \d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1} (for extracting the GST patterns wherever)
                PAN - ^[A-Z]{5}[0-9]{4}[A-Z]$ (for matching the whole string aka validation)
                similarly for DATES
        """
        if ignore_case:
            matches = re.findall(pattern, text, re.I)
        else:
            matches = re.findall(pattern, text, re.I)

        return self.get_occurence(list(matches))
