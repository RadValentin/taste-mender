import { getScrollbarWidth } from "../layout"

describe('getScrollbarWidth', () => {
  it('should not leave any artifacts in the DOM', () => {
    const nodesBefore = Array.from(document.body.childNodes)
    getScrollbarWidth()
    const nodesAfter = Array.from(document.body.childNodes)

    expect(nodesBefore).toEqual(nodesAfter)
  })

  it('should measure scrollbar width', () => {
    const result = getScrollbarWidth()

    expect(result).not.toBeNaN()
    expect(result).toBeTypeOf("number")
  })
})