import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import TourMCQPage from './app/tour/TourMCQPage'
import TourSystemDesignPage from './app/tour/TourSystemDesignPage'
import TourCodingPage from './app/tour/TourCodingPage'
import MCQPage from './app/Candidate/MCQPage'
import CodingTestPage from './app/Candidate/CodingTestPage'
import SystemDesignPage from './app/Candidate/SystemDesignPage'
import NotFoundPage from './pages/NotFoundPage'
function AppRoutes1(){
    return(
        <Routes>
        {/* Auth Routes */}
  
        
        {/* Root route - redirects based on auth status */}
     
        
        {/* Protected Routes - require authentication */}
        <Route path="/" element={<Navigate to="/candidate/mcq" replace />} />
        
        {/* Tutorial/Mock Test Pages */}
        <Route path="/tutorial/mcq" element={<TourMCQPage />} />
        <Route path="/tutorial/coding" element={<TourCodingPage />} />
        <Route path="/tutorial/system-design" element={<TourSystemDesignPage />} />
        
        {/* Original Test Pages */}
        <Route path="/candidate/mcq" element={<MCQPage />} />
        <Route path="/candidate/coding" element={<CodingTestPage />} />
        <Route path="/candidate/system-design" element={<SystemDesignPage />} />
        
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      

    )
}
const App1 = () => {
  return (

      <BrowserRouter>
        <AppRoutes1 />
      </BrowserRouter>

  )
}

export default App1