import type { Mock } from 'vitest';
import { render, screen, fireEvent, act, cleanup} from '@testing-library/react';
import { AUDIO_FEATURES, MOOD_FEATURES, FEATURE_DISPLAY_NAMES } from '../../constants';
import { PlaybackContextProvider } from '../../PlaybackProvider';
import { initialPlaybackState } from '../../PlaybackContext';
import Filters from './../Filters';

describe('Filters', () => {
  let mockOnChange: Mock, container: HTMLElement;

  beforeEach(() => {
    mockOnChange = vi.fn();
    vi.useFakeTimers();

    container = render(<Filters onChange={mockOnChange} />, {
      wrapper: PlaybackContextProvider,
    }).container;
  });

  afterEach(() => {
    cleanup();
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('should render something', () => {
    expect(container.querySelector('.filters')?.children.length).toBeGreaterThan(0);
  });

  it.for(AUDIO_FEATURES)('should render sliders for audio features', (featureName) => {
    const slider = screen.getByRole('slider', {name: FEATURE_DISPLAY_NAMES[featureName]});

    expect(slider).toBeInstanceOf(HTMLInputElement);
  });

  it.for(MOOD_FEATURES)('should render sliders for mood features', (featureName) => {
    const slider = screen.getByRole('slider', {name: FEATURE_DISPLAY_NAMES[featureName]});

    expect(slider).toBeInstanceOf(HTMLInputElement);
  });

  it('should call the callback with a delay after slider change', () => {
    const slider = screen.getByRole('slider', {
      name: 'Danceability',
    });

    fireEvent.change(slider, {target: {value: '0.9'}});

    expect(slider).toBeInstanceOf(HTMLInputElement);
    expect(mockOnChange).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(300));
    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        feature_weights: expect.objectContaining({
          danceability: 0.9
        })
      })
    )
  });

  it('should debounce the callback for consecutive slider changes', () => {
    const slider = screen.getByRole('slider', {
      name: 'Aggressiveness',
    });

    fireEvent.change(slider, {target: {value: '0.9'}});

    expect(slider).toBeInstanceOf(HTMLInputElement);
    expect(mockOnChange).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(100));
    fireEvent.change(slider, {target: {value: '0.3'}});
    act(() => vi.advanceTimersByTime(200));

    expect(mockOnChange).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(100));

    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        feature_weights: expect.objectContaining({
          aggressiveness: 0.3
        })
      })
    )
  });

  it('should reset state when button is clicked', () => {
    const slider = screen.getByRole('slider', {
      name: 'Aggressiveness',
    });

    // Make a change to state
    fireEvent.change(slider, {target: {value: '0.9'}});
    act(() => vi.advanceTimersByTime(300));

    // Try to reset state
    const button = screen.getByRole('button');
    fireEvent.click(button);
    act(() => vi.advanceTimersByTime(301));

    expect(mockOnChange).toHaveBeenCalledTimes(2);
    expect(mockOnChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        feature_weights: expect.objectContaining({
          aggressiveness: initialPlaybackState.filters.feature_weights.aggressiveness
        })
      })
    )
  });
});
