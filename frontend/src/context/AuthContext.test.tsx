import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from './AuthContext'
import * as api from '../services/api'
import { mockUser, mockToken, mockApiResponses } from '../test/mocks'

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
    it('sets loading to true initially', () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      expect(result.current.loading).toBe(true)
    })

    it('loads user from token if present in localStorage', async () => {
      localStorage.setItem('access_token', mockToken)
      vi.mocked(api.authAPI.getCurrentUser).mockResolvedValueOnce({
        data: mockUser,
      } as any)

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
  })

  describe('login', () => {
    it('successfully logs in user and stores token', async () => {
      vi.mocked(api.authAPI.login).mockResolvedValueOnce({
        data: mockApiResponses.login,
      } as any)
      vi.mocked(api.authAPI.getCurrentUser).mockResolvedValueOnce({
        data: mockUser,
      } as any)

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      await result.current.login('test@example.com', 'password123')

      expect(api.authAPI.login).toHaveBeenCalledWith(
        'test@example.com',
        'password123'
      )
      expect(localStorage.getItem('access_token')).toBe(mockToken)
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
    })

    it('throws error when login fails', async () => {
      vi.mocked(api.authAPI.login).mockRejectedValueOnce(
        new Error('Invalid credentials')
      )

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      await expect(
        result.current.login('wrong@example.com', 'wrongpass')
      ).rejects.toThrow('Invalid credentials')

      expect(result.current.user).toBeNull()
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })

  describe('register', () => {
    it('successfully registers user and logs them in', async () => {
      vi.mocked(api.authAPI.register).mockResolvedValueOnce({
        data: mockUser,
      } as any)
      vi.mocked(api.authAPI.login).mockResolvedValueOnce({
        data: mockApiResponses.login,
      } as any)
      vi.mocked(api.authAPI.getCurrentUser).mockResolvedValueOnce({
        data: mockUser,
      } as any)

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      await result.current.register(
        'newuser@example.com',
        'password123',
        'New User'
      )

      expect(api.authAPI.register).toHaveBeenCalledWith(
        'newuser@example.com',
        'password123',
        'New User'
      )
      expect(api.authAPI.login).toHaveBeenCalledWith(
        'newuser@example.com',
        'password123'
      )
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
    })

    it('throws error when registration fails', async () => {
      vi.mocked(api.authAPI.register).mockRejectedValueOnce(
        new Error('Email already registered')
      )

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      await expect(
        result.current.register('existing@example.com', 'password123')
      ).rejects.toThrow('Email already registered')

      expect(result.current.user).toBeNull()
    })
  })

  describe('logout', () => {
    it('clears user and token, redirects to login', async () => {
      // Setup authenticated user
      localStorage.setItem('access_token', mockToken)
      vi.mocked(api.authAPI.getCurrentUser).mockResolvedValueOnce({
        data: mockUser,
      } as any)

      const { result } = renderHook(() => useAuth(), {
        wrapper: AuthProvider,
      })

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser)
      })

      // Mock window.location.href
      delete (window as any).location
      window.location = { href: '' } as any

      // Logout
      result.current.logout()

      expect(localStorage.getItem('access_token')).toBeNull()
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(window.location.href).toBe('/login')
    })
  })
})
