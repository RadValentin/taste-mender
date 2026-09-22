import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router';
import AppLayout from './AppLayout.tsx';
import HomePage from './pages/HomePage.tsx';
import SearchPage from './pages/SearchPage.tsx';
import NotFoundPage from './pages/NotFoundPage.tsx';
import { PlaybackContextProvider } from './PlaybackProvider.tsx';
import './root.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <PlaybackContextProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </PlaybackContextProvider>
    </BrowserRouter>
  </StrictMode>,
)
