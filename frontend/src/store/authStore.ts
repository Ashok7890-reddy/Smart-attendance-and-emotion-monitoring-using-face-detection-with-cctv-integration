import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User } from '@/types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      
      login: async (email: string, _password: string) => {
        try {
          // TODO: Replace with actual API call
          const mockUser: User = {
            id: '1',
            name: 'Dr. John Smith',
            email,
            role: 'faculty'
          }
          
          set({ user: mockUser, isAuthenticated: true })
        } catch (error) {
          throw new Error('Invalid credentials')
        }
      },
      
      logout: () => {
        set({ user: null, isAuthenticated: false })
      },
      
      setUser: (user: User) => {
        set({ user, isAuthenticated: true })
      },
    }),
    {
      name: 'auth-storage',
    }
  )
)