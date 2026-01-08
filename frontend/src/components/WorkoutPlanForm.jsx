import { useMemo, useState } from 'react'

const TRAINING_DAYS = [
  { key: 'mon', label: 'Thứ 2' },
  { key: 'tue', label: 'Thứ 3' },
  { key: 'wed', label: 'Thứ 4' },
  { key: 'thu', label: 'Thứ 5' },
  { key: 'fri', label: 'Thứ 6' },
  { key: 'sat', label: 'Thứ 7' },
  { key: 'sun', label: 'Chủ nhật' },
]

function WorkoutPlanForm({ onSubmit, loading }) {
  const [formData, setFormData] = useState({
    goal_text: '',
    days_per_week: 4,
    session_minutes: 60,

    sex: '',
    height: '',
    weight: '',
    waist: '',
    hip: '',
    chest: '',

    experience: '',
    equipment: '',
    seed: '',
  })

  // NEW: training_days (optional). Nếu không chọn gì -> BE sẽ tự default.
  const [trainingDays, setTrainingDays] = useState([])
  const [localError, setLocalError] = useState('')

  const numberFields = useMemo(
    () => new Set(['days_per_week', 'session_minutes', 'height', 'weight', 'waist', 'hip', 'chest', 'seed']),
    []
  )

  const daysPerWeekNum = Number(formData.days_per_week) || 0

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: numberFields.has(name) ? value : value,
    }))

    if (name === 'days_per_week') {
      // nếu user đã chọn trainingDays > days_per_week mới -> trim cho khỏi “kẹt”
      const next = Number(value) || 0
      setTrainingDays((prev) => (prev.length > next ? prev.slice(0, next) : prev))
      setLocalError('')
    }
  }

  const toggleTrainingDay = (dayKey) => {
    setTrainingDays((prev) => {
      const exists = prev.includes(dayKey)
      if (exists) {
        setLocalError('')
        return prev.filter((d) => d !== dayKey)
      }
      // nếu đang chọn thủ công, chặn vượt quá days_per_week
      if (daysPerWeekNum > 0 && prev.length >= daysPerWeekNum) {
        setLocalError(`Bạn đang chọn thủ công. Số ngày chọn phải đúng bằng ${daysPerWeekNum}.`)
        return prev
      }
      setLocalError('')
      return [...prev, dayKey]
    })
  }

  const clearTrainingDays = () => {
    setTrainingDays([])
    setLocalError('')
  }

  const buildPayload = () => {
    const p = {
      goal_text: (formData.goal_text || '').trim(),
      days_per_week: Number(formData.days_per_week),
      session_minutes: Number(formData.session_minutes),
    }

    if (formData.sex) p.sex = formData.sex
    if (formData.experience) p.experience = formData.experience
    if ((formData.equipment || '').trim()) p.equipment = formData.equipment.trim()

    const maybeNumber = (v) => {
      if (v === null || v === undefined) return undefined
      const s = String(v).trim()
      if (!s) return undefined
      const n = Number(s)
      return Number.isFinite(n) ? n : undefined
    }

    const height = maybeNumber(formData.height)
    const weight = maybeNumber(formData.weight)
    const waist = maybeNumber(formData.waist)
    const hip = maybeNumber(formData.hip)
    const chest = maybeNumber(formData.chest)
    const seed = maybeNumber(formData.seed)

    if (height !== undefined) p.height = height
    if (weight !== undefined) p.weight = weight
    if (waist !== undefined) p.waist = waist
    if (hip !== undefined) p.hip = hip
    if (chest !== undefined) p.chest = chest
    if (seed !== undefined) p.seed = Math.trunc(seed)

    // NEW: chỉ gửi training_days nếu user có chọn thủ công
    if (trainingDays.length > 0) {
      p.training_days = trainingDays
    }

    return p
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setLocalError('')

    const payload = buildPayload()
    if (!payload.goal_text) return

    // Nếu user chọn thủ công => bắt buộc đúng bằng days_per_week
    if (trainingDays.length > 0 && trainingDays.length !== payload.days_per_week) {
      setLocalError(`Số ngày tập đã chọn (${trainingDays.length}) phải đúng bằng days_per_week (${payload.days_per_week}).`)
      return
    }

    onSubmit?.(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow p-6 space-y-5">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Tạo Workout Plan</h2>
        <p className="text-sm text-gray-500 mt-1">
          Nhập mục tiêu tự do (goal_text) + lịch tập/tuần. training_days là tuỳ chọn; nếu bỏ trống hệ thống sẽ tự sinh lịch mặc định.
        </p>
      </div>

      {localError && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-lg">
          {localError}
        </div>
      )}

      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">Mục tiêu (goal_text)</label>
        <textarea
          name="goal_text"
          value={formData.goal_text}
          onChange={handleChange}
          rows={3}
          placeholder="Ví dụ: Giảm mỡ, rõ cơ bụng, vai rộng hơn. Tập 4 buổi/tuần, 60 phút/buổi."
          className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Số buổi/tuần (days_per_week)</label>
          <input
            type="number"
            name="days_per_week"
            min={1}
            max={7}
            value={formData.days_per_week}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Thời lượng/buổi (session_minutes)</label>
          <input
            type="number"
            name="session_minutes"
            min={10}
            max={240}
            value={formData.session_minutes}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* NEW: training_days selector */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <label className="block text-sm font-medium text-gray-700">
            Chọn thứ tập (training_days) <span className="text-gray-400 font-normal">(tuỳ chọn)</span>
          </label>
          <button
            type="button"
            onClick={clearTrainingDays}
            className="text-sm text-indigo-600 hover:text-indigo-800"
            disabled={loading}
          >
            Bỏ chọn (auto)
          </button>
        </div>

        <p className="text-xs text-gray-500">
          Nếu bạn chọn thủ công: số ngày chọn phải đúng bằng <b>{daysPerWeekNum || 0}</b>. Nếu không chọn gì, backend sẽ tự sinh lịch mặc định.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
          {TRAINING_DAYS.map((d) => {
            const active = trainingDays.includes(d.key)
            return (
              <button
                key={d.key}
                type="button"
                onClick={() => toggleTrainingDay(d.key)}
                disabled={loading}
                className={[
                  'px-3 py-2 rounded-lg border text-sm transition-colors',
                  active
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50',
                ].join(' ')}
              >
                {d.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Giới tính (tuỳ chọn)</label>
          <select
            name="sex"
            value={formData.sex}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Không chọn</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Kinh nghiệm (tuỳ chọn)</label>
          <select
            name="experience"
            value={formData.experience}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Không chọn</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Chiều cao (cm)</label>
          <input
            type="number"
            name="height"
            min={0}
            value={formData.height}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Cân nặng (kg)</label>
          <input
            type="number"
            name="weight"
            min={0}
            value={formData.weight}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Vòng eo (cm)</label>
          <input
            type="number"
            name="waist"
            min={0}
            value={formData.waist}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Vòng mông (cm)</label>
          <input
            type="number"
            name="hip"
            min={0}
            value={formData.hip}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Vòng ngực (cm)</label>
          <input
            type="number"
            name="chest"
            min={0}
            value={formData.chest}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Seed (tuỳ chọn)</label>
          <input
            type="number"
            name="seed"
            value={formData.seed}
            onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">Thiết bị (tuỳ chọn, phân tách bằng dấu phẩy)</label>
        <input
          type="text"
          name="equipment"
          value={formData.equipment}
          onChange={handleChange}
          placeholder="Ví dụ: dumbbell, pullup_bar, resistance_band"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <button
        type="submit"
        disabled={loading || !String(formData.goal_text || '').trim()}
        className="w-full bg-indigo-600 text-white py-3 px-4 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? 'Đang tạo workout plan...' : 'Tạo Workout Plan'}
      </button>
    </form>
  )
}

export default WorkoutPlanForm
