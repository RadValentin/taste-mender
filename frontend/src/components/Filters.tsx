/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useEffectEvent, useRef } from "react";
import isEqual from "react-fast-compare";
import { AUDIO_FEATURES, MOOD_FEATURES, FEATURE_DISPLAY_NAMES } from "../constants";
import { initialPlaybackState, usePlaybackContext } from "../PlaybackContext";
import "./Filters.css";

export type FiltersPayload = {
    filters?: any;
    feature_weights?: any;
    total_weights?: any;
}

type FiltersProps = {
    onChange: (payload:FiltersPayload) => void;
}

const defaultFiltersState = initialPlaybackState.filters.filters;
const defaultTotalWeightsState = initialPlaybackState.filters.total_weights;
const defaultFeatureWeightsState = initialPlaybackState.filters.feature_weights;

/**
 * Recommendation settings panel. Exposes controls for genre and decade guardrails,
 * the similarity/popularity ranking balance, and per-feature audio weight sliders.
 * Calls `onChange` whenever any setting changes so the parent can re-fetch recommendations.
 */
export default function Filters({ onChange }: FiltersProps) {
  const {state} = usePlaybackContext();
  const [filters, setFilters] = useState(state.filters.filters);
  const [totalWeights, setTotalWeights] = useState(state.filters.total_weights);
  const [featureWeights, setFeatureWeights] = useState(state.filters.feature_weights);

  const prevPayloadRef = useRef<FiltersPayload>({
    filters: defaultFiltersState,
    total_weights: defaultTotalWeightsState,
    feature_weights: defaultFeatureWeightsState,
  });

  /** When filters change, call the parent with updated payload. It's an EffectEvent in case the
   * parent callback (onChange) changes before callback has a change to fire
   * (getting recs for prev track).
   */
  const handleOnChange = useEffectEvent((payload: FiltersPayload) => {
    onChange(payload);
  });

  // Set up a check for input changes on an interval
  useEffect(() => {
    const payload: FiltersPayload = {
      filters,
      total_weights: {
        similarity: +totalWeights.similarity.toFixed(4),
        popularity: +totalWeights.popularity.toFixed(4),
      },
      feature_weights: featureWeights,
    };

    if (isEqual(payload, prevPayloadRef.current)) {
      return;
    }

    // If there was a change fire off a debounced callback to parent. Useful for preventing
    // redundant requests while sliders are dragged.
    const timeout = window.setTimeout(() => {
      prevPayloadRef.current = payload;
      handleOnChange(payload);
    }, 300);

    return () => window.clearTimeout(timeout);
  }, [filters, totalWeights, featureWeights]);

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
    setFilters(defaultFiltersState);
    setTotalWeights(defaultTotalWeightsState);
    setFeatureWeights(defaultFeatureWeightsState);
  };

  const getFeatureDisplayName = (key: string) => FEATURE_DISPLAY_NAMES[key] ?? key;

  return (
    <div className="filters">
      <h3 className="heading mobile-hidden">Recommendation Settings</h3>
      <h4 className="heading">Genre & Era</h4>
      <div className="filters__container">
        <label className="filters__label filters__label--inline">
          <span>Same genre</span>
          <input
            type="checkbox"
            checked={filters.same_genre}
            onChange={() => toggleFilter("same_genre")}
          />
        </label>
        <label className="filters__label filters__label--inline">
          <span>Same decade</span>
          <input
            type="checkbox"
            checked={filters.same_decade}
            onChange={() => toggleFilter("same_decade")}
          />
        </label>
        <label className="filters__label filters__label--inline filters__label--full">
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
      <div className="filters__container">
        <label className="filters__label">
          <span>Similarity</span>
          <input
            className="filters__slider" type="range" min={0} max={1} step={0.1}
            value={totalWeights.similarity}
            onChange={e => updateSimilarity(parseFloat(e.target.value))}
          />
        </label>
        <label className="filters__label">
          Popularity
          <input
            className="filters__slider" type="range" min={0} max={1} step={0.1}
            value={totalWeights.popularity}
            onChange={e => updatePopularity(parseFloat(e.target.value))}
          />
        </label>
      </div>

      <h4 className="heading">Sound & Energy</h4>
      <div className="filters__container">
        {AUDIO_FEATURES.map(feature_name => (
          <label className="filters__label" key={feature_name}>
            <span>{getFeatureDisplayName(feature_name)}</span>
            <input
              className="filters__slider" type="range" min={0} max={1} step={0.1}
              value={featureWeights[feature_name]}
              onChange={e => updateFeatureWeight(feature_name, parseFloat(e.target.value))}
            />
          </label>
        ))}
      </div>

      <h4 className="heading">Mood & Atmosphere</h4>
      <div className="filters__container">
        {MOOD_FEATURES.map(feature_name => (
          <label className="filters__label" key={feature_name}>
            <span title={getFeatureDisplayName(feature_name)}>{getFeatureDisplayName(feature_name)}</span>
            <input
              className="filters__slider" type="range" min={0} max={1} step={0.1}
              value={featureWeights[feature_name]}
              onChange={e => updateFeatureWeight(feature_name, parseFloat(e.target.value))}
            />
          </label>
        ))}
      </div>

      <button className="btn btn-amber" onClick={resetState}>
        RESET
      </button>
    </div>
  )
}