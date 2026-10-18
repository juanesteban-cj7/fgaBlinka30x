import { useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { LayoutDashboard, FileText, Upload, ShieldCheck, Users, History, RotateCcw, Moon, Sun } from 'lucide-react'

const darkLogo = new URL('../assets/trustflow-dark.png', import.meta.url).href
const lightLogo = new URL('../assets/trustflow-light.png', import.meta.url).href

const links = [
  { path: '/', label: 'Panel', icon: LayoutDashboard },
  { path: '/invoices', label: 'Facturas', icon: FileText },
  { path: '/upload', label: 'Cargar factura', icon: Upload },
  { path: '/approvals', label: 'Aprobaciones', icon: ShieldCheck },
  { path: '/history', label: 'Historial', icon: History },
  { path: '/rules', label: 'Reglas y políticas', icon: RotateCcw },
  { path: '/beneficiaries', label: 'Beneficiarios', icon: Users },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark')
  const navigate = useNavigate()

  useEffect(() => {
    const theme = darkMode ? 'dark' : 'light'
    document.documentElement.dataset.theme = theme
    localStorage.setItem('theme', theme)
  }, [darkMode])

  return (
    <div className="layout">
      <aside className="sidebar">
        <img className="logo" src={darkMode ? darkLogo : lightLogo} alt="TrustFlow" />
        <nav className="nav">
          {links.map((l) => {
            const Icon = l.icon
            return (
              <a
                key={l.path}
                href={l.path}
                onClick={(e) => {
                  e.preventDefault()
                  navigate(l.path)
                  setSidebarOpen(false)
                }}
                className={cn(l.path === window.location.pathname ? 'active' : '')}
              >
                <Icon size={18} />
                {l.label}
              </a>
            )
          })}
        </nav>
      </aside>
      <div className="content">
        <header className="app-navbar">
          <h1>{currentLabel()}</h1>
          <div className="header-actions">
            <button className="btn btn-icon btn-outline" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Menú" />
            <button
              className="btn btn-icon btn-outline theme-toggle"
              onClick={() => setDarkMode(!darkMode)}
              aria-label={`Cambiar a modo ${darkMode ? 'claro' : 'oscuro'}`}
              aria-pressed={darkMode}
              title={`Cambiar a modo ${darkMode ? 'claro' : 'oscuro'}`}
            >
              {darkMode ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>
        <main>{<Outlet />}</main>
      </div>
    </div>
  )
}

function currentLabel(): string {
  const p = window.location.pathname
  const found = links.find((l) => p === l.path || p.startsWith(l.path + '/'))
  return found ? found.label : 'Página no encontrada'
}

import { cn } from '../lib/utils'
