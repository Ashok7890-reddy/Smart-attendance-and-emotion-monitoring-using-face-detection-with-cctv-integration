import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock environment variables
Object.defineProperty(import.meta, 'env', {
  value: {
    VITE_API_URL: 'http://localhost:8000/api',
    VITE_WS_URL: 'ws://localhost:8000',
    VITE_USE_MOCK_DATA: 'true'
  }
})

// Global test utilities
;(global as any).vi = vi