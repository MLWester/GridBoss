import type { ReactElement } from 'react'
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { LeagueLayout } from './components/layout/LeagueLayout'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { LeagueOverviewPage } from './pages/LeagueOverviewPage'
import {
  LeagueDriversPlaceholder,
  LeagueEventsPlaceholder,
  LeagueSettingsPlaceholder,
  LeagueStandingsPlaceholder,
  LeagueTeamsPlaceholder,
} from './pages/LeaguePlaceholders'
import { ProtectedRoute } from './routes/ProtectedRoute'

const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
    ],
  },
  {
    path: '/leagues/:slug',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        path: '',
        element: <LeagueLayout />,
        children: [
          {
            index: true,
            element: <LeagueOverviewPage />,
          },
          {
            path: 'drivers',
            element: <LeagueDriversPlaceholder />,
          },
          {
            path: 'teams',
            element: <LeagueTeamsPlaceholder />,
          },
          {
            path: 'events',
            element: <LeagueEventsPlaceholder />,
          },
          {
            path: 'standings',
            element: <LeagueStandingsPlaceholder />,
          },
          {
            path: 'settings',
            element: <LeagueSettingsPlaceholder />,
          },
        ],
      },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
])

function App(): ReactElement {
  return <RouterProvider router={router} />
}

export default App
