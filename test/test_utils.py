# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
#
# Copyright (C) 2006-2007 Lukáš Lalinský
# Copyright (C) 2010 fatih
# Copyright (C) 2010-2011, 2014, 2018-2021 Philipp Wolfer
# Copyright (C) 2012, 2014, 2018 Wieland Hoffmann
# Copyright (C) 2013 Ionuț Ciocîrlan
# Copyright (C) 2013-2014, 2018-2021 Laurent Monin
# Copyright (C) 2014, 2017 Sophist-UK
# Copyright (C) 2016 Frederik “Freso” S. Olesen
# Copyright (C) 2017 Sambhav Kothari
# Copyright (C) 2017 Shen-Ta Hsieh
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


import builtins
from collections import namedtuple
from collections.abc import Iterator
import re
import unittest
from unittest.mock import Mock

from test.picardtestcase import PicardTestCase

from picard import util
from picard.const.sys import IS_WIN
from picard.util import (
    extract_year_from_date,
    find_best_match,
    is_absolute_path,
    iter_files_from_objects,
    iter_unique,
    limited_join,
    make_filename_from_title,
    pattern_as_regex,
    sort_by_similarity,
    tracknum_and_title_from_filename,
    tracknum_from_filename,
    uniqify,
)


# ensure _() is defined
if '_' not in builtins.__dict__:
    builtins.__dict__['_'] = lambda a: a


class ReplaceWin32IncompatTest(PicardTestCase):

    @unittest.skipUnless(IS_WIN, "windows test")
    def test_correct_absolute_win32(self):
        self.assertEqual(util.replace_win32_incompat("c:\\test\\te\"st/2"),
                             "c:\\test\\te_st/2")
        self.assertEqual(util.replace_win32_incompat("c:\\test\\d:/2"),
                             "c:\\test\\d_/2")

    @unittest.skipUnless(not IS_WIN, "non-windows test")
    def test_correct_absolute_non_win32(self):
        self.assertEqual(util.replace_win32_incompat("/test/te\"st/2"),
                             "/test/te_st/2")
        self.assertEqual(util.replace_win32_incompat("/test/d:/2"),
                             "/test/d_/2")

    def test_correct_relative(self):
        self.assertEqual(util.replace_win32_incompat("A\"*:<>?|b"),
                             "A_______b")
        self.assertEqual(util.replace_win32_incompat("d:tes<t"),
                             "d_tes_t")

    def test_incorrect(self):
        self.assertNotEqual(util.replace_win32_incompat("c:\\test\\te\"st2"),
                             "c:\\test\\te\"st2")


class MakeFilenameTest(PicardTestCase):
    def test_filename_from_title(self):
        self.assertEqual(make_filename_from_title(), _("No Title"))
        self.assertEqual(make_filename_from_title(""), _("No Title"))
        self.assertEqual(make_filename_from_title(" "), _("No Title"))
        self.assertEqual(make_filename_from_title(default="New Default"), "New Default")
        self.assertEqual(make_filename_from_title("", "New Default"), "New Default")
        self.assertEqual(make_filename_from_title("/"), "_")

    @unittest.skipUnless(IS_WIN, "windows test")
    def test_filename_from_title_win32(self):
        self.assertEqual(make_filename_from_title("\\"), "_")
        self.assertEqual(make_filename_from_title(":"), "_")

    @unittest.skipUnless(not IS_WIN, "non-windows test")
    def test_filename_from_title_non_win32(self):
        self.assertEqual(make_filename_from_title(":"), ":")


class ExtractYearTest(PicardTestCase):
    def test_string(self):
        self.assertEqual(extract_year_from_date(""), None)
        self.assertEqual(extract_year_from_date(2020), None)
        self.assertEqual(extract_year_from_date("2020"), 2020)
        self.assertEqual(extract_year_from_date('2020-02-28'), 2020)
        self.assertEqual(extract_year_from_date('2015.02'), 2015)
        self.assertEqual(extract_year_from_date('2015; 2015'), None)
        # test for the format as supported by ID3 (https://id3.org/id3v2.4.0-structure): yyyy-MM-ddTHH:mm:ss
        self.assertEqual(extract_year_from_date('2020-07-21T13:00:00'), 2020)

    def test_mapping(self):
        self.assertEqual(extract_year_from_date({}), None)
        self.assertEqual(extract_year_from_date({'year': 'abc'}), None)
        self.assertEqual(extract_year_from_date({'year': '2020'}), 2020)
        self.assertEqual(extract_year_from_date({'year': 2020}), 2020)
        self.assertEqual(extract_year_from_date({'year': '2020-02-28'}), None)


