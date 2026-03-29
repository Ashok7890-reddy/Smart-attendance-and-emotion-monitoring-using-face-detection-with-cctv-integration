import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User } from '@/types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
}

// Helper function to extract username from email
const getUsernameFromEmail = (email: string): string => {
  return email.split('@')[0]
}

// Helper function to generate user ID
const generateUserId = (): string => {
  return 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      
      login: async (email: string, password: string) => {
        try {
          // Get stored users from localStorage
          const storedUsers = JSON.parse(localStorage.getItem('registered_users') || '[]')
          
          // Find user by email
          const user = storedUsers.find((u: any) => u.email === email)
          
          if (!user) {
            throw new Error('User not found. Please sign up first.')
          }
          
          if (user.password !== password) {
            throw new Error('Invalid password')
          }
          
          // Create user object without password
          const authenticatedUser: User = {
            id: user.id,
            name: user.name,
            email: user.email,
            role: user.role
          }
          
          set({ user: authenticatedUser, isAuthenticated: true })
          
          console.log('✅ Login successful:', authenticatedUser.name)
        } catch (error) {
          console.error('❌ Login failed:', error)
          throw error
        }
      },
      
      signup: async (email: string, password: string, fullName: string) => {
        try {
          // Get existing users
          const storedUsers = JSON.parse(localStorage.getItem('registered_users') || '[]')
          
          // Check if user already exists
          const existingUser = storedUsers.find((u: any) => u.email === email)
          if (existingUser) {
            throw new Error('User with this email already exists')
          }
          
          // Extract username from email
          const username = getUsernameFromEmail(email)
          
          // Create new user
          const newUser = {
            id: generateUserId(),
            name: fullName,
            username: username,
            email: email,
            password: password, // In real app, this should be hashed
            role: 'faculty' as const,
            createdAt: new Date().toISOString()
          }
          
          // Add to stored users
          storedUsers.push(newUser)
          localStorage.setItem('registered_users', JSON.stringify(storedUsers))
          
          // Create authenticated user object (without password)
          const authenticatedUser: User = {
            id: newUser.id,
            name: newUser.name,
            email: newUser.email,
            role: newUser.role
          }
          
          set({ user: authenticatedUser, isAuthenticated: true })
          
          console.log('✅ Signup successful:', authenticatedUser.name, 'Username:', username)
        } catch (error) {
          console.error('❌ Signup failed:', error)
          throw error
        }
      },
      
      logout: () => {
        set({ user: null, isAuthenticated: false })
        console.log('👋 User logged out')
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