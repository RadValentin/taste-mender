import {render} from '@testing-library/react'
import PlayButton from '../PlayButton'

describe('PlayButton', () => {
  it('should render play icon - snapshot', () => {
    const { asFragment } = render(<PlayButton />)
    expect(asFragment()).toMatchSnapshot()
  })

  it('should render disabled state - snapshot', () => {
    const { asFragment } = render(<PlayButton disabled={true} />)
    expect(asFragment()).toMatchSnapshot()
  })

  it('should set callback when provided - snapshot', () => {
    const { asFragment } = render(
      <PlayButton onClick={() => { console.log('YOLO') }} />
    )
    expect(asFragment()).toMatchSnapshot()
  })

  it('should render children when provided - snapshot', () => {
    const { asFragment } = render(
      <PlayButton>WOW</PlayButton>
    )
    expect(asFragment()).toMatchSnapshot()
  })
})