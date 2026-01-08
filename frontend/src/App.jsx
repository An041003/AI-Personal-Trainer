import { useState } from 'react'
import WorkoutPlanForm from './components/WorkoutPlanForm'
import WorkoutPlanResult from './components/WorkoutPlanResult'

function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (formData) => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch('/api/backend/plan/generate-agent/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Có lỗi xảy ra khi tạo workout plan')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      if (err.message.includes('Failed to fetch') || err.message.includes('ECONNREFUSED')) {
        setError('Không thể kết nối đến backend. Vui lòng đảm bảo Django server đang chạy tại http://localhost:8000')
      } else {
        setError(err.message)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold text-center text-gray-800 mb-2">
            AI Personal Trainer
          </h1>
          <p className="text-center text-gray-600 mb-8">
            Tạo kế hoạch tập luyện cá nhân hóa với AI
          </p>

          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <WorkoutPlanForm onSubmit={handleSubmit} loading={loading} />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
              <p className="font-semibold">Lỗi:</p>
              <p>{error}</p>
            </div>
          )}

          {result && <WorkoutPlanResult result={result} />}
        </div>
      </div>
    </div>
  )
}

export default App

