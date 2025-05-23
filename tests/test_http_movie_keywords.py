def test_movie_keywords_should_be_a_list_of_keywords(ia):
    movie = ia.get_movie('0133093', info=['keywords'])  # Matrix
    keywords = movie.get('keywords', [])
    assert 40 <= len(keywords) <= 400
    assert {'agent', 'artificial-intelligence', 'artificial-reality'}.issubset(set(keywords))


def test_movie_relevant_keywords_should_be_a_list_of_keywords(ia):
    movie = ia.get_movie('0133093', info=['keywords'])  # Matrix
    keywords = movie.get('relevant keywords', [])
    assert 40 <= len(keywords) <= 400
    assert 'artificial reality' in [x['keyword'] for x in keywords]


def test_movie_keywords_if_none_should_be_excluded(ia):
    movie = ia.get_movie('1863157', info=['keywords'])  # Ates Parcasi
    assert 'keywords' not in movie
