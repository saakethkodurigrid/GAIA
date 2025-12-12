import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/global.css'
import App from './App.tsx'
import App2 from './App2.tsx'
// import App1 from './App1.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
    {/* <App1/> */}
    {/* <App2/> */}
  </StrictMode>,
)
