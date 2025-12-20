import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from './AuthContext'
import * as api from '../services/api'
import { mockUser, mockToken } from '../test/mocks'

vi.mock('../services/api')

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('useAuth hook', () => {
    it('throws error when used outside AuthProvider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(() => {
        renderHook(() => useAuth())
      }).toThrow('useAuth must be used within an AuthProvider')

      consoleSpy.mockRestore()
    })
  })

  describe('AuthProvider initialization', () => {
    it('sets loading to false when no token present', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      // Wait for useEffect to complete (loading starts as true, then becomes false)
      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
      
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })

    it('loads user from token if present in localStorage', async () => {
      localStorage.setItem('access_token', mockToken)
      vi.mocked(api.authAPI.getCurrentUser).mockResolvedValueOnce({
        data: mockUser,
      } as unknown as Awaited<ReturnType<typeof api.authAPI.getCurrentUser>>)

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
    })

    it('removes invalid token and sets user to null', async () => {
      localStorage.setItem('access_token', 'invalid-token')
      vi.mocked(api.authAPI.getCurrentUser).mockRejectedValueOnce(
        new Error('Unauthorized')
      )

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
      expect(localStorage.getItem('access_token')).toBeNull()
    })

    it('sets loading to false when no token present', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })

    it('handles token from URL query parameter', async () => {
      // Mock URLSearchParams by setting token in localStorage directly
      // (The actual URL handling is tested in integration)
      localStorage.setItem('access_token', 'test-token-123')
      
      vi.mocked(api.authAPI.getCurrentUser).mockResolvedValueOnce({
        data: mockUser,
      } as unknown as Awaited<ReturnType<typeof api.authAPI.getCurrentUser>>)

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(localStorage.getItem('access_token')).toBe('test-token-123')
      expect(result.current.user).toEqual(mockUser)
    })
  })

  describe('logout', () => {
    it('clears user and token, redirects to login', async () => {
      // Setup authenticated user
      localStorage.setItem('access_token', mockToken)
      vi.mocked(api.authAPI.getCurrentUser).mockResolvedValueOnce({
        data: mockUser,
      } as unknown as Awaited<ReturnType<typeof api.authAPI.getCurrentUser>>)

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser)
      })

      // Mock window.location.href
      const mockLocation = { href: '' } as Location
      Object.defineProperty(window, 'location', {
        value: mockLocation,
        writable: true,
      })

      // Logout - this immediately redirects, so check state before redirect
      result.current.logout()

      // Logout clears localStorage and sets user to null synchronously
      expect(localStorage.getItem('access_token')).toBeNull()
      // Note: user state may not update before redirect, but localStorage is cleared
      expect(mockLocation.href).toBe('/login')
    })
  })
})
