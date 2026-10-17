import queue
from pathlib import Path
from threading import Event

from moviq.core.matching import is_confident, rank, score
from moviq.core.models import Item
from moviq.core.naming import similarity
from moviq.core.tmdb import TMDB
from moviq.ui.app import App


def test_generic_filename_title_does_not_auto_match_my_hero_academia():
    filename = "The.Movie [Directors Cut] 2019.mkv"
    item = Item(Path(filename), Path("Movies"))
    tmdb_result = {
        "id": 592350,
        "title": "My Hero Academia: Heroes Rising",
        "original_title": "The Movie",
        "release_date": "2019-12-20",
        "popularity": 100,
    }
    client = TMDB("test-key")
    search_calls = []

    def fake_get(path, **params):
        search_calls.append((path, params))
        return {"results": [tmdb_result]}

    client.get = fake_get

    candidates = client.search(item.query, item.year)
    assert search_calls == [(
        "/search/movie",
        {
            "query": "The Movie",
            "year": 2019,
            "include_adult": "false",
        },
    )]
    ranked = rank(candidates, item.query)
    top = ranked[0]
    compared_fields = {
        "title": top["title"],
        "original_title": top["original_title"],
    }
    canonical_score = similarity(item.query, compared_fields["title"])
    alias_score = similarity(item.query, compared_fields["original_title"])

    print({
        "raw_filename": filename,
        "cleaned_query": item.query,
        "parsed_year": item.year,
        "tmdb_candidates": candidates,
        "top_candidate_display_title": top["title"],
        "scorer_field": "title",
        "compared_string": compared_fields["title"],
        "scorer": "SequenceMatcher via similarity()",
        "canonical_title_score": canonical_score,
        "original_title_alias_score_not_used": alias_score,
        "score": score(top, item.query),
        "auto_confident": is_confident(ranked, item.query, item.year),
    })

    assert score(top, item.query) == 0.0
    assert not is_confident(ranked, item.query, item.year)


def test_filename_normalization_preserves_real_movie_matches():
    cases = (
        ("Inception.2010.1080p.BluRay.mkv", "Inception", "Inception", 2010),
        (
            "The.Matrix.1999.Directors.Cut.mkv",
            "The Matrix",
            "The Matrix",
            1999,
        ),
        (
            "Spirited Away 2001.mkv",
            "Spirited Away",
            "Spirited Away",
            2001,
        ),
    )

    for filename, title, tmdb_title, year in cases:
        item = Item(Path(filename), Path("Movies"))
        candidates = [{
            "id": 1,
            "title": tmdb_title,
            "original_title": (
                "Sen to Chihiro no Kamikakushi"
                if title == "Spirited Away" else tmdb_title
            ),
            "release_date": f"{year}-01-01",
        }]
        ranked = rank(candidates, item.query)

        assert item.year == year
        assert item.query == title
        assert score(ranked[0], item.query) == 1.0
        assert is_confident(ranked, item.query, item.year)

    tagged_result = {"title": "Inception (2010) Extended Unrated Remastered"}
    assert score(tagged_result, "Inception.2010.1080p.BluRay") == 1.0


def test_generic_one_word_title_without_year_is_not_confident():
    item = Item(Path("Movie.mkv"), Path("Movies"))
    candidates = [{
        "id": 1,
        "title": "Movie",
        "original_title": "Movie",
    }]
    ranked = rank(candidates, item.query)

    assert item.year is None
    assert score(ranked[0], item.query) == 0.0
    assert not is_confident(ranked, item.query, item.year)


def test_weak_exact_filename_match_is_sent_to_manual_review(monkeypatch):
    filename = "The.Movie [Directors Cut] 2019.mkv"
    item = Item(Path(filename), Path("Movies"))
    result = {
        "id": 592350,
        "title": "My Hero Academia: Heroes Rising",
        "original_title": "The Movie",
        "release_date": "2019-12-20",
    }

    class StopWorker(Exception):
        pass

    class OneJobQueue:
        def __init__(self):
            self.job = (7, Event(), item, "test-key", "en-US", 0.9)

        def get(self):
            if self.job is None:
                raise StopWorker
            job, self.job = self.job, None
            return job

    class FakeTMDB:
        def __init__(self, key, language, cancel_event):
            self.key = key
            self.language = language
            self.cancel_event = cancel_event

        def search(self, query, year):
            assert (query, year) == ("The Movie", 2019)
            return [result]

    monkeypatch.setattr("moviq.ui.app.TMDB", FakeTMDB)
    app = App.__new__(App)
    app.jobs = OneJobQueue()
    app.results = queue.Queue()

    try:
        app.worker()
    except StopWorker:
        pass

    events = [app.results.get_nowait(), app.results.get_nowait()]
    finished = events[1]
    assert finished[0:3] == ("finished", 7, item)
    assert finished[3:] == ("review", None, "")


def test_tv_files_share_series_search_and_season_request(monkeypatch):
    items = [
        Item(Path("Breaking.Bad.S01E01.Pilot.mkv"), Path("Shows"), "tv"),
        Item(
            Path("Breaking.Bad.S01E02.Cats.in.the.Bag.mkv"),
            Path("Shows"),
            "tv",
        ),
    ]
    show = {
        "id": 1396,
        "name": "Breaking Bad",
        "first_air_date": "2008-01-20",
    }
    calls = {"search": 0, "season": 0, "episode": 0}

    class StopWorker(Exception):
        pass

    class OneJobQueue:
        def __init__(self):
            self.job = (7, Event(), items, "test-key", "en-US", 0.9)

        def get(self):
            if self.job is None:
                raise StopWorker
            job, self.job = self.job, None
            return job

    class FakeTMDB:
        def __init__(self, key, language, cancel_event):
            self.key = key
            self.language = language
            self.cancel_event = cancel_event

        def search_tv(self, query, year):
            calls["search"] += 1
            assert (query, year) == ("Breaking Bad", None)
            return [show]

        def season(self, show_id, season_number):
            calls["season"] += 1
            return {
                "episodes": [
                    {
                        "season_number": 1,
                        "episode_number": 1,
                        "name": "Pilot",
                    },
                    {
                        "season_number": 1,
                        "episode_number": 2,
                        "name": "Cat's in the Bag...",
                    },
                ],
            }

        def episode(self, *_args):
            calls["episode"] += 1
            raise AssertionError("Episode endpoints should not be used.")

    monkeypatch.setattr("moviq.ui.app.TMDB", FakeTMDB)
    app = App.__new__(App)
    app.jobs = OneJobQueue()
    app.results = queue.Queue()

    try:
        app.worker()
    except StopWorker:
        pass

    events = []
    while not app.results.empty():
        events.append(app.results.get_nowait())
    finished = [event for event in events if event[0] == "finished"]

    assert calls == {"search": 1, "season": 1, "episode": 0}
    assert len(finished) == 2
    assert [event[4]["episode_title"] for event in finished] == [
        "Pilot",
        "Cat's in the Bag...",
    ]


def test_original_title_alias_does_not_inflate_similarity():
    result = {
        "id": 1,
        "title": "My Hero Academia: Heroes Rising",
        "original_title": "The Movie",
    }

    assert score(result, "The Movie") == 0.0
