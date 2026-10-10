# Notes for implementation:
# - Not all ISRCs have matching YouTube videos
# - Official videos that are found by ISRC have "Provided to YouTube by" in description
# - Need to check that the video title matches the song title to ensure we're saving the right source
# - If a video isn't found for an ISRC, we need to mark the ISRC as not found in the output, to prevent later searches for it
import re
import unicodedata
from rapidfuzz import fuzz


def normalize_text(title: str) -> str:
    if not title:
        return ""

    title = unicodedata.normalize("NFKC", title).lower()

    target_annotations = [
        "lyric video", "official video", "audio only", "remastered", "remaster",
        "official music video", "mono", "official audio", "audio", "acoustic / lyric video",
        "remix", "official hd video", "radio edit", "original official video", "official 4k video",
        "4k", "mono version", "album version", "video"
    ]
    phrases_regex = "|".join(re.escape(phrase) for phrase in target_annotations)
    pattern = rf"\s*(?:\([^()]*?(?:{phrases_regex})[^()]*?\)|\[[^\[\]]*?(?:{phrases_regex})[^\[\]]*?\])"
    title = re.sub(pattern, "", title, flags=re.I).strip()

    return title.strip()

def titles_are_for_same_track(
    original_title: str, comparison_title: str, artists: list[str] = [], is_isrc: bool = False
) -> tuple[bool, float]:
    """
    Checks if two titles are for the same track. Useful for checking if a YT search result matches
    a song in the DB. Artist names are taken into account.

    Args:
        original_title: the canonical title of the track
        comparison_title: candidate title for comparison
        artists: optional list of artists used in non-ISRC searches
        is_isrc: optional flag indicating that comparison_title was retrieved from a search by ISRC code
    """
    # Sanitization - strip extra terms
    original_title = normalize_text(original_title)
    comparison_title = normalize_text(comparison_title)
    artists = list(map(normalize_text, artists))

    if not original_title or not comparison_title:
        return False, 0.0

    # If the comparison_title was retrieved through an ISRC search it means that the record label
    # released the official video on YouTube and set the code in the video metadata.
    # We consider this a strong indicator of correctness and relax the search to a partial match.
    if (is_isrc):
        match_score = fuzz.partial_ratio(original_title, comparison_title)
        #print(f"ISRC match_score: {match_score}")
        return match_score > 80, match_score

    # Otherwise, the search was made for title + artist, not a strong indicator of correctness
    # - We don't have a strong indicator of correctness. If the artist is present, include it when matching strings.
    # - It's not clear what we should do for single word songs so if the original is a single word, we need to strictly match it against the result
    else:
        all_artists = " ".join(artists).strip()
        artist_first_match_score = fuzz.partial_ratio(f"{all_artists} {original_title}", comparison_title)
        artist_last_match_score = fuzz.partial_ratio(f"{original_title} {all_artists}", comparison_title)
        #print(f"Search match_score: {artist_first_match_score}, {artist_last_match_score}")

        match_score = max(artist_first_match_score, artist_last_match_score)

        return match_score > 80, match_score
