/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from "react";
import "./Filters.css";

export type FiltersPayload = {
    filters?: any;
    feature_weights?: any;
    total_weights?: any;
}

type FiltersProps = {
    onChange: (payload:FiltersPayload) => void;
}

const defaultFiltersState = {
   same_genre: true, same_decade: true, genre_classification: "rosamerica"
}

const AUDIO_FEATURES = [
  "danceability", "aggressiveness", "happiness", "sadness", "relaxedness", "partyness",
  "acousticness", "electronicness", "instrumentalness", "tonality", "brightness"
];

const MOOD_FEATURES = [
  "moods_mirex_1", "moods_mirex_2", "moods_mirex_3", "moods_mirex_4", "moods_mirex_5"
];

const FEATURE_DISPLAY_NAMES: Record<string, string> = {
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

const defaultFeatureWeightsState = Object.fromEntries(
  AUDIO_FEATURES.concat(MOOD_FEATURES).map(f => [f, 0.5])
);

const defaultTotalWeightsState = {
  similarity: 0.7, popularity: 0.3
}

/**
 * Recommendation settings panel. Exposes controls for genre and decade guardrails,
 * the similarity/popularity ranking balance, and per-feature audio weight sliders.
 * Calls `onChange` whenever any setting changes so the parent can re-fetch recommendations.
 */
export default function Filters({ onChange }: FiltersProps) {
  const [filters, setFilters] = useState(defaultFiltersState);
  const [totalWeights, setTotalWeights] = useState(defaultTotalWeightsState);
  const [featureWeights, setFeatureWeights] = useState(defaultFeatureWeightsState);

  const updateSimilarity = (val: number) => {
    setTotalWeights({ similarity: val, popularity: +(1 - val).toFixed(4) });
  };

  const updatePopularity = (val: number) => {
    setTotalWeights({ similarity: +(1 - val).toFixed(4), popularity: val });
  };

  const toggleFilter = (key: "same_genre" | "same_decade") => {
    setFilters(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const updateClassification = (value: string) => {
    const val = value === "dortmund" ? "dortmund" : "rosamerica";
    setFilters(prev => ({ ...prev, genre_classification: val }));
  };

  const updateFeatureWeight = (key: string, value: number) => {
    setFeatureWeights(prev => ({...prev, [key]: value}));
  }

  const resetState = () => {
    const isFiltersDefault = JSON.stringify(filters) === JSON.stringify(defaultFiltersState);
    const isTotalWeightsDefault = JSON.stringify(totalWeights) === JSON.stringify(defaultTotalWeightsState);
    const isFeatureWeightsDefault = JSON.stringify(featureWeights) === JSON.stringify(defaultFeatureWeightsState);

    if (isFiltersDefault && isTotalWeightsDefault && isFeatureWeightsDefault) {
      return;
    }

    setFilters(defaultFiltersState);
    setTotalWeights(defaultTotalWeightsState);
    setFeatureWeights(defaultFeatureWeightsState);

    // Trigger callback when weights reset, for filters it's automatically triggered
    if (!isTotalWeightsDefault || !isFeatureWeightsDefault) {
      setTimeout(handleChangeEnd, 0);
    }
  };

  // When filters change, call the parent with updated payload
  const handleChangeEnd = () => {
    onChange({
      filters: {
        same_genre: filters.same_genre,
        same_decade: filters.same_decade,
        genre_classification: filters.genre_classification
      },
      total_weights: {
        similarity: +totalWeights.similarity.toFixed(4),
        popularity: +totalWeights.popularity.toFixed(4),
      },
      feature_weights: featureWeights
    });
  };

  // For checkboxes and select automatically call the parent on state updates
  useEffect(() => {
    handleChangeEnd();
  }, [filters]);

  const getFeatureDisplayName = (key: string) => FEATURE_DISPLAY_NAMES[key] ?? key;

  return (
    <div className="filters">
      <h3 className="heading">Recommendation Settings</h3>
      <h4 className="heading">Genre & Era</h4>
      <div className="filters-container">
        <label className="label-inline">
          <span>Same genre</span>
          <input
            type="checkbox"
            checked={filters.same_genre}
            onChange={() => toggleFilter("same_genre")}
          />
        </label>
        <label className="label-inline">
          <span>Same decade</span>
          <input
            type="checkbox"
            checked={filters.same_decade}
            onChange={() => toggleFilter("same_decade")}
          />
        </label>
        <label className="label-inline label-full">
          <span>Genre system</span>
          <select
            value={filters.genre_classification}
            onChange={e => {updateClassification(e.target.value)}}
          >
            <option value="rosamerica">rosamerica</option>
            <option value="dortmund">dortmund</option>
          </select>
        </label>
      </div>

      <h4 className="heading">Ranking Balance</h4>
      <div className="filters-container">
        <label>
          <span>Similarity</span>
          <input
            className="slider" type="range" min={0} max={1} step={0.1}
            value={totalWeights.similarity}
            onChange={e => updateSimilarity(parseFloat(e.target.value))}
            onMouseUp={handleChangeEnd}
            onKeyUp={handleChangeEnd}
            onTouchEnd={handleChangeEnd}
          />
        </label>
        <label>
          Popularity
          <input
            className="slider" type="range" min={0} max={1} step={0.1}
            value={totalWeights.popularity}
            onChange={e => updatePopularity(parseFloat(e.target.value))}
            onMouseUp={handleChangeEnd}
            onKeyUp={handleChangeEnd}
            onTouchEnd={handleChangeEnd}
          />
        </label>
      </div>

      <h4 className="heading">Sound & Energy</h4>
      <div className="filters-container">
        {AUDIO_FEATURES.map(feature_name => (
          <label key={feature_name}>
            <span>{getFeatureDisplayName(feature_name)}</span>
            <input
              className="slider" type="range" min={0} max={1} step={0.1}
              value={featureWeights[feature_name]}
              onChange={e => updateFeatureWeight(feature_name, parseFloat(e.target.value))}
              onMouseUp={handleChangeEnd}
              onKeyUp={handleChangeEnd}
              onTouchEnd={handleChangeEnd}
            />
          </label>
        ))}
      </div>

      <h4 className="heading">Mood & Atmosphere</h4>
      <div className="filters-container">
        {MOOD_FEATURES.map(feature_name => (
          <label key={feature_name}>
            <span title={getFeatureDisplayName(feature_name)}>{getFeatureDisplayName(feature_name)}</span>
            <input
              className="slider" type="range" min={0} max={1} step={0.1}
              value={featureWeights[feature_name]}
              onChange={e => updateFeatureWeight(feature_name, parseFloat(e.target.value))}
              onMouseUp={handleChangeEnd}
              onKeyUp={handleChangeEnd}
              onTouchEnd={handleChangeEnd}
            />
          </label>
        ))}
      </div>

      <button className="btn btn-amber" onClick={resetState}>RESET</button>
    </div>
  )
}