import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { AuthPage } from '@/components/Auth/AuthPage'
import { ProtectedRoute } from '@/components/Auth/ProtectedRoute'
import { FaceServiceInitializer } from '@/components/System/FaceServiceInitializer'
import { DashboardLayout } from '@/components/Layout/DashboardLayout'
import { Dashboard } from '@/pages/Dashboard'
import { Analytics } from '@/pages/Analytics'
import { Reports } from '@/pages/Reports'
import { Settings } from '@/pages/Settings'
import { RegisterStudent } from '@/pages/RegisterStudent'
import { GateCamera } from '@/pages/GateCamera'
import { ClassroomCamera } from '@/pages/ClassroomCamera'
import { CameraTest } from '@/pages/CameraTest'

const App: React.FC = () => {
  const { isAuthenticated } = useAuthStore()

  return (
    <FaceServiceInitializer>
      <Routes>
      <Route 
        path="/login" 
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <AuthPage />
        } 
      />
      
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardLayout title="Dashboard" subtitle="Real-time attendance monitoring" />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
      </Route>
      
      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            <DashboardLayout title="Analytics" subtitle="Student engagement insights" />
          </ProtectedRoute>
        }
      >
        <Route index element={<Analytics />} />
      </Route>
      
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <DashboardLayout title="Reports" subtitle="Attendance and engagement reports" />
          </ProtectedRoute>
        }
      >
        <Route index element={<Reports />} />
      </Route>
      
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <DashboardLayout title="Settings" subtitle="System configuration" />
          </ProtectedRoute>
        }
      >
        <Route index element={<Settings />} />
      </Route>
      
      <Route
        path="/register-student"
        element={
          <ProtectedRoute>
            <DashboardLayout title="Register Student" subtitle="Register new student with camera" />
          </ProtectedRoute>
        }
      >
        <Route index element={<RegisterStudent />} />
      </Route>
      
      <Route
        path="/gate-camera"
        element={
          <ProtectedRoute>
            <DashboardLayout title="Gate Camera" subtitle="Day scholar entry monitoring" />
          </ProtectedRoute>
        }
      >
        <Route index element={<GateCamera />} />
      </Route>
      
      <Route
        path="/classroom-camera"
        element={
          <ProtectedRoute>
            <DashboardLayout title="Classroom Camera" subtitle="Classroom attendance monitoring" />
          </ProtectedRoute>
        }
      >
        <Route index element={<ClassroomCamera />} />
      </Route>
      
      <Route
        path="/camera-test"
        element={
          <ProtectedRoute>
            <DashboardLayout title="Camera Test" subtitle="Test camera functionality" />
          </ProtectedRoute>
        }
      >
        <Route index element={<CameraTest />} />
      </Route>
      
      <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </FaceServiceInitializer>
  )
}

export default App