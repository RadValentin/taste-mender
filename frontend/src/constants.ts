/** Recommendation API */
export const AUDIO_FEATURES = [
  "danceability", "aggressiveness", "happiness", "sadness", "relaxedness", "partyness",
  "acousticness", "electronicness", "instrumentalness", "tonality", "brightness"
] as const;

export const MOOD_FEATURES = [
  "moods_mirex_1", "moods_mirex_2", "moods_mirex_3", "moods_mirex_4", "moods_mirex_5"
] as const;

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
  moods_mirex_1: "Passionate / Rousing / Rowdy",
  moods_mirex_2: "Cheerful / Fun / Sweet",
  moods_mirex_3: "Poignant / Wistful / Bittersweet",
  moods_mirex_4: "Humorous / Silly / Witty",
  moods_mirex_5: "Aggressive / Fiery / Intense",
};