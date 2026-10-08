from django.test import SimpleTestCase
from ingest.enrichments.youtube_source_metadata import titles_are_for_same_track, normalize_text


class YouTubeSourceMetadataTests_Titles(SimpleTestCase):
    # Text normalization
    def test_normalizes_to_lower_case(self):
        self.assertEqual(normalize_text("MASTER of Puppets"), "master of puppets")

    def test_strips_annotations(self):
        text_tuples = [
            ("Jason Aldean - Don't You Wanna Stay (with Kelly Clarkson) (Lyric Video)", "jason aldean - don't you wanna stay (with kelly clarkson)"),
            ("Good Times Roll (2016 Remaster)", "good times roll"),
            ("Good Times Roll (Remaster 2019)", "good times roll"),
            ("Good Times Roll ( remaster )", "good times roll"),
            ("Good Times Roll [2019 Remaster]", "good times roll"),
            ("Good Times Roll [Remastered 2019]", "good times roll"),
            ("Brothers In Arms (Remastered 1996)", "brothers in arms"),
            ("Brothers In Arms (Official Music Video)", "brothers in arms"),
            ("We Can Work It Out (Official Music Video) [Remastered 2015]", "we can work it out")
        ]

        for raw_text, normalized_text in text_tuples:
            self.assertEqual(normalize_text(raw_text), normalized_text)

    # All searches
    def test_rejects_empty_titles(self):
        self.assertEqual(titles_are_for_same_track("Titanium", ""), (False, 0.0))
        self.assertEqual(titles_are_for_same_track("", "Titanium"), (False, 0.0))

    # ISRC searches
    def test_matches_identical_titles(self):
        is_match, _ = titles_are_for_same_track(
            "master of puppets", "master of puppets", is_isrc=True
        )
        self.assertTrue(is_match)

    def test_matches_different_capitalization(self):
        is_match, _ = titles_are_for_same_track(
            "Master Of Puppets", "master of puppets", is_isrc=True
        )
        self.assertTrue(is_match)

    def test_matches_titles_with_extra_terms(self):
        # contains tuples of (canonical title, search result title, a)
        title_tuples = [
            ("Titanium", "Titanium (feat. Sia)"),
            ("Titanium", "David Guetta - Titanium ft. Sia (Official Video)"),
            ("Don’t You Wanna Stay", "Don't You Wanna Stay (with Kelly Clarkson)"),
            ("Don’t You Wanna Stay", "Jason Aldean - Don't You Wanna Stay (with Kelly Clarkson) (Lyric Video)"),
            ("Ode To My Family", "The Cranberries - Ode To My Family (Official Music Video)"),
            ("Statesboro Blues", "The Allman Brothers Band - Statesboro Blues ( At Fillmore East, 1971 )"),
            ("(Sittin’ on) The Dock of the Bay", "[Sittin' On] the Dock of the Bay"),
            ("(Sittin’ on) The Dock of the Bay", "(Sittin' On) the Dock of the Bay [Mono]"),
            ("Sabbath Bloody Sabbath", 'BLACK SABBATH - "Sabbath Bloody Sabbath" (Official Video)'),
            ("Stars", "Simply Red - Stars (Official Video)"),
            ("Thorn in My Side", "Eurythmics, Annie Lennox, Dave Stewart - Thorn In My Side (Official Video)"),
            ("Blowin’ in the Wind", "Blowin' in the Wind (Album Version)"),
            ("Satisfaction", "(I Can't Get No) Satisfaction (Official Lyric Video)"),
            ("D’yer Mak’er", "Led Zeppelin - D'yer Mak'er (Official Audio)"),
            ("Do You Remember Rock ’n’ Roll Radio?", "Ramones - Do You Remember Rock and Roll Radio?"),
        ]

        for original_title, comparison_title in title_tuples:
            is_match, _ = titles_are_for_same_track(original_title, comparison_title, is_isrc=True)
            self.assertTrue(is_match)

    def test_does_not_match_distinct_titles(self):
        title_tuples = [
            ("Ramble On", "Moby Dick (Intro / Outro Rough Mix)")
        ]

        for original_title, comparison_title in title_tuples:
            is_match, _ = titles_are_for_same_track(original_title, comparison_title, is_isrc=True)
            self.assertFalse(is_match)

    # Title + Artist searches
    def test_rejects_wrong_artist_when_artist_is_known(self):
        is_match, _ = titles_are_for_same_track(
            "Fast Car",
            "Jonas Blue - Fast Car ft. Dakota",
            artists=["Tracy Chapman"],
        )
        self.assertFalse(is_match)

    def test_accepts_artist(self):
        title_tuples = [
            (
                "Don’t You Wanna Stay",
                "Jason Aldean - Don't You Wanna Stay (with Kelly Clarkson) (Lyric Video)",
                ["Kelly Clarkson"],
            ), (
                "Ode to My Family",
                "The Cranberries - Ode To My Family (Official Music Video)",
                ["The Cranberries"]
            )
        ]

        for original_title, comparison_title, artists in title_tuples:
            is_match, _ = titles_are_for_same_track(
                original_title,
                comparison_title,
                artists=artists,
            )
            self.assertTrue(is_match)
