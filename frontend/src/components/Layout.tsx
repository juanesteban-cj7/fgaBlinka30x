import { useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { LayoutDashboard, FileText, Upload, ShieldCheck, Users, History, RotateCcw, Moon, Sun, PanelLeftClose, PanelLeftOpen } from 'lucide-react'

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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('sidebar-collapsed') === 'true')
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark')
  const navigate = useNavigate()

  useEffect(() => {
    const theme = darkMode ? 'dark' : 'light'
    document.documentElement.dataset.theme = theme
    localStorage.setItem('theme', theme)
  }, [darkMode])

  const toggleSidebar = () => {
    setSidebarCollapsed((collapsed) => {
      localStorage.setItem('sidebar-collapsed', String(!collapsed))
      return !collapsed
    })
  }

  return (
    <div className="layout">
      <aside className={cn('sidebar', sidebarCollapsed && 'collapsed')}>
        <div className="logo" aria-label="TrustFlow">
          <span className="logo-full">TrustFlow</span>
          <span className="logo-short" aria-hidden="true">TF</span>
        </div>
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
                title={sidebarCollapsed ? l.label : undefined}
              >
                <Icon size={18} />
                <span className="nav-label">{l.label}</span>
              </a>
            )
          })}
        </nav>
        <button
          className="sidebar-toggle"
          type="button"
          onClick={toggleSidebar}
          aria-label={sidebarCollapsed ? 'Expandir barra lateral' : 'Comprimir barra lateral'}
          title={sidebarCollapsed ? 'Expandir barra lateral' : 'Comprimir barra lateral'}
        >
          {sidebarCollapsed ? <PanelLeftOpen size={18} /> : <><PanelLeftClose size={18} /><span>Comprimir</span></>}
        </button>
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
        <main><Outlet /></main>
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
