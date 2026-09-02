import { createGlobalStyle } from 'styled-components'

export const GlobalStyles = createGlobalStyle`
  @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

  * {
    box-sizing: border-box;
    font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
  }

  html, body, #root {
    height: 100%;
    margin: 0;
    padding: 0;
  }

  body {
    background-color: #030712;
    color: #f8fafc;
    overflow-x: hidden;
  }

  /* 배경 성운 글로우 효과 */
  body::before {
    content: "";
    position: fixed;
    top: -150px;
    right: -100px;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(147, 51, 234, 0.12) 0%, rgba(0, 0, 0, 0) 70%);
    pointer-events: none;
    z-index: 0;
  }

  body::after {
    content: "";
    position: fixed;
    bottom: -150px;
    left: -100px;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(56, 189, 248, 0.08) 0%, rgba(0, 0, 0, 0) 70%);
    pointer-events: none;
    z-index: 0;
  }

  /* 커스텀 스크롤바 */
  ::-webkit-scrollbar {
    width: 8px;
  }

  ::-webkit-scrollbar-track {
    background: #090d16;
  }

  ::-webkit-scrollbar-thumb {
    background: #1e293b;
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: #334155;
  }

  /* 선택 텍스트 스타일 */
  ::selection {
    background-color: #a855f7;
    color: #ffffff;
  }
`
