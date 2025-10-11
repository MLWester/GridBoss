const DEFAULT_API_URL = 'http://localhost:8000'

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) || DEFAULT_API_URL