class SanitizeDateTest(PicardTestCase):

    def test_correct(self):
        self.assertEqual(util.sanitize_date("2006--"), "2006")
        self.assertEqual(util.sanitize_date("2006--02"), "2006")
        self.assertEqual(util.sanitize_date("2006   "), "2006")
        self.assertEqual(util.sanitize_date("2006 02"), "")
        self.assertEqual(util.sanitize_date("2006.02"), "")
        self.assertEqual(util.sanitize_date("2006-02"), "2006-02")

    def test_incorrect(self):
        self.assertNotEqual(util.sanitize_date("2006--02"), "2006-02")
        self.assertNotEqual(util.sanitize_date("2006.03.02"), "2006-03-02")


class SanitizeFilenameTest(PicardTestCase):

    def test_replace_slashes(self):
        self.assertEqual(util.sanitize_filename("AC/DC"), "AC_DC")

    def test_custom_replacement(self):
        self.assertEqual(util.sanitize_filename("AC/DC", "|"), "AC|DC")

    def test_win_compat(self):
        self.assertEqual(util.sanitize_filename("AC\\/DC", win_compat=True), "AC__DC")

    @unittest.skipUnless(IS_WIN, "windows test")
    def test_replace_backslashes(self):
        self.assertEqual(util.sanitize_filename("AC\\DC"), "AC_DC")

    @unittest.skipIf(IS_WIN, "non-windows test")
    def test_keep_backslashes(self):
        self.assertEqual(util.sanitize_filename("AC\\DC"), "AC\\DC")


class TranslateArtistTest(PicardTestCase):

    def test_latin(self):
        self.assertEqual("thename", util.translate_from_sortname("thename", "sort, name"))

    def test_kanji(self):
        self.assertEqual("Tetsuya Komuro", util.translate_from_sortname("小室哲哉", "Komuro, Tetsuya"))
        # see _reverse_sortname(), cases with 3 or 4 chunks
        self.assertEqual("c b a", util.translate_from_sortname("小室哲哉", "a, b, c"))
        self.assertEqual("b a, d c", util.translate_from_sortname("小室哲哉", "a, b, c, d"))

    def test_kanji2(self):
        self.assertEqual("Ayumi Hamasaki & Keiko", util.translate_from_sortname("浜崎あゆみ & KEIKO", "Hamasaki, Ayumi & Keiko"))

    def test_cyrillic(self):
        self.assertEqual("Pyotr Ilyich Tchaikovsky", util.translate_from_sortname("Пётр Ильич Чайковский", "Tchaikovsky, Pyotr Ilyich"))


class FormatTimeTest(PicardTestCase):

    def test(self):
        self.assertEqual("?:??", util.format_time(0))
        self.assertEqual("0:00", util.format_time(0, display_zero=True))
        self.assertEqual("3:00", util.format_time(179750))
        self.assertEqual("3:00", util.format_time(179500))
        self.assertEqual("2:59", util.format_time(179499))
        self.assertEqual("59:59", util.format_time(3599499))
        self.assertEqual("1:00:00", util.format_time(3599500))
        self.assertEqual("1:02:59", util.format_time(3779499))


class HiddenFileTest(PicardTestCase):

    @unittest.skipUnless(not IS_WIN, "non-windows test")
    def test(self):
        self.assertTrue(util.is_hidden('/a/b/.c.mp3'))
        self.assertTrue(util.is_hidden('/a/.b/.c.mp3'))
        self.assertFalse(util.is_hidden('/a/.b/c.mp3'))


class TagsTest(PicardTestCase):

    def test_display_tag_name(self):
        dtn = util.tags.display_tag_name
        self.assertEqual(dtn('tag'), 'tag')
        self.assertEqual(dtn('tag:desc'), 'tag [desc]')
        self.assertEqual(dtn('tag:'), 'tag')
        self.assertEqual(dtn('tag:de:sc'), 'tag [de:sc]')
        self.assertEqual(dtn('originalyear'), 'Original Year')
        self.assertEqual(dtn('originalyear:desc'), 'Original Year [desc]')
        self.assertEqual(dtn('~length'), 'Length')
        self.assertEqual(dtn('~lengthx'), '~lengthx')
        self.assertEqual(dtn(''), '')


