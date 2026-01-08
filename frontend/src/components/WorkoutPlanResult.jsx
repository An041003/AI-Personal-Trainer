// Component để render JSON value
function JsonValue({ value, level = 0 }) {
  if (value === null) {
    return <span className="text-gray-500">null</span>
  }

  if (typeof value === 'string') {
    return <span className="text-green-700">"{value}"</span>
  }

  if (typeof value === 'number') {
    return <span className="text-blue-600">{value}</span>
  }

  if (typeof value === 'boolean') {
    return <span className="text-purple-600">{value.toString()}</span>
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-gray-500">[]</span>
    }
    return (
      <div className="ml-4 border-l-2 border-gray-300 pl-4">
        {value.map((item, index) => (
          <div key={index} className="mb-2">
            <span className="text-gray-500">[{index}]</span>
            <div className="ml-4">
              <JsonValue value={item} level={level + 1} />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (typeof value === 'object') {
    const keys = Object.keys(value)
    if (keys.length === 0) {
      return <span className="text-gray-500">{'{}'}</span>
    }
    return (
      <div className="ml-4 border-l-2 border-gray-300 pl-4 space-y-2">
        {keys.map((key) => (
          <div key={key} className="mb-2">
            <span className="text-indigo-600 font-semibold">"{key}":</span>
            <div className="ml-4">
              <JsonValue value={value[key]} level={level + 1} />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return <span>{String(value)}</span>
}

// Component để render Workout Plan có cấu trúc
function WorkoutPlanDisplay({ plan }) {
  if (typeof plan === 'string') {
    return (
      <div className="bg-gray-50 rounded-lg p-4">
        <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
          {plan}
        </pre>
      </div>
    )
  }

  if (typeof plan === 'object' && plan !== null) {
    return (
      <div className="bg-gray-50 rounded-lg p-4 overflow-x-auto">
        <div className="space-y-4">
          {plan.goal && (
            <div className="bg-white p-3 rounded border">
              <span className="font-semibold text-indigo-600">Mục tiêu:</span>
              <span className="ml-2 text-gray-700 capitalize">{plan.goal}</span>
            </div>
          )}

          {plan.days_per_week && (
            <div className="bg-white p-3 rounded border">
              <span className="font-semibold text-indigo-600">Số ngày tập/tuần:</span>
              <span className="ml-2 text-gray-700">{plan.days_per_week}</span>
            </div>
          )}

          {plan.session_minutes && (
            <div className="bg-white p-3 rounded border">
              <span className="font-semibold text-indigo-600">Thời gian mỗi buổi:</span>
              <span className="ml-2 text-gray-700">{plan.session_minutes} phút</span>
            </div>
          )}

          {plan.split && (
            <div className="bg-white p-3 rounded border">
              <span className="font-semibold text-indigo-600">Split:</span>
              <span className="ml-2 text-gray-700">{plan.split}</span>
            </div>
          )}

          {plan.days && Array.isArray(plan.days) && plan.days.length > 0 && (
            <div className="space-y-4">
              <h4 className="font-semibold text-indigo-600 text-lg">Lịch tập theo ngày:</h4>
              {plan.days.map((dayPlan, dayIndex) => (
                <div key={dayIndex} className="bg-white p-4 rounded border border-indigo-200">
                  <h5 className="font-bold text-lg text-indigo-700 mb-3">
                    {dayPlan.day || `Ngày ${dayIndex + 1}`}
                  </h5>
                  {dayPlan.exercises && Array.isArray(dayPlan.exercises) && (
                    <div className="space-y-3">
                      {dayPlan.exercises.map((exercise, exIndex) => (
                        <div key={exIndex} className="bg-gray-50 p-4 rounded border-l-4 border-indigo-400">
                          <div className="flex flex-col md:flex-row gap-4">
                            {/* Phần ảnh */}
                            {exercise.image_url && (
                              <div className="flex-shrink-0">
                                <div className="relative w-full md:w-48 h-48 rounded-lg border border-gray-300 shadow-sm overflow-hidden bg-gray-100">
                                  <img
                                    src={exercise.image_url}
                                    alt={exercise.title || `Exercise ${exercise.exercise_id}`}
                                    className="w-full h-full object-cover"
                                    onError={(e) => {
                                      e.target.style.display = 'none'
                                      const parent = e.target.parentElement
                                      if (parent) {
                                        parent.innerHTML = '<div class="w-full h-full flex items-center justify-center text-gray-400 text-sm">Không tải được ảnh</div>'
                                      }
                                    }}
                                    loading="lazy"
                                  />
                                </div>
                              </div>
                            )}

                            {/* Phần thông tin */}
                            <div className="flex-1">
                              {exercise.title && (
                                <h6 className="font-bold text-lg text-indigo-700 mb-2">
                                  {exercise.title}
                                </h6>
                              )}

                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-2">
                                <div>
                                  <span className="font-semibold text-gray-600">Exercise ID:</span>
                                  <span className="ml-2 text-gray-800">{exercise.exercise_id}</span>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Sets:</span>
                                  <span className="ml-2 text-gray-800">{exercise.sets}</span>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Reps:</span>
                                  <span className="ml-2 text-gray-800">{exercise.reps}</span>
                                </div>
                                <div>
                                  <span className="font-semibold text-gray-600">Nghỉ:</span>
                                  <span className="ml-2 text-gray-800">{exercise.rest_sec}s</span>
                                </div>
                              </div>

                              {exercise.muscle_groups && Array.isArray(exercise.muscle_groups) && exercise.muscle_groups.length > 0 && (
                                <div className="mb-2 text-sm">
                                  <span className="font-semibold text-gray-600">Nhóm cơ:</span>
                                  <span className="ml-2 text-gray-800">
                                    {exercise.muscle_groups.join(', ')}
                                  </span>
                                </div>
                              )}

                              {exercise.notes && (
                                <div className="mt-2 text-sm text-gray-600">
                                  <span className="font-semibold">Ghi chú:</span>
                                  <span className="ml-2">{exercise.notes}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Hiển thị các trường khác nếu có */}
          {Object.keys(plan).filter(key => !['goal', 'days_per_week', 'session_minutes', 'split', 'days'].includes(key)).length > 0 && (
            <details className="mt-4">
              <summary className="cursor-pointer font-semibold text-gray-700 mb-2">
                Các trường khác
              </summary>
              <div className="bg-white p-3 rounded border mt-2">
                <JsonValue value={Object.fromEntries(
                  Object.entries(plan).filter(([key]) =>
                    !['goal', 'days_per_week', 'session_minutes', 'split', 'days'].includes(key)
                  )
                )} />
              </div>
            </details>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
        {JSON.stringify(plan, null, 2)}
      </pre>
    </div>
  )
}

function WorkoutPlanResult({ result }) {
  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-semibold text-gray-800 mb-4">
        Kết quả Workout Plan
      </h2>

      {result.request_id && (
        <div className="mb-4 p-3 bg-indigo-50 rounded-lg border border-indigo-200">
          <p className="text-sm text-gray-700">
            <span className="font-semibold text-indigo-600">Request ID:</span>
            <span className="ml-2 font-mono text-xs">{result.request_id}</span>
          </p>
        </div>
      )}

      {result.warnings && result.warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg mb-4">
          <p className="font-semibold mb-2">⚠️ Cảnh báo:</p>
          <ul className="list-disc list-inside space-y-1">
            {result.warnings.map((warning, index) => (
              <li key={index}>
                {typeof warning === 'string'
                  ? warning
                  : (warning && typeof warning === 'object'
                    ? (warning.detail || warning.message || JSON.stringify(warning))
                    : String(warning))}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.issues && result.issues.length > 0 && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg mb-4">
          <p className="font-semibold mb-2">❌ Vấn đề:</p>
          <ul className="list-disc list-inside space-y-1">
            {result.issues.map((issue, index) => (
              <li key={index}>
                {typeof issue === 'string'
                  ? issue
                  : (issue && typeof issue === 'object'
                    ? (issue.detail || issue.message || JSON.stringify(issue))
                    : String(issue))}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.plan && (
        <div className="mt-4">
          <h3 className="text-xl font-semibold text-gray-800 mb-3">📋 Plan chi tiết:</h3>
          <WorkoutPlanDisplay plan={result.plan} />
        </div>
      )}

      {result.audit && (
        <div className="mt-4">
          <details className="bg-gray-50 rounded-lg p-4">
            <summary className="cursor-pointer font-semibold text-gray-700 hover:text-indigo-600">
              🔍 Xem thông tin audit (JSON)
            </summary>
            <div className="mt-2 bg-white p-3 rounded border overflow-x-auto">
              <JsonValue value={result.audit} />
            </div>
          </details>
        </div>
      )}

      {/* Hiển thị toàn bộ JSON nếu muốn xem raw data */}
      <div className="mt-4">
        <details className="bg-gray-50 rounded-lg p-4">
          <summary className="cursor-pointer font-semibold text-gray-700 hover:text-indigo-600 text-sm">
            📄 Xem toàn bộ JSON response
          </summary>
          <div className="mt-2 bg-white p-3 rounded border overflow-x-auto">
            <pre className="text-xs text-gray-600 font-mono whitespace-pre-wrap">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </details>
      </div>
    </div>
  )
}

export default WorkoutPlanResult

