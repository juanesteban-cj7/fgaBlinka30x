import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import { AuthProvider, useAuth } from './components/AuthContext'
import Dashboard from './pages/Dashboard'
import Invoices from './pages/Invoices'
import InvoiceDetail from './pages/InvoiceDetail'
import InvoiceEdit from './pages/InvoiceEdit'
import Upload from './pages/Upload'
import ApprovalCenter from './pages/ApprovalCenter'
import History from './pages/History'
import Rules from './pages/Rules'
import Beneficiaries from './pages/Beneficiaries'
import Login from './pages/Login'
import PageNotFound from './pages/PageNotFound'

const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: <ProtectedLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'invoices', element: <Invoices /> },
      { path: 'invoices/:id', element: <InvoiceDetail /> },
      { path: 'invoices/:id/edit', element: <InvoiceEdit /> },
      { path: 'upload', element: <Upload /> },
      { path: 'approvals', element: <ApprovalCenter /> },
      { path: 'history', element: <History /> },
      { path: 'rules', element: <Rules /> },
      { path: 'beneficiaries', element: <Beneficiaries /> },
      { path: '*', element: <PageNotFound /> },
    ],
  },
])

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}

function ProtectedLayout() {
  const { user, loading } = useAuth()
  if (loading) return <div className="center-panel"><div className="empty-state">Verificando sesión...</div></div>
  if (!user) return <Navigate to="/login" replace />
  return <Layout />
}
