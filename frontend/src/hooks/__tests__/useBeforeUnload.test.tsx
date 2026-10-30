import type { Mock } from 'vitest';
import { cleanup, fireEvent, render } from "@testing-library/react"
import useBeforeUnload from "../useBeforeUnload"

function DummyComponent({enabled = false}) {
  useBeforeUnload(enabled)

  return null
};

describe('useBeforeUnload', () => {
  let addSpy: Mock, removeSpy: Mock

  beforeEach(() => {
    addSpy = vi.spyOn(window, 'addEventListener')
    removeSpy = vi.spyOn(window, 'removeEventListener')
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('should do nothing when not enabled', () => {
    render(<DummyComponent enabled={false} />)

    expect(addSpy).not.toHaveBeenCalled()
  })

  it('should do nothing on unmount when not enabled', () => {
    const {unmount} = render(<DummyComponent enabled={false} />)
    unmount()

    expect(addSpy).not.toHaveBeenCalled()
    expect(removeSpy).not.toHaveBeenCalled()
  })

  it('should attach listener when enabled', () => {
    render(<DummyComponent enabled={true} />)

    expect(addSpy).toHaveBeenCalledWith(
      'beforeunload',
      expect.any(Function),
    )
  })

  it('should detach listener on unmount when enabled', () => {
    const {unmount} = render(<DummyComponent enabled={true} />)
    unmount()

    expect(removeSpy).toHaveBeenCalledWith(
      'beforeunload',
      expect.any(Function),
    )
  })

  it('should request confirmation when enabled', () => {
    render(<DummyComponent enabled={true} />)

    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
  })
})