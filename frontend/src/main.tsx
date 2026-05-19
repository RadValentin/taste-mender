import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { PlayerContextProvider } from './PlayerProvider.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PlayerContextProvider>
      <App />
    </PlayerContextProvider>
  </StrictMode>,
)
