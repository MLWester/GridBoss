import type { ReactElement } from 'react'
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { LeagueLayout } from './components/layout/LeagueLayout'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { LeagueOverviewPage } from './pages/LeagueOverviewPage'
import { LeagueSettingsPlaceholder } from './pages/LeaguePlaceholders'
import { LeagueDriversPage } from './pages/LeagueDriversPage'
import { LeagueTeamsPage } from './pages/LeagueTeamsPage'
import { LeagueEventsPage } from './pages/LeagueEventsPage'
import { LeagueResultsPage } from './pages/LeagueResultsPage'
import { LeagueStandingsPage } from './pages/LeagueStandingsPage'
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
            element: <LeagueDriversPage />,
          },
          {
            path: 'teams',
            element: <LeagueTeamsPage />,
          },
          {
            path: 'events',
            element: <LeagueEventsPage />,
          },
          {
            path: 'results',
            element: <LeagueResultsPage />,
          },
          {
            path: 'standings',
            element: <LeagueStandingsPage />,
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
