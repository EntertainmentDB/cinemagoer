# Copyright 2004-2022 Davide Alberani <da@erlug.linux.it>
#           2008-2018 H. Turgut Uyar <uyar@tekir.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""
This module provides the classes (and the instances) that are used to parse
the IMDb pages on the www.imdb.com server about a person.

For example, for "Mel Gibson" the referred pages would be:

categorized
    http://www.imdb.com/name/nm0000154/maindetails

biography
    http://www.imdb.com/name/nm0000154/bio

...and so on.
"""

import re
from datetime import datetime

from imdb.utils import analyze_name

from .movieParser import (
    DOMHTMLNewsParser,
    DOMHTMLOfficialsitesParser,
    DOMHTMLTechParser,
)
from .piculet import Path, Rule, Rules, transformers
from .utils import DOMParserBase, analyze_imdbid, build_movie, build_person

_re_spaces = re.compile(r'\s+')
_reRoles = re.compile(r'(<li>.*? \.\.\.\. )(.*?)(</li>|<br>)', re.I | re.M | re.S)


class DOMHTMLMaindetailsParser(DOMParserBase):
    """Parser for the "maindetails" page of a given person.
    The page should be provided as a string, as taken from
    the www.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example::

        cparser = DOMHTMLMaindetailsParser()
        result = cparser.parse(categorized_html_string)
    """
    _containsObjects = True
    _name_imdb_index = re.compile(r'\([IVXLCDM]+\)')

    _birth_rules = [
        Rule(
            key='birth date',
            extractor=Path('.//time[@itemprop="birthDate"]/@datetime')
        ),
        Rule(
            key='birth place',
            extractor=Path('.//a[starts-with(@href, "/search/name?birth_place=")]/text()')
        )
    ]

    _death_rules = [
        Rule(
            key='death date',
            extractor=Path('.//time[@itemprop="deathDate"]/@datetime')
        ),
        Rule(
            key='death place',
            extractor=Path('.//a[starts-with(@href, "/search/name?death_place=")]/text()')
        ),
        Rule(
            key='death notes',
            extractor=Path(
                './/div[contains(@class, "ipc-html-content-inner-div")]/text()',
                transform=lambda texts: next((t.strip() for t in texts if t and t.strip().startswith('(')), None)
            )
        )
    ]

    rules = [
        Rule(
            key='name',
            extractor=Path(
                '//h1[@data-testid="hero__pageTitle"]//text()',
                transform=lambda x: analyze_name(x)
            )
        ),
        Rule(
            key='birth info',
            extractor=Rules(
                section='//div[h4="Born:"]',
                rules=_birth_rules
            )
        ),
        Rule(
            key='death info',
            extractor=Rules(
                section='//div[h4="Died:"]',
                rules=_death_rules,
            )
        ),
        Rule(
            key='headshot',
            extractor=Path('(//section[contains(@class, "ipc-page-section")])[1]//div[contains(@class, "ipc-poster")]/img[@class="ipc-image"]/@src')  # noqa: E501
        ),
        Rule(
            key='akas',
            extractor=Path(
                '//div[h4="Alternate Names:"]/text()',
                transform=lambda x: x.strip().split('  ')
            )
        ),
        Rule(
            key='in development',
            extractor=Rules(
                foreach='//div[starts-with(@class,"devitem")]',
                rules=[
                    Rule(
                        key='link',
                        extractor=Path('./a/@href')
                    ),
                    Rule(
                        key='title',
                        extractor=Path('./a/text()')
                    )
                ],
                transform=lambda x: build_movie(
                    x.get('title') or '',
                    movieID=analyze_imdbid(x.get('link') or ''),
                    roleID=(x.get('roleID') or '').split('/'),
                    status=x.get('status') or None
                )
            )
        ),
        Rule(
            key='imdbID',
            extractor=Path('//meta[@property="og:url"]/@content',
                           transform=analyze_imdbid)
        )
    ]

    preprocessors = [
        ('<div class="clear"/> </div>', ''), ('<br/>', '<br />')
    ]

    def postprocess_data(self, data):
        for key in ['name']:
            if (key in data) and isinstance(data[key], dict):
                subdata = data[key]
                del data[key]
                data.update(subdata)
        for what in 'birth date', 'death date':
            if what in data and not data[what]:
                del data[what]
        return data


class DOMHTMLFilmographyParser(DOMParserBase):
    """Parser for the "full credits" page of a given person.
    The page should be provided as a string, as taken from
    the www.imdb.com server.

    Example::

        filmo_parser = DOMHTMLFilmographyParser()
        result = filmo_parser.parse(fullcredits_html_string)
    """
    _defGetRefs = True

    _film_rules = [
        Rule(
            key='link',
            extractor=Path('.//b/a/@href')
        ),
        Rule(
            key='title',
            extractor=Path('.//b/a/text()')
        ),
        # TODO: Notes not migrated yet
        Rule(
            key='notes',
            extractor=Path('.//div[@class="ipc-metadata-list-summary-item__c"]//ul[contains(@class, "ipc-metadata-list-summary-item__stl")]//label/text()')  # noqa: E501
        ),
        Rule(
            key='year',
            extractor=Path(
                './/span[@class="year_column"]//text()',
                transform=lambda x: x.strip(),
            ),
        ),
        Rule(
            key='status',
            extractor=Path('./a[@class="in_production"]/text()')
        ),
        Rule(
            key='rolesNoChar',
            extractor=Path(
                './/br/following-sibling::text()',
                transform=lambda x: x.strip(),
            ),
        )
    ]

    rules = [
        Rule(
            key='filmography',
            extractor=Rules(
                foreach='//div[contains(@id, "filmo-head-")]',
                rules=[
                    Rule(
                        key=Path(
                            './/a/text()',
                            transform=lambda x: x.lower()
                        ),
                        extractor=Rules(
                            foreach='./following-sibling::div[1]/div[contains(@class, "filmo-row")]',
                            rules=_film_rules,
                            transform=lambda x: build_movie(
                                x.get('title') or '',
                                year=x.get('year'),
                                movieID=analyze_imdbid(x.get('link') or ''),
                                rolesNoChar=(x.get('rolesNoChar') or '').strip(),
                                additionalNotes=x.get('notes'),
                                status=x.get('status') or None
                            )
                        )
                    )
                ]
            )
        )
    ]

    def postprocess_data(self, data):
        filmo = {}
        for job in (data.get('filmography') or []):
            if not isinstance(job, dict) or not job:
                continue
            filmo.update(job)
        if filmo:
            data['filmography'] = filmo
        return data


def extract_notes(notes):
    """Extracts the notes from the text of the death info."""
    note_begin_idx = notes.find('(')
    note_end_idx = notes.rfind(')')
    if note_begin_idx == -1 or note_end_idx == -1:
        return ''
    return notes[note_begin_idx + 1:note_end_idx].strip()


class DOMHTMLBioParser(DOMParserBase):
    """Parser for the "biography" page of a given person.
    The page should be provided as a string, as taken from
    the www.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example::

        bioparser = DOMHTMLBioParser()
        result = bioparser.parse(biography_html_string)
    """
    _defGetRefs = True

    _birth_rules = [
        Rule(
            key='monthday',
            extractor=Path('.//a[starts-with(@href, "/search/name/?birth_monthday=")]/text()')
        ),
        Rule(
            key='year',
            extractor=Path('.//a[starts-with(@href, "/search/name/?birth_year=")]/text()')
        ),
        Rule(
            key='birth place',
            extractor=Path('.//a[starts-with(@href, "/search/name/?birth_place=")]/text()')
        ),
    ]

    _death_rules = [
        Rule(
            key='monthday',
            extractor=Path('.//a[contains(@href, "monthday")]/text()')
        ),
        Rule(
            key='year',
            extractor=Path('.//a[starts-with(@href, "/search/name/?death_date=")][2]/text()')
        ),
        Rule(
            key='death place',
            extractor=Path('.//a[starts-with(@href, "/search/name/?death_place=")]/text()')
        ),

        Rule(
            key='death notes',
            extractor=Path(
                './/div[contains(@class, "ipc-html-content-inner-div")]/text()',
                transform=extract_notes
            )
        )
    ]

    rules = [
        Rule(
            key='headshot',
            extractor=Path('//div[contains(@class, "ipc-poster")]//img[contains(@class, "ipc-image")]/@src')
        ),
        Rule(
            key='birth name',
            extractor=Path('//li[@id="name"]/div[contains(@class, "ipc-metadata-list-item__content-container")]//div[contains(@class, "ipc-html-content-inner-div")]/text()', transform=lambda x: x.strip())
        ),
        Rule(
            key='nick names',
            extractor=Rules(
                foreach='//li[@id="nicknames"]//ul[contains(@class, "ipc-inline-list")]/li/span',
                rules=[
                    Rule(
                        key='nickname',
                        extractor=Path(
                            './/text()',
                            transform=lambda x: x.strip()
                        )
                    )
                ],
                transform=lambda x: x.get('nickname') or ''
            )
        ),
        Rule(
            key='birth info',
            extractor=Rules(
                section='//ul[contains(@class, "ipc-metadata-list")]/li[@id="born"]',
                rules=_birth_rules,
            )
        ),
        Rule(
            key='death info',
            extractor=Rules(
                section='//ul[contains(@class, "ipc-metadata-list")]/li[@id="died"]',
                rules=_death_rules
            )
        ),
        Rule(
            key='birth name',
            extractor=Path(
                '//table[@id="overviewTable"]'
                '//td[text()="Birth Name"]/following-sibling::td[1]/text()',
                transform=lambda x: x.strip()
            )
        ),
        Rule(
            key='height',
            extractor=Path(
                '//li[@id="height"]/div[contains(@class, "ipc-metadata-list-item__content-container")]//div[contains(@class, "ipc-html-content-inner-div")]/text()',
                transform=transformers.strip
            )
        ),
        Rule(
            key='mini biography',
            extractor=Rules(
                foreach='//div[@data-testid="sub-section-mini_bio"]',
                rules=[
                    Rule(
                        key='bio',
                        extractor=Path('.//text()')
                    ),
                    Rule(
                        key='by',
                        extractor=Path('.//a[@name="ba"]//text()')
                    )
                ],
                transform=lambda x: "%s::%s" % (
                    (x.get('bio') or '').split('- IMDb Mini Biography By:')[0].strip(),
                    (x.get('by') or '').strip() or 'Anonymous'
                )
            )
        ),
        Rule(
            key='spouse',
            extractor=Rules(
                foreach='//a[@name="spouse"]/following::table[1]//tr',
                rules=[
                    Rule(
                        key='name',
                        extractor=Path('./td[1]//text()')
                    ),
                    Rule(
                        key='info',
                        extractor=Path('./td[2]//text()')
                    )
                ],
                transform=lambda x: ("%s::%s" % (
                    x.get('name').strip(),
                    (_re_spaces.sub(' ', x.get('info') or '')).strip())).strip(':')
            )
        ),
        Rule(
            key='trade mark',
            extractor=Rules(
                foreach='//div[@data-testid="sub-section-trademark"]//li[contains(@id, "trademark_")]',
                rules=[
                    Rule(
                        key='trademark',
                        extractor=Path('.//div[contains(@class, "ipc-html-content-inner-div")]/text()', transform=transformers.strip)
                    )
                ],
                transform=lambda x: x.get('trademark') or ''
            )
        ),
        Rule(
            key='trivia',
            extractor=Rules(
                foreach='//div[@data-testid="sub-section-trivia"]//li[contains(@id, "trivia_")]',
                rules=[
                    Rule(
                        key='trivia_item',
                        extractor=Path('.//div[contains(@class, "ipc-html-content-inner-div")]/text()', transform=transformers.strip)
                    )
                ],
                transform=lambda x: x.get('trivia_item') or ''
            )
        ),
        Rule(
            key='quotes',
            extractor=Rules(
                foreach='//div[@data-testid="sub-section-quotes"]//li[contains(@id, "quote_")]',
                rules=[
                    Rule(
                        key='quote',
                        extractor=Path('.//div[contains(@class, "ipc-html-content-inner-div")]/text()', transform=transformers.strip)
                    )
                ],
                transform=lambda x: (x.get('quote') or '').replace('\n', ' ')
            )
        ),
        Rule(
            key='salary history',
            extractor=Rules(
                foreach='//div[@data-testid="sub-section-salary"]//li',
                rules=[
                    Rule(
                        key='title',
                        extractor=Path('.//a/text()', transform=transformers.strip)
                    ),
                    Rule(
                        key='info',
                        extractor=Path('string(.//a/following-sibling::text()[1])', transform=transformers.strip)
                    )
                ],
                transform=lambda x: "%s %s" % (
                    (x.get('title') or '').strip(),
                    (x.get('info') or '').strip().replace(' - ', '::')
                )
            )
        )
    ]

    def postprocess_data(self, data):
        for event in ['birth', 'death']:
            info = data.pop(f'{event} info', {})
            monthday = ''
            year = ''
            the_date = ''
            if 'monthday' in info:
                monthday = datetime.strptime(info.pop('monthday'), '%B %d').strftime('%m-%d')
            if 'year' in info:
                year = info.pop('year')
            if year and monthday:
                the_date = f'{year}-{monthday}'
            elif year:
                the_date = year
            elif monthday:
                the_date = monthday
            if the_date:
                data[f'{event} date'] = the_date
            data.update(info)
            if 'death notes' in info:
                data['death notes'] = info['death notes'].strip()
        if 'nick names' in data and isinstance(data['nick names'], str):
            data['nick names'] = [data['nick names']]
        return data


class DOMHTMLOtherWorksParser(DOMParserBase):
    """Parser for the "other works" page of a given person.
    The page should be provided as a string, as taken from
    the www.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example::

        owparser = DOMHTMLOtherWorksParser()
        result = owparser.parse(otherworks_html_string)
    """
    _defGetRefs = True

    rules = [
        Rule(
            key='other works',
            extractor=Rules(
                foreach='//li[contains(@class, "ipc-metadata-list__item") and @data-testid="list-item"]',
                rules=[
                    Rule(
                        key='work',
                        extractor=Path('.//div[contains(@class, "ipc-html-content-inner-div")]/text()', transform=transformers.strip)
                    )
                ],
                transform=lambda x: x.get('work') or ''
            )
        )
    ]


class DOMHTMLPersonGenresParser(DOMParserBase):
    """Parser for the "by genre" and "by keywords" pages of a given person.
    The page should be provided as a string, as taken from
    the www.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example::

        gparser = DOMHTMLPersonGenresParser()
        result = gparser.parse(bygenre_html_string)
    """
    kind = 'genres'
    _containsObjects = True

    rules = [
        Rule(
            key='genres',
            extractor=Rules(
                foreach='//b/a[@name]/following-sibling::a[1]',
                rules=[
                    Rule(
                        key=Path('./text()', transform=str.lower),
                        extractor=Rules(
                            foreach='../../following-sibling::ol[1]/li//a[1]',
                            rules=[
                                Rule(
                                    key='link',
                                    extractor=Path('./@href')
                                ),
                                Rule(
                                    key='title',
                                    extractor=Path('./text()')
                                ),
                                Rule(
                                    key='info',
                                    extractor=Path('./following-sibling::text()')
                                )
                            ],
                            transform=lambda x: build_movie(
                                x.get('title') + x.get('info').split('[')[0],
                                analyze_imdbid(x.get('link')))
                        )
                    )
                ]
            )
        )
    ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        return {self.kind: data}


def _process_person_award(x):
    awards = {}
    movies = x.get('movies')
    year = x.get('year')
    result = x.get('result')
    prize = x.get('prize')
    category = x.get('category')
    award = x.get('award')
    sharedWith = x.get('shared with')

    if year:
        awards['year'] = int(year.strip())
    if result:
        awards['result'] = result.strip()
    if prize:
        awards['prize'] = prize.strip()
    if category:
        awards['category'] = category.strip()
    if movies:
        awards['movies'] = movies
    if award:
        awards['award'] = award.strip()
    if sharedWith:
        awards['shared with'] = sharedWith
    return awards


class DOMHTMLPersonAwardsParser(DOMParserBase):
    _defGetRefs = True

    rules = [
        Rule(
            key='awards',
            extractor=Rules(
                foreach='//table[@class="awards"]/tr',
                rules=[
                    Rule(
                        key='year',
                        extractor=Path('./td[@class="award_year"]/a/text()')
                    ),
                    Rule(
                        key='result',
                        extractor=Path('./td[@class="award_outcome"]/b/text()')
                    ),
                    Rule(
                        key='prize',
                        extractor=Path('.//span[@class="award_category"]/text()')
                    ),
                    Rule(
                        key='movies',
                        foreach='./td[@class="award_description"]/a',
                        extractor=Rules(
                            [
                                Rule(
                                    key='title',
                                    extractor=Path('./text()')
                                ),
                                Rule(
                                    key='link',
                                    extractor=Path('./@href')
                                ),
                                Rule(
                                    key='year',
                                    extractor=Path('./following-sibling::span[@class="title_year"][1]/text()')
                                )
                            ],
                            transform=lambda x: build_movie(
                                x.get('title') or '',
                                movieID=analyze_imdbid(x.get('link')),
                                year=x.get('year')
                            )
                        )
                    ),
                    Rule(
                        key='shared with',
                        foreach='./td[@class="award_description"]/div[@class="shared_with"]/following-sibling::ul//a',
                        extractor=Rules(
                            [
                                Rule(
                                    key='name',
                                    extractor=Path('./text()')
                                ),
                                Rule(
                                    key='link',
                                    extractor=Path('./@href')
                                )
                            ],
                            transform=lambda x: build_person(
                                x.get('name') or '',
                                personID=analyze_imdbid(x.get('link'))
                            )
                        )
                    ),
                    Rule(
                        key='category',
                        extractor=Path('./td[@class="award_description"]/text()')
                    ),
                    Rule(
                        key='award',
                        extractor=Path('../preceding-sibling::h3[1]/text()')
                    ),
                ],
                transform=_process_person_award
            )
        )
    ]


_OBJECTS = {
    'maindetails_parser': ((DOMHTMLMaindetailsParser,), None),
    'bio_parser': ((DOMHTMLBioParser,), None),
    'filmo_parser': ((DOMHTMLFilmographyParser,), None),
    'otherworks_parser': ((DOMHTMLOtherWorksParser,), None),
    'person_officialsites_parser': ((DOMHTMLOfficialsitesParser,), None),
    'person_awards_parser': ((DOMHTMLPersonAwardsParser,), None),
    'publicity_parser': ((DOMHTMLTechParser,), {'kind': 'publicity'}),
    'person_contacts_parser': ((DOMHTMLTechParser,), {'kind': 'contacts'}),
    'person_genres_parser': ((DOMHTMLPersonGenresParser,), None),
    'person_keywords_parser': ((DOMHTMLPersonGenresParser,), {'kind': 'keywords'}),
    'news_parser': ((DOMHTMLNewsParser,), None),
}