class LinearCombinationTest(PicardTestCase):

    def test_0(self):
        parts = []
        self.assertEqual(util.linear_combination_of_weights(parts), 0.0)

    def test_1(self):
        parts = [(1.0, 1), (1.0, 1), (1.0, 1)]
        self.assertEqual(util.linear_combination_of_weights(parts), 1.0)

    def test_2(self):
        parts = [(0.0, 1), (0.0, 0), (1.0, 0)]
        self.assertEqual(util.linear_combination_of_weights(parts), 0.0)

    def test_3(self):
        parts = [(0.0, 1), (1.0, 1)]
        self.assertEqual(util.linear_combination_of_weights(parts), 0.5)

    def test_4(self):
        parts = [(0.5, 4), (1.0, 1)]
        self.assertEqual(util.linear_combination_of_weights(parts), 0.6)

    def test_5(self):
        parts = [(0.95, 100), (0.05, 399), (0.0, 1), (1.0, 0)]
        self.assertEqual(util.linear_combination_of_weights(parts), 0.2299)

    def test_6(self):
        parts = [(-0.5, 4)]
        self.assertRaises(ValueError, util.linear_combination_of_weights, parts)

    def test_7(self):
        parts = [(0.5, -4)]
        self.assertRaises(ValueError, util.linear_combination_of_weights, parts)

    def test_8(self):
        parts = [(1.5, 4)]
        self.assertRaises(ValueError, util.linear_combination_of_weights, parts)

    def test_9(self):
        parts = ((1.5, 4))
        self.assertRaises(TypeError, util.linear_combination_of_weights, parts)


class AlbumArtistFromPathTest(PicardTestCase):

    def test_album_artist_from_path(self):
        aafp = util.album_artist_from_path
        file_1 = r"/10cc/Original Soundtrack/02 I'm Not in Love.mp3"
        file_2 = r"/10cc - Original Soundtrack/02 I'm Not in Love.mp3"
        file_3 = r"/Original Soundtrack/02 I'm Not in Love.mp3"
        file_4 = r"/02 I'm Not in Love.mp3"
        file_5 = r"/10cc - Original Soundtrack - bonus/02 I'm Not in Love.mp3"
        self.assertEqual(aafp(file_1, '', ''), ('Original Soundtrack', '10cc'))
        self.assertEqual(aafp(file_2, '', ''), ('Original Soundtrack', '10cc'))
        self.assertEqual(aafp(file_3, '', ''), ('Original Soundtrack', ''))
        self.assertEqual(aafp(file_4, '', ''), ('', ''))
        self.assertEqual(aafp(file_5, '', ''), ('Original Soundtrack - bonus', '10cc'))
        self.assertEqual(aafp(file_1, 'album', ''), ('album', ''))
        self.assertEqual(aafp(file_2, 'album', ''), ('album', ''))
        self.assertEqual(aafp(file_3, 'album', ''), ('album', ''))
        self.assertEqual(aafp(file_4, 'album', ''), ('album', ''))
        self.assertEqual(aafp(file_1, '', 'artist'), ('Original Soundtrack', 'artist'))
        self.assertEqual(aafp(file_2, '', 'artist'), ('Original Soundtrack', 'artist'))
        self.assertEqual(aafp(file_3, '', 'artist'), ('Original Soundtrack', 'artist'))
        self.assertEqual(aafp(file_4, '', 'artist'), ('', 'artist'))
        self.assertEqual(aafp(file_1, 'album', 'artist'), ('album', 'artist'))
        self.assertEqual(aafp(file_2, 'album', 'artist'), ('album', 'artist'))
        self.assertEqual(aafp(file_3, 'album', 'artist'), ('album', 'artist'))
        self.assertEqual(aafp(file_4, 'album', 'artist'), ('album', 'artist'))
        for name in ('', 'x', '/', '\\', '///'):
            self.assertEqual(aafp(name, '', 'artist'), ('', 'artist'))
        # test Strip disc subdirectory
        self.assertEqual(aafp(r'/artistx/albumy/CD 1/file.flac', '', ''), ('albumy', 'artistx'))
        self.assertEqual(aafp(r'/artistx/albumy/the DVD 23 B/file.flac', '', ''), ('albumy', 'artistx'))
        self.assertEqual(aafp(r'/artistx/albumy/disc23/file.flac', '', ''), ('albumy', 'artistx'))
        self.assertNotEqual(aafp(r'/artistx/albumy/disc/file.flac', '', ''), ('albumy', 'artistx'))


