import { apiFetch } from './client'
import { ApiError } from './auth'
import type { DriverRead, DriverSummary, BulkDriverInput, UpdateDriverRequest } from '../types/drivers'

function mapDriver(driver: DriverRead): DriverSummary {
  return {
    id: driver.id,
    displayName: driver.display_name,
    teamId: driver.team_id ?? null,
    teamName: driver.team_name ?? null,
    linkedUser: Boolean(driver.user?.id ?? driver.discord_id),
    discordId: driver.discord_id ?? null,
    userName: driver.user?.discord_username ?? null,
  }
}

export async function fetchLeagueDrivers(token: string, slug: string): Promise<DriverSummary[]> {
  const response = await apiFetch(`/leagues/${slug}/drivers`, {
    token,
  })

  if (!response.ok) {
    throw new ApiError('Unable to load drivers', response.status)
  }

  const payload = (await response.json()) as DriverRead[]
  return payload.map(mapDriver)
}

export async function bulkCreateDrivers(
  token: string,
  slug: string,
  items: BulkDriverInput[],
): Promise<DriverSummary[]> {
  const response = await apiFetch(`/leagues/${slug}/drivers`, {
    method: 'POST',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ items }),
  })

  if (response.status === 409) {
    throw new ApiError('One or more driver names already exist', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to create drivers', response.status)
  }

  const payload = (await response.json()) as DriverRead[]
  return payload.map(mapDriver)
}

export async function updateDriver(
  token: string,
  driverId: string,
  body: UpdateDriverRequest,
): Promise<DriverSummary> {
  const response = await apiFetch(`/drivers/${driverId}`, {
    method: 'PATCH',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (response.status === 404) {
    throw new ApiError('Driver not found', response.status)
  }

  if (!response.ok) {
    throw new ApiError('Unable to update driver', response.status)
  }

  const payload = (await response.json()) as DriverRead
  return mapDriver(payload)
}
