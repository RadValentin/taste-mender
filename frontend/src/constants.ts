/** Recommendation API */
export const AUDIO_FEATURES = [
  "danceability", "aggressiveness", "happiness", "sadness", "relaxedness", "partyness",
  "acousticness", "electronicness", "instrumentalness", "tonality", "brightness"
];

export const MOOD_FEATURES = [
  "moods_mirex_1", "moods_mirex_2", "moods_mirex_3", "moods_mirex_4", "moods_mirex_5"
];

export const FEATURE_DISPLAY_NAMES: Record<string, string> = {
  danceability: "Danceability",
  aggressiveness: "Aggressiveness",
  happiness: "Happiness",
  sadness: "Sadness",
  relaxedness: "Relaxedness",
  partyness: "Partyness",
  acousticness: "Acousticness",
  electronicness: "Electronicness",
  instrumentalness: "Instrumentalness",
  tonality: "Tonality",
  brightness: "Brightness",
  moods_mirex_1: "Passionate / Cheerful / Rowdy",
  moods_mirex_2: "Poignant / Sad / Bittersweet",
  moods_mirex_3: "Humorous / Silly / Witty",
  moods_mirex_4: "Aggressive / Fiery / Intense",
  moods_mirex_5: "Peaceful / Relaxed / Calming"
};