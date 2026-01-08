# AI Personal Trainer - Frontend

Frontend cho ứng dụng AI Personal Trainer được xây dựng với React, Vite và TailwindCSS.

## Cài đặt

```bash
cd frontend
npm install
```

## Chạy ứng dụng

```bash
npm run dev
```

Ứng dụng sẽ chạy tại `http://localhost:3000`

## Build cho production

```bash
npm run build
```

## Cấu trúc

- `src/App.jsx` - Component chính
- `src/components/WorkoutPlanForm.jsx` - Form nhập thông tin workout plan
- `src/components/WorkoutPlanResult.jsx` - Component hiển thị kết quả

## API Endpoints

Frontend gọi API tại:
- `POST /api/workout/plan/generate-agent/` - Tạo workout plan


