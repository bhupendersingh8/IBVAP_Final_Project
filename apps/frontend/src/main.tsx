import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'

import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { Cameras } from './pages/Cameras'
import { Incidents } from './pages/Incidents'
import { Evidence } from './pages/Evidence'
import { ANPR } from './pages/ANPR'
import { Zones } from './pages/Zones'
import { Reports } from './pages/Reports'
import { System } from './pages/System'
import { Settings } from './pages/Settings'

const queryClient = new QueryClient()

const App = () => {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/cameras" element={<Cameras />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/evidence" element={<Evidence />} />
          <Route path="/anpr" element={<ANPR />} />
          <Route path="/zones" element={<Zones />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/system" element={<System />} />
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
