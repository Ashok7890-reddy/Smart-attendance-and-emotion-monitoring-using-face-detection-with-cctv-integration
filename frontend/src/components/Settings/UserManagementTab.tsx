import React, { useState, useEffect } from 'react'

interface Student {
  student_id: string
  name: string
  phone: string
  type: string
  registeredAt: string
}

interface Faculty {
  id: string
  name: string
  email: string
  role: string
}

export const UserManagementTab: React.FC = () => {
  const [students, setStudents] = useState<Student[]>([])
  const [faculty, setFaculty] = useState<Faculty[]>([])

  const [showStudents, setShowStudents] = useState(false)
  const [showFaculty, setShowFaculty] = useState(false)
  const [showAddFaculty, setShowAddFaculty] = useState(false)

  const [newFaculty, setNewFaculty] = useState({ name: '', email: '', role: 'Teacher' })

  // Load data
  useEffect(() => {
    const s = JSON.parse(localStorage.getItem('students') || '[]')
    setStudents(s)
    const f = JSON.parse(localStorage.getItem('faculty') || '[]')
    setFaculty(f)
  }, [])

  // Delete student
  const deleteStudent = (id: string) => {
    if (!window.confirm(`Are you sure you want to delete student ${id}?`)) return
    const updated = students.filter(s => s.student_id !== id)
    setStudents(updated)
    localStorage.setItem('students', JSON.stringify(updated))
  }

  // Clear all
  const clearAllStudents = () => {
    if (!window.confirm('WARNING: This will delete ALL student records! Are you sure?')) return
    setStudents([])
    localStorage.setItem('students', '[]')
  }

  // Add Faculty
  const handleAddFaculty = (e: React.FormEvent) => {
    e.preventDefault()
    const id = `fac-${Date.now()}`
    const updated = [...faculty, { ...newFaculty, id }]
    setFaculty(updated)
    localStorage.setItem('faculty', JSON.stringify(updated))
    setNewFaculty({ name: '', email: '', role: 'Teacher' })
    setShowAddFaculty(false)
    setShowFaculty(true)
  }

  // Delete Faculty
  const deleteFaculty = (id: string) => {
    if (!window.confirm(`Are you sure you want to delete this faculty member?`)) return
    const updated = faculty.filter(f => f.id !== id)
    setFaculty(updated)
    localStorage.setItem('faculty', JSON.stringify(updated))
  }

  // Export CSV
  const exportStudentsCSV = () => {
    if (students.length === 0) {
      alert('No students to export.')
      return
    }
    const headers = ['Student ID', 'Name', 'Phone', 'Type', 'Registered At']
    const csvContent = [
      headers.join(','),
      ...students.map(s => `"${s.student_id}","${s.name}","${s.phone || ''}","${s.type || 'day_scholar'}","${s.registeredAt || ''}"`)
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `students_export_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="space-y-6">
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Student Database ({students.length})</h3>
        <p className="text-sm text-gray-600 mb-4">Manage registered students and export records.</p>
        
        <div className="flex flex-wrap gap-3">
          <button onClick={() => setShowStudents(!showStudents)} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
            {showStudents ? 'Hide Students' : 'View All Students'}
          </button>
          <button onClick={exportStudentsCSV} className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
            Export Student Data (CSV)
          </button>
          <button onClick={clearAllStudents} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors">
            Clear All Student Data
          </button>
        </div>
      </div>

      {showStudents && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Phone</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {students.length === 0 ? (
                <tr><td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">No students registered</td></tr>
              ) : (
                students.map(s => (
                  <tr key={s.student_id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{s.student_id}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">{s.type?.replace('_', ' ') || 'Day Scholar'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.phone}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button onClick={() => deleteStudent(s.student_id)} className="text-red-600 hover:text-red-900 focus:outline-none">
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-gray-50 rounded-lg p-4 mt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Faculty Access ({faculty.length})</h3>
        <p className="text-sm text-gray-600 mb-4">Manage faculty accounts and permissions.</p>
        
        <div className="flex flex-wrap gap-3">
          <button onClick={() => setShowFaculty(!showFaculty)} className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
            {showFaculty ? 'Hide Faculty' : 'View Faculty'}
          </button>
          <button onClick={() => setShowAddFaculty(!showAddFaculty)} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors">
            {showAddFaculty ? 'Cancel' : 'Add Faculty'}
          </button>
        </div>
      </div>

      {showAddFaculty && (
        <form onSubmit={handleAddFaculty} className="bg-white border p-6 rounded-lg shadow-sm space-y-4 max-w-lg">
          <div>
            <label className="block text-sm font-medium text-gray-700">Faculty Name</label>
            <input required type="text" value={newFaculty.name} onChange={e => setNewFaculty({...newFaculty, name: e.target.value})} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Email Address</label>
            <input required type="email" value={newFaculty.email} onChange={e => setNewFaculty({...newFaculty, email: e.target.value})} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Role</label>
            <select value={newFaculty.role} onChange={e => setNewFaculty({...newFaculty, role: e.target.value})} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
              <option>Teacher</option>
              <option>Admin</option>
              <option>IT Support</option>
            </select>
          </div>
          <button type="submit" className="w-full bg-indigo-600 text-white py-2 px-4 rounded hover:bg-indigo-700 transition">Save Faculty</button>
        </form>
      )}

      {showFaculty && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {faculty.length === 0 ? (
                <tr><td colSpan={4} className="px-6 py-4 text-center text-sm text-gray-500">No faculty members found.</td></tr>
              ) : (
                 faculty.map(f => (
                  <tr key={f.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{f.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{f.email}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{f.role}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button onClick={() => deleteFaculty(f.id)} className="text-red-600 hover:text-red-900 focus:outline-none">
                        Remove
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

    </div>
  )
}
