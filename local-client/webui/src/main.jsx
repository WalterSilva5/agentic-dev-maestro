import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { applyTheme, getTheme } from './theme'
import { getSettings } from './api'
import { setLang } from './i18n'
import './styles.css'

applyTheme(getTheme())

function render() {
  createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </React.StrictMode>,
  )
}

// Carrega o idioma da config antes de renderizar (t() usa o idioma vigente).
getSettings()
  .then((s) => setLang(s.language || 'pt'))
  .catch(() => {})
  .finally(render)