class IsAbsolutePathTest(PicardTestCase):

    def test_is_absolute(self):
        self.assertTrue(is_absolute_path('/foo/bar'))
        self.assertFalse(is_absolute_path('foo/bar'))
        self.assertFalse(is_absolute_path('./foo/bar'))
        self.assertFalse(is_absolute_path('../foo/bar'))

    @unittest.skipUnless(IS_WIN, "windows test")
    def test_is_absolute_windows(self):
        self.assertTrue(is_absolute_path('D:/foo/bar'))
        self.assertTrue(is_absolute_path('D:\\foo\\bar'))
        self.assertTrue(is_absolute_path('\\foo\\bar'))
        # Paths to Windows shares
        self.assertTrue(is_absolute_path('\\\\foo\\bar'))
        self.assertTrue(is_absolute_path('\\\\foo\\bar\\'))
        self.assertTrue(is_absolute_path('\\\\foo\\bar\\baz'))


class CompareBarcodesTest(PicardTestCase):

    def test_same(self):
        self.assertTrue(util.compare_barcodes('0727361379704', '0727361379704'))
        self.assertTrue(util.compare_barcodes('727361379704', '727361379704'))
        self.assertTrue(util.compare_barcodes('727361379704', '0727361379704'))
        self.assertTrue(util.compare_barcodes('0727361379704', '727361379704'))
        self.assertTrue(util.compare_barcodes(None, None))
        self.assertTrue(util.compare_barcodes('', ''))
        self.assertTrue(util.compare_barcodes(None, ''))
        self.assertTrue(util.compare_barcodes('', None))

    def test_not_same(self):
        self.assertFalse(util.compare_barcodes('0727361379704', '0727361379705'))
        self.assertFalse(util.compare_barcodes('727361379704', '1727361379704'))
        self.assertFalse(util.compare_barcodes('0727361379704', None))
        self.assertFalse(util.compare_barcodes(None, '0727361379704'))


class MbidValidateTest(PicardTestCase):

    def test_ok(self):
        self.assertTrue(util.mbid_validate('2944824d-4c26-476f-a981-be849081942f'))
        self.assertTrue(util.mbid_validate('2944824D-4C26-476F-A981-be849081942f'))
        self.assertFalse(util.mbid_validate(''))
        self.assertFalse(util.mbid_validate('Z944824d-4c26-476f-a981-be849081942f'))
        self.assertFalse(util.mbid_validate('22944824d-4c26-476f-a981-be849081942f'))
        self.assertFalse(util.mbid_validate('2944824d-4c26-476f-a981-be849081942ff'))
        self.assertFalse(util.mbid_validate('2944824d-4c26.476f-a981-be849081942f'))

    def test_not_ok(self):
        self.assertRaises(TypeError, util.mbid_validate, 123)
        self.assertRaises(TypeError, util.mbid_validate, None)


SimMatchTest = namedtuple('SimMatchTest', 'similarity name')


class SortBySimilarity(PicardTestCase):

    def setUp(self):
        super().setUp()
        self.test_values = [
            SimMatchTest(similarity=0.74, name='d'),
            SimMatchTest(similarity=0.61, name='a'),
            SimMatchTest(similarity=0.75, name='b'),
            SimMatchTest(similarity=0.75, name='c'),
        ]

    def candidates(self):
        yield from self.test_values

    def test_sort_by_similarity(self):
        results = [result.name for result in sort_by_similarity(self.candidates)]
        self.assertEqual(results, ['b', 'c', 'd', 'a'])

    def test_findbestmatch(self):
        no_match = SimMatchTest(similarity=-1, name='no_match')
        best_match = find_best_match(self.candidates, no_match)

        self.assertEqual(best_match.result.name, 'b')
        self.assertEqual(best_match.similarity, 0.75)
        self.assertEqual(best_match.num_results, 4)

    def test_findbestmatch_nomatch(self):
        self.test_values = []

        no_match = SimMatchTest(similarity=-1, name='no_match')
        best_match = find_best_match(self.candidates, no_match)

        self.assertEqual(best_match.result.name, 'no_match')
        self.assertEqual(best_match.similarity, -1)
        self.assertEqual(best_match.num_results, 0)


