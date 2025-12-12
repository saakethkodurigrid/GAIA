import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import TourMCQPage from './app/tour/TourMCQPage';
import TourCodingPage from './app/tour/TourCodingPage';
import TourSystemDesignPage from './app/tour/TourSystemDesignPage';

function App2() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Default route - show TourCodingPage */}
        <Route path="/" element={<TourMCQPage  />} />
        
        {/* Tour pages routes */}
        <Route path="/tutorial/mcq" element={<TourMCQPage />} />
        <Route path="/tutorial/coding" element={<TourCodingPage />} />
        <Route path="/tutorial/system-design" element={<TourSystemDesignPage />} />
        
        {/* Catch all - redirect to tour coding page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App2;

