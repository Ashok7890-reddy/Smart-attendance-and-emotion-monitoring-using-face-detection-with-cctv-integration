import React, { useState } from 'react'
import { FaceRecognitionSettings } from '@/components/Settings/FaceRecognitionSettings'
import { CogIcon, EyeIcon, ChartBarIcon, UserGroupIcon } from '@heroicons/react/24/outline'

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'face-recognition' | 'system' | 'analytics' | 'users'>('face-recognition')

  const tabs = [
    { id: 'face-recognition', name: 'Face Recognition', icon: EyeIcon },
    { id: 'system', name: 'System', icon: CogIcon },
    { id: 'analytics', name: 'Analytics', icon: ChartBarIcon },
    { id: 'users', name: 'Users', icon: UserGroupIcon },
  ]

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-lg">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon
                    className={`-ml-0.5 mr-2 h-5 w-5 ${
                      activeTab === tab.id ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'
                    }`}
                  />
                  {tab.name}
                </button>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      <div className="min-h-[600px]">
        {activeTab === 'face-recognition' && <FaceRecognitionSettings />}
        
        {activeTab === 'system' && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center mb-6">
              <CogIcon className="h-6 w-6 text-primary-600 mr-3" />
              <h2 className="text-xl font-semibold text-gray-900">System Configuration</h2>
            </div>
            
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Camera Settings</h3>
                  <p className="text-sm text-gray-600 mb-4">Configure camera capture intervals and quality settings.</p>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Gate Camera Interval</label>
                      <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                        <option>3 seconds</option>
                        <option>5 seconds</option>
                        <option>10 seconds</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Classroom Camera Interval</label>
                      <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                        <option>5 seconds</option>
                        <option>10 seconds</option>
                        <option>15 seconds</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Recognition Thresholds</h3>
                  <p className="text-sm text-gray-600 mb-4">Adjust recognition sensitivity and accuracy thresholds.</p>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">ONNX Threshold</label>
                      <input type="range" min="0.7" max="0.95" step="0.05" defaultValue="0.85" className="w-full" />
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>70%</span>
                        <span>85%</span>
                        <span>95%</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">face-api.js Threshold</label>
                      <input type="range" min="0.4" max="0.8" step="0.05" defaultValue="0.60" className="w-full" />
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>40%</span>
                        <span>60%</span>
                        <span>80%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="text-sm font-medium text-blue-800 mb-2">System Information</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-blue-600 font-medium">Version:</span>
                    <p className="text-blue-800">v2.0.0</p>
                  </div>
                  <div>
                    <span className="text-blue-600 font-medium">Build:</span>
                    <p className="text-blue-800">Enhanced</p>
                  </div>
                  <div>
                    <span className="text-blue-600 font-medium">Models:</span>
                    <p className="text-blue-800">ONNX + face-api.js</p>
                  </div>
                  <div>
                    <span className="text-blue-600 font-medium">Runtime:</span>
                    <p className="text-blue-800">WASM Optimized</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center mb-6">
              <ChartBarIcon className="h-6 w-6 text-primary-600 mr-3" />
              <h2 className="text-xl font-semibold text-gray-900">Analytics Configuration</h2>
            </div>
            
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Emotion Detection</h3>
                  <p className="text-sm text-gray-600 mb-4">Configure emotion analysis and engagement tracking.</p>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">Enable Emotion Detection</span>
                      <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-primary-600">
                        <span className="inline-block h-4 w-4 transform rounded-full bg-white translate-x-6" />
                      </button>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">Real-time Engagement Scoring</span>
                      <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-primary-600">
                        <span className="inline-block h-4 w-4 transform rounded-full bg-white translate-x-6" />
                      </button>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Performance Tracking</h3>
                  <p className="text-sm text-gray-600 mb-4">Monitor system performance and accuracy metrics.</p>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">Detailed Performance Logging</span>
                      <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-primary-600">
                        <span className="inline-block h-4 w-4 transform rounded-full bg-white translate-x-6" />
                      </button>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">Model Usage Analytics</span>
                      <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-primary-600">
                        <span className="inline-block h-4 w-4 transform rounded-full bg-white translate-x-6" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'users' && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center mb-6">
              <UserGroupIcon className="h-6 w-6 text-primary-600 mr-3" />
              <h2 className="text-xl font-semibold text-gray-900">User Management</h2>
            </div>
            
            <div className="space-y-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-lg font-medium text-gray-900 mb-2">Student Database</h3>
                <p className="text-sm text-gray-600 mb-4">Manage registered students and their face recognition data.</p>
                
                <div className="flex flex-wrap gap-3">
                  <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
                    View All Students
                  </button>
                  <button className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
                    Export Student Data
                  </button>
                  <button className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors">
                    Backup Database
                  </button>
                  <button className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors">
                    Clear All Data
                  </button>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-lg font-medium text-gray-900 mb-2">Faculty Access</h3>
                <p className="text-sm text-gray-600 mb-4">Manage faculty accounts and permissions.</p>
                
                <div className="flex flex-wrap gap-3">
                  <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
                    View Faculty
                  </button>
                  <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors">
                    Add Faculty
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}