class GetQtEnum(PicardTestCase):

    def test_get_qt_enum(self):
        from PyQt5.QtCore import QStandardPaths
        values = util.get_qt_enum(QStandardPaths, QStandardPaths.LocateOption)
        self.assertIn('LocateFile', values)
        self.assertIn('LocateDirectory', values)
        self.assertNotIn('DesktopLocation', values)


class LimitedJoin(PicardTestCase):

    def setUp(self):
        super().setUp()
        self.list = [str(x) for x in range(0, 10)]

    def test_1(self):
        expected = '0+1+...+8+9'
        result = limited_join(self.list, 5, '+', '...')
        self.assertEqual(result, expected)

    def test_2(self):
        expected = '0+1+2+3+4+5+6+7+8+9'
        result = limited_join(self.list, -1)
        self.assertEqual(result, expected)
        result = limited_join(self.list, len(self.list))
        self.assertEqual(result, expected)
        result = limited_join(self.list, len(self.list) + 1)
        self.assertEqual(result, expected)

    def test_3(self):
        expected = '0,1,2,3,…,6,7,8,9'
        result = limited_join(self.list, len(self.list) - 1, ',')
        self.assertEqual(result, expected)


class IterFilesFromObjectsTest(PicardTestCase):

    def test_iterate_only_unique(self):
        f1 = Mock()
        f2 = Mock()
        f3 = Mock()
        obj1 = Mock()
        obj1.iterfiles = Mock(return_value=[f1, f2])
        obj2 = Mock()
        obj2.iterfiles = Mock(return_value=[f2, f3])
        result = iter_files_from_objects([obj1, obj2])
        self.assertTrue(isinstance(result, Iterator))
        self.assertEqual([f1, f2, f3], list(result))


class IterUniqifyTest(PicardTestCase):

    def test_unique(self):
        items = [1, 2, 3, 2, 3, 4]
        result = uniqify(items)
        self.assertEqual([1, 2, 3, 4], result)


class IterUniqueTest(PicardTestCase):

    def test_unique(self):
        items = [1, 2, 3, 2, 3, 4]
        result = iter_unique(items)
        self.assertTrue(isinstance(result, Iterator))
        self.assertEqual([1, 2, 3, 4], list(result))


class TracknumFromFilenameTest(PicardTestCase):

    def test_returns_expected_tracknumber(self):
        tests = (
            (2, '2.mp3'),
            (2, '02.mp3'),
            (2, '002.mp3'),
            (None, 'Foo.mp3'),
            (1, 'Foo 0001.mp3'),
            (1, '1 song.mp3'),
            (99, '99 Foo.mp3'),
            (42, '42. Foo.mp3'),
            (None, '20000 Feet.mp3'),
            (242, 'track no 242.mp3'),
            (77, 'Track no. 77 .mp3'),
            (242, 'track-242.mp3'),
            (242, 'track nr 242.mp3'),
            (242, 'track_242.mp3'),
            (1, 'artist song 2004 track01 xxxx.ogg'),
            (1, 'artist song 2004 track-no-01 xxxx.ogg'),
            (1, 'artist song 2004 track-no_01 xxxx.ogg'),
            (1, '01_foo.mp3'),
            (1, '01ābc.mp3'),
            (1, '01abc.mp3'),
            (11, "11 Linda Jones - Things I've Been Through 08.flac"),
            (1, "01 artist song [2004] (02).mp3"),
            (1, "01 artist song [04].mp3"),
            (7, "artist song [2004] [7].mp3"),
            # (7, "artist song [2004] (7).mp3"),
            (7, 'artist song [2004] [07].mp3'),
            (7, 'artist song [2004] (07).mp3'),
            (4, 'xx 01 artist song [04].mp3'),
            (None, 'artist song-(666) (01) xxx.ogg'),
            (None, 'song-70s 69 comment.mp3'),
            (13, "2_13 foo.mp3"),
            (13, "02-13 foo.mp3"),
            (None, '1971.mp3'),
            (42, '1971 Track 42.mp3'),
            (None, "artist song [2004].mp3"),
            (None, '0.mp3'),
            (None, 'track00.mp3'),
            (None, 'song [2004] [1000].mp3'),
            (None, 'song 2015.mp3'),
            (None, '2015 song.mp3'),
            (None, '30,000 Pounds of Bananas.mp3'),
            (None, 'Dalas 1 PM.mp3'),
            (None, "Don't Stop the 80's.mp3"),
            (None, 'Symphony no. 5 in D minor.mp3'),
            (None, 'Song 2.mp3'),
            (None, '80s best of.mp3'),
            (None, 'best of 80s.mp3'),
            # (None, '99 Luftballons.mp3'),
            (7, '99 Luftballons Track 7.mp3'),
            (None, 'Margin 0.001.mp3'),
            (None, 'All the Small Things - blink‐182.mp3'),
            (None, '99.99 Foo.mp3'),
            (5, '٠٥ فاصله میان دو پرده.mp3'),
            (23, '23 foo.mp3'),
            (None, '²³ foo.mp3'),
        )
        for expected, filename in tests:
            tracknumber = tracknum_from_filename(filename)
            self.assertEqual(expected, tracknumber, filename)


