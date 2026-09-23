import axios from 'axios';
import type {
  Track, TrackFeaturesResponse, Artist, Paginated, RecommendRequest, RecommendResponse,
  SearchResponse, Album
} from './types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE || '/api/v1/'

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

export async function getTracks(ordering?: string, signal?: AbortSignal) {
  const params: Record<string, string> = {};
  if (ordering) params.ordering = ordering;

  return api.get<Paginated<Track>>(`tracks/`, { params, signal }).then(resp => resp.data);
}

export function getTrack(mbid: string, signal?: AbortSignal) {
  return api.get<Track>(`tracks/${mbid}/`, { signal }).then(resp => resp.data);
}

export function getTrackFeatures(mbid: string, signal?: AbortSignal) {
  return api.get<TrackFeaturesResponse>(`tracks/${mbid}/features/`, { signal }).then(resp => resp.data);
}

export function getTrackSources(mbid: string, signal?: AbortSignal) {
  return api.get(`tracks/${mbid}/sources/`, { signal }).then(resp => resp.data.sources);
}

export function getTracksDailyPicks(signal?: AbortSignal) {
  return api.get<Paginated<Track>>('tracks/daily_picks/', { signal }).then(resp => resp.data);
}

export function getTracksTop(signal?: AbortSignal) {
  return api.get<Paginated<Track>>('tracks/top_tracks/', { signal }).then(resp => resp.data);
}

export function getTracksOnThisDay(day?: number, month?: number, signal?: AbortSignal) {
  const url = (day !== undefined && month !== undefined)
    ? `tracks/on_this_day/?mmdd=${month}-${day}`
    : `tracks/on_this_day/`;

  return api.get<Paginated<Track>>(url, { signal }).then(resp => resp.data);
}

export async function getArtists(signal?: AbortSignal) {
  return api.get<Paginated<Artist>>(`artists/`, { signal }).then(resp => resp.data);
}

export function getArtist(mbid: string, signal?: AbortSignal) {
  return api.get<Artist>(`artists/${mbid}/`, { signal }).then(resp => resp.data);
}

export function getArtistTracks(mbid: string, signal?: AbortSignal) {
  return api.get<Paginated<Track>>(`artists/${mbid}/tracks/`, { signal }).then(resp => resp.data);
}

export function getArtistTopTracks(mbid: string, signal?: AbortSignal) {
  return api.get<Paginated<Track>>(`artists/${mbid}/top-tracks/`, { signal }).then(resp => resp.data);
}

export function getArtistAlbums(mbid: string, signal?: AbortSignal) {
  return api.get<Paginated<Album>>(`artists/${mbid}/albums/`, { signal }).then(resp => resp.data);
}

export async function getAlbums(signal?: AbortSignal) {
  return api.get<Paginated<Album>>(`albums/`, { signal }).then(resp => resp.data);
}

export function getAlbum(mbid: string, signal?: AbortSignal) {
  return api.get<Album>(`albums/${mbid}/`, { signal }).then(resp => resp.data);
}

export function getAlbumArt(mbid: string, signal?: AbortSignal) {
  return api.get<string>(`albums/${mbid}/art/`, { signal }).then(resp => resp.data);
}

export function getRecommendations(body: RecommendRequest, signal?: AbortSignal) {
  return api.post<RecommendResponse>('recommend/', body, { signal }).then(resp => resp.data);
}

export function searchTracks(
  query: string, limit: number = 25, offset: number = 0, signal?: AbortSignal
) {
  return api.get<SearchResponse<Track>>(
    `search/?type=track&q=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}`,
    { signal },
  )
    .then(resp => resp.data);
}

export default api;