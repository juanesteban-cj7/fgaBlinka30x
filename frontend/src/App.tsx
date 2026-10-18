import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Invoices from './pages/Invoices'
import InvoiceDetail from './pages/InvoiceDetail'
import InvoiceEdit from './pages/InvoiceEdit'
import Upload from './pages/Upload'
import ApprovalCenter from './pages/ApprovalCenter'
import History from './pages/History'
import Rules from './pages/Rules'
import Beneficiaries from './pages/Beneficiaries'
import PageNotFound from './pages/PageNotFound'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
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
  return <RouterProvider router={router} />
}
