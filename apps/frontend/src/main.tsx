import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'

import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { Incidents } from './pages/Incidents'
import { Cameras } from './pages/Cameras'
import { Zones } from './pages/Zones'
import { Settings } from './pages/Settings'

const queryClient = new QueryClient()

const App = () => {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/cameras" element={<Cameras />} />
          <Route path="/zones" element={<Zones />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}


ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