class TracknumAndTitleFromFilenameTest(PicardTestCase):

    def test_returns_expected_tracknumber(self):
        tests = (
            ((None, 'Foo'), 'Foo.mp3'),
            (('1', 'Track 0001'), 'Track 0001.mp3'),
            (('99', 'Foo'), '99 Foo.mp3'),
            (('42', 'Foo'), '0000042 Foo.mp3'),
            (('2', 'Foo'), '0000002 Foo.mp3'),
            ((None, '20000 Feet'), '20000 Feet.mp3'),
            ((None, '20,000 Feet'), '20,000 Feet.mp3'),
        )
        for expected, filename in tests:
            result = tracknum_and_title_from_filename(filename)
            self.assertEqual(expected, result)

    def test_namedtuple(self):
        result = tracknum_and_title_from_filename('0000002 Foo.mp3')
        self.assertEqual(result.tracknumber, '2')
        self.assertEqual(result.title, 'Foo')


class PatternAsRegexTest(PicardTestCase):

    def test_regex(self):
        regex = pattern_as_regex(r'/^foo.*/')
        self.assertEqual(r'^foo.*', regex.pattern)
        self.assertFalse(regex.flags & re.IGNORECASE)
        self.assertFalse(regex.flags & re.MULTILINE)

    def test_regex_flags(self):
        regex = pattern_as_regex(r'/^foo.*/', flags=re.MULTILINE | re.IGNORECASE)
        self.assertEqual(r'^foo.*', regex.pattern)
        self.assertTrue(regex.flags & re.IGNORECASE)
        self.assertTrue(regex.flags & re.MULTILINE)

    def test_regex_extra_flags(self):
        regex = pattern_as_regex(r'/^foo.*/im', flags=re.VERBOSE)
        self.assertEqual(r'^foo.*', regex.pattern)
        self.assertTrue(regex.flags & re.VERBOSE)
        self.assertTrue(regex.flags & re.IGNORECASE)
        self.assertTrue(regex.flags & re.MULTILINE)

    def test_regex_raises(self):
        with self.assertRaises(re.error):
            pattern_as_regex(r'/^foo(.*/')

    def test_wildcard(self):
        regex = pattern_as_regex(r'(foo)*', allow_wildcards=True)
        self.assertEqual(r'^\(foo\).*$', regex.pattern)
        self.assertFalse(regex.flags & re.IGNORECASE)
        self.assertFalse(regex.flags & re.MULTILINE)

    def test_wildcard_flags(self):
        regex = pattern_as_regex(r'(foo)*', allow_wildcards=True, flags=re.MULTILINE | re.IGNORECASE)
        self.assertEqual(r'^\(foo\).*$', regex.pattern)
        self.assertTrue(regex.flags & re.IGNORECASE)
        self.assertTrue(regex.flags & re.MULTILINE)

    def test_string_match(self):
        regex = pattern_as_regex(r'(foo)*', allow_wildcards=False)
        self.assertEqual(r'\(foo\)\*', regex.pattern)
        self.assertFalse(regex.flags & re.IGNORECASE)
        self.assertFalse(regex.flags & re.MULTILINE)

    def test_string_match_flags(self):
        regex = pattern_as_regex(r'(foo)*', allow_wildcards=False, flags=re.MULTILINE | re.IGNORECASE)
        self.assertEqual(r'\(foo\)\*', regex.pattern)
        self.assertTrue(regex.flags & re.IGNORECASE)
        self.assertTrue(regex.flags & re.MULTILINE)
