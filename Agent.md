# Agent.md — Hướng dẫn AI code lại dự án AI Personal Trainer từ đầu

> Mục tiêu: dùng file này làm chỉ dẫn chính cho AI coding agent để dựng lại toàn bộ dự án từ máy trắng. Agent chỉ cần 4 tư liệu nền: `Agent.md`, `Architecture.md`, `exercises.csv`, `nutrition_atoms_seed.csv`.

---

## 0. Nguyên tắc phục dựng

Dự án phải được **xây lại từ đầu**, không code chắp vá từ trạng thái cũ. Tuy nhiên phải giữ đúng định hướng sản phẩm đã thống nhất:

- Backend: Django + Django REST Framework.
- Database: PostgreSQL + pgvector.
- LLM: toàn bộ luồng AI dùng OpenAI.
- Embedding/RAG: dùng OpenAI Embeddings.
- Frontend: React + Vite + Tailwind CSS.
- Seed bài tập: dùng `exercises.csv`.
- Seed nguyên liệu: dùng `nutrition_atoms_seed.csv`.
- Workout phải có bước **intent analysis riêng**, không gộp vào prompt generate plan.
- Nutrition dùng truy vấn nguyên liệu cơ bản, không cần RAG phức tạp.
- Chỉ số cơ thể nhập ở trang Profile.
- Trang Profile cần có prompt AI đưa lời khuyên dựa trên chỉ số cơ thể, mục tiêu và bệnh lý/hạn chế.

---

## 1. Stack kỹ thuật bắt buộc

### Backend

- Python 3.11+
- Django
- Django REST Framework
- PostgreSQL
- pgvector
- OpenAI Python SDK
- python-dotenv / django-environ
- django-cors-headers
- drf-spectacular
- Pillow cho avatar

### Frontend

- React 18+
- Vite
- Tailwind CSS
- React Router
- Axios hoặc fetch wrapper
- lucide-react hoặc Feather-style icons

### Database

- PostgreSQL là database chính ngay từ đầu.
- Bật extension `vector` để lưu embedding bài tập.
- Không dùng SQLite làm MVP chính.

---

## 2. Cấu trúc repo đề xuất

```text
ai-personal-trainer/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── seed/
│   │   ├── exercises.csv
│   │   └── nutrition_atoms_seed.csv
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   └── apps/
│       ├── accounts/
│       ├── profiles/
│       ├── workout/
│       ├── nutrition/
│       └── common/
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       ├── components/
│       ├── pages/
│       ├── layouts/
│       └── styles/
├── Agent.md
├── Architecture.md
└── README.md
```

Nếu muốn làm nhanh hơn, có thể dùng một Django app tên `backend`, nhưng cấu trúc nhiều app như trên dễ bảo trì hơn.

---

## 3. Bootstrap project từ số 0

### 3.1. Tạo repo

```bash
mkdir ai-personal-trainer
cd ai-personal-trainer
git init
mkdir backend frontend
```

### 3.2. Tạo backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

django-admin startproject config .
python manage.py startapp accounts apps/accounts
python manage.py startapp profiles apps/profiles
python manage.py startapp workout apps/workout
python manage.py startapp nutrition apps/nutrition
python manage.py startapp common apps/common
```

Nếu `startapp accounts apps/accounts` lỗi do thư mục chưa tồn tại thì tạo thủ công:

```bash
mkdir -p apps/accounts apps/profiles apps/workout apps/nutrition apps/common
python manage.py startapp accounts apps/accounts
```

### 3.3. Tạo frontend

```bash
cd ../frontend
npm create vite@latest . -- --template react
npm install
npm install react-router-dom axios lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Cấu hình `tailwind.config.js`:

```js
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

`src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

---

## 4. PostgreSQL setup

### 4.1. Tạo database và user

Mở SQL Shell hoặc pgAdmin, chạy:

```sql
CREATE DATABASE aipt_db;
CREATE USER aipt_user WITH PASSWORD 'aipt_password';
ALTER ROLE aipt_user SET client_encoding TO 'utf8';
ALTER ROLE aipt_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE aipt_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE aipt_db TO aipt_user;
```

Kết nối vào database `aipt_db` rồi bật pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Nếu user không có quyền tạo extension, dùng postgres superuser bật extension trước.

### 4.2. `.env.example`

Tạo `backend/.env.example`:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=aipt_db
DB_USER=aipt_user
DB_PASSWORD=aipt_password
DB_HOST=127.0.0.1
DB_PORT=5432

OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBED_MODEL=text-embedding-3-small
OPENAI_EMBED_DIM=1536

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Tạo file `.env` thật từ `.env.example`, sau đó user sẽ tự điền `OPENAI_API_KEY`.

---

## 5. `requirements.txt`

File `backend/requirements.txt` phải khớp với file đi kèm, tối thiểu có:

```txt
django
djangorestframework
django-cors-headers
drf-spectacular
psycopg[binary]
pgvector
python-dotenv
django-environ
openai
pydantic
numpy
pandas
Pillow
rapidfuzz
```

---

## 6. Django settings bắt buộc

Trong `config/settings.py`:

- Đọc `.env`.
- Cài app:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'drf_spectacular',
    'pgvector.django',

    'apps.accounts',
    'apps.profiles',
    'apps.workout',
    'apps.nutrition',
    'apps.common',
]
```

Middleware phải có `corsheaders.middleware.CorsMiddleware` trước `CommonMiddleware`.

REST Framework:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

Database:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}
```

---

## 7. Models cần tạo

### 7.1. accounts

Dùng Django `User` mặc định để nhanh. Không custom user nếu không cần.

### 7.2. profiles.UserProfile

Các chỉ số cơ thể nhập tại Profile:

- user OneToOne
- full_name
- avatar
- sex: male/female
- birth_year hoặc age
- height_cm
- weight_kg
- waist_cm
- neck_cm
- hip_cm
- activity_level: sedentary/light/moderate/very_active/athlete
- experience_level: beginner/intermediate/advanced
- goal_type: cut/bulk/recomp/maintain
- goal_text
- created_at, updated_at

### 7.3. profiles.UserPreferences

- user OneToOne
- dietary_style: none/vegetarian/vegan/halal/low_carb/keto/mediterranean
- allergies JSON list
- disliked_foods JSON list
- favorite_foods JSON list
- avoid_ingredients JSON list
- medical_conditions JSON list
- notes

### 7.4. workout.Exercise

Dùng `exercises.csv` seed.

Fields:

- title
- body_part_raw
- muscle_groups JSON list
- equipment JSON list, có thể infer từ title
- level default beginner/intermediate
- image_url
- image_file
- embedding VectorField(1536), null
- embedding_text
- embedding_model
- created_at

Index HNSW:

```python
from pgvector.django import VectorField, HnswIndex

class Meta:
    indexes = [
        HnswIndex(
            name='wk_ex_emb_hnsw',
            fields=['embedding'],
            m=16,
            ef_construction=64,
            opclasses=['vector_cosine_ops'],
        )
    ]
```

### 7.5. nutrition.NutritionAtom

Dùng `nutrition_atoms_seed.csv` seed.

Fields:

- canonical_name unique
- display_name_vi
- category
- food_role
- edible_form
- kcal_per_100g
- protein_g_per_100g
- carb_g_per_100g
- fat_g_per_100g
- fiber_g_per_100g
- sodium_mg_per_100g
- default_serving_g
- aliases text, phân tách bằng `|`
- source
- is_active
- created_at, updated_at

### 7.6. Plan và PlanAudit

Có thể tạo app `common` hoặc để trong từng domain.

`Plan`:

- user FK
- plan_type: workout/nutrition/full
- title
- payload JSON
- created_at

`PlanAudit`:

- plan FK nullable
- request_id
- domain
- step
- payload JSON
- created_at

---

## 8. Seed database

### 8.1. Copy seed files

Đặt:

```text
backend/seed/exercises.csv
backend/seed/nutrition_atoms_seed.csv
```

`exercises.csv` có header:

```csv
title,body_part,image_url,image_file
```

`nutrition_atoms_seed.csv` có header:

```csv
canonical_name,display_name_vi,category,food_role,edible_form,kcal_per_100g,protein_g_per_100g,carb_g_per_100g,fat_g_per_100g,fiber_g_per_100g,sodium_mg_per_100g,default_serving_g,aliases,source,is_active
```

### 8.2. Management command `import_exercises`

Tạo `apps/workout/management/commands/import_exercises.py`.

Yêu cầu:

- Đọc CSV.
- Map `body_part` sang `muscle_groups`.
- Infer equipment từ title.
- Upsert theo `title`.
- Không gọi OpenAI trong bước import.

Body part mapping tối thiểu:

```python
BODY_PART_TO_MUSCLES = {
    'Chest': ['chest'],
    'Back': ['back'],
    'Shoulders': ['shoulders'],
    'Upper Arms': ['biceps', 'triceps'],
    'Triceps, Upper Arms': ['triceps'],
    'Biceps, Upper Arms': ['biceps'],
    'Thighs': ['quadriceps', 'hamstrings', 'glutes'],
    'Quadriceps, Thighs': ['quadriceps'],
    'Hamstrings, Thighs': ['hamstrings'],
    'Hips': ['glutes'],
    'Waist': ['core'],
    'Calves': ['calves'],
    'Cardio': ['cardio'],
}
```

Command:

```bash
python manage.py import_exercises --csv seed/exercises.csv
```

### 8.3. Management command `seed_nutrition_atoms`

Tạo `apps/nutrition/management/commands/seed_nutrition_atoms.py`.

Yêu cầu:

- Đọc CSV.
- Upsert theo `canonical_name`.
- Convert số đúng kiểu Decimal/float.
- `is_active` đọc `1/0`, `true/false`.

Command:

```bash
python manage.py seed_nutrition_atoms --csv seed/nutrition_atoms_seed.csv
```

### 8.4. Backfill embedding bài tập

Tạo command:

```bash
python manage.py backfill_exercise_embeddings --batch-size 64
```

Yêu cầu:

- Dùng `OPENAI_EMBED_MODEL=text-embedding-3-small`.
- Lưu vector 1536 chiều.
- Text embedding:

```text
{title} | muscles={muscle_groups} | body_part={body_part_raw} | equipment={equipment}
```

Nếu chưa có OpenAI key thì bỏ qua được, nhưng endpoint workout generate AI sẽ chưa chạy RAG semantic chuẩn.

---

## 9. Luồng Workout bắt buộc

Workout không được generate thẳng từ goal text. Phải tách 2 bước:

```text
User goal/profile
→ Intent Analysis API
→ internal_goal/focus_muscles/training_days
→ Generate Workout API
→ Retrieval RAG bằng focus_muscles
→ OpenAI generate plan
→ Evaluate
→ Repair nếu lỗi
→ Enrich metadata
→ FE hiển thị
```

---

## 10. Workout Intent Analysis

### 10.1. Endpoint

```http
POST /api/workout/intent/analyze/
```

Input:

```json
{
  "goal_text": "giảm mỡ, vai rộng, rõ cơ bụng",
  "days_per_week": 4,
  "session_minutes": 60,
  "training_days": ["mon", "wed", "fri", "sat"],
  "experience_level": "beginner",
  "equipment": ["dumbbell", "bench"]
}
```

Output:

```json
{
  "goal_style": "fat_loss",
  "priority_targets": ["vai rộng", "bụng rõ"],
  "focus_muscles": ["shoulders", "core", "chest", "back"],
  "training_days": ["mon", "wed", "fri", "sat"],
  "weekly_focus_by_day": [
    {"day": "mon", "focus": ["chest", "triceps", "shoulders"]},
    {"day": "wed", "focus": ["back", "biceps", "core"]},
    {"day": "fri", "focus": ["legs", "glutes", "core"]},
    {"day": "sat", "focus": ["shoulders", "chest", "core"]}
  ],
  "risk_notes": [],
  "raw_reasoning_summary": "..."
}
```

Không trả chain-of-thought dài. Chỉ trả summary ngắn.

### 10.2. OpenAI prompt intent

System:

```text
You are a fitness intent parser. Convert user goals into structured training intent. Do not create a workout plan. Only classify goal style, focus muscles, training days, and risk notes. Return strict JSON only.
```

User prompt gồm:

- profile
- goal_text
- days_per_week
- session_minutes
- training_days nếu có
- equipment
- injury nếu có
- muscle taxonomy

Muscle taxonomy cố định:

```text
chest, back, shoulders, biceps, triceps, forearms, core, quadriceps, hamstrings, glutes, calves, cardio, full_body
```

Goal style enum:

```text
fat_loss, hypertrophy, strength, endurance, mobility, health, body_recomposition, mixed
```

---

## 11. Workout Generate

### 11.1. Endpoint

```http
POST /api/workout/plan/generate/
```

Input nhận `internal_goal` từ bước intent:

```json
{
  "profile": {...},
  "internal_goal": {...},
  "constraints": {
    "max_exercises_per_day": 6,
    "max_repair_iterations": 2
  }
}
```

Output:

```json
{
  "request_id": "uuid",
  "plan": {
    "goal": "fat_loss",
    "days_per_week": 4,
    "session_minutes": 60,
    "split": "upper/lower + focus",
    "days": [
      {
        "day": "mon",
        "title": "Upper Push + Shoulders",
        "exercises": [
          {
            "exercise_id": 1,
            "title": "Bench Press",
            "sets": 4,
            "reps": "8-12",
            "rest_sec": 90,
            "notes": "Keep 1-2 reps in reserve",
            "muscle_groups": ["chest"],
            "image_url": "..."
          }
        ]
      }
    ]
  },
  "warnings": [],
  "issues": [],
  "audit": {...}
}
```

### 11.2. Retrieval RAG workout

Dùng OpenAI embeddings:

- Khi seed/backfill: embed từng Exercise.
- Khi generate: embed query tạo từ `goal_style + focus_muscles + equipment + experience`.
- Filter cơ bản theo `focus_muscles` và equipment nếu có.
- Dùng pgvector similarity search.
- Top K khoảng 50–80 bài.
- Không gửi toàn bộ database vào prompt.

Retrieval query mẫu:

```text
fat_loss hypertrophy workout for shoulders core chest back beginner dumbbell bench
```

Candidate gửi vào OpenAI dạng ngắn:

```text
id=12 | title=Dumbbell Lateral Raise | muscles=shoulders | equipment=dumbbell | level=beginner
```

### 11.3. OpenAI plan prompt

System:

```text
You are a certified personal trainer. Generate a safe weekly workout plan using only the provided candidate exercise IDs. Return strict JSON matching the schema. Do not invent exercise IDs. Do not include exercises outside candidates.
```

Rules:

- Chỉ dùng `exercise_id` trong candidate pack.
- Mỗi ngày 4–6 bài.
- Rest hợp lý.
- Sets/reps phù hợp level.
- Không lặp 1 bài quá nhiều lần/tuần.
- Ưu tiên focus muscle từ intent.
- Nếu equipment thiếu thì dùng bodyweight/cable/machine phù hợp dữ liệu.
- Với beginner tránh volume quá cao.

### 11.4. Evaluator workout

Kiểm tra:

- `exercise_id` có trong candidate IDs không.
- Số bài/ngày trong min/max.
- Số ngày bằng `days_per_week`.
- Không vượt quá `session_minutes` quá nhiều.
- Focus muscle chính có xuất hiện trong tuần không.
- Không lặp cùng exercise vượt ngưỡng.

Nếu lỗi hard issue: repair tối đa 2 lần bằng OpenAI, gửi lại issue list + previous plan.

---

## 12. Nutrition: yêu cầu tổng thể

Nutrition gồm 3 phần chính:

```text
Profile body metrics
→ Rulebase targets + disease/diet restrictions
→ OpenAI meal prompt
→ Basic ingredient lookup từ NutritionAtom
→ Calculate totals
→ Optimize grams
→ Evaluate
→ Return meal plan + warnings + shopping list
```

Không cần RAG phức tạp cho nguyên liệu. Chỉ dùng truy vấn cơ bản theo:

- exact canonical_name
- aliases contains
- display_name_vi contains
- fuzzy match bằng rapidfuzz nếu cần
- filter category/food_role nếu prompt có role protein/carb/fat/veg

---

## 13. Nutrition Profile Metrics

### 13.1. Endpoint

```http
POST /api/nutrition/metrics/
```

Input nên lấy từ Profile, không bắt user nhập lại ở Nutrition:

```json
{
  "sex": "male",
  "age": 21,
  "height_cm": 170,
  "weight_kg": 70,
  "waist_cm": 80,
  "neck_cm": 38,
  "hip_cm": null,
  "activity_level": "moderate"
}
```

Output:

```json
{
  "bmi": 24.22,
  "bmr_kcal": 1650,
  "tdee_kcal": 2550,
  "bodyfat_percent": 18.5,
  "bodyfat_method": "us_navy",
  "whtr": 0.47,
  "notes": {...}
}
```

### 13.2. Công thức

BMR Mifflin-St Jeor:

- Male: `10w + 6.25h - 5a + 5`
- Female: `10w + 6.25h - 5a - 161`

PAL:

- sedentary: 1.2
- light: 1.375
- moderate: 1.55
- very_active: 1.725
- athlete: 1.9

TDEE = BMR × PAL.

Body fat nếu đủ vòng đo thì dùng US Navy:

- Male cần waist, neck, height.
- Female cần waist, neck, hip, height.
- Nếu thiếu thì trả `null` và note rõ.

---

## 14. Nutrition Rulebase

Rulebase là phần deterministic, không dùng LLM để quyết định số liệu chính.

### 14.1. Endpoint preview

```http
POST /api/nutrition/rulebase/preview/
```

Input:

```json
{
  "metrics": {...},
  "goal": {
    "goal_type": "cut",
    "goal_mode": "standard"
  },
  "preferences": {...},
  "medical": {...},
  "restriction_levels": {
    "protein_level": 0,
    "carbs_level": 0,
    "fat_level": 0
  }
}
```

Output:

```json
{
  "derived_targets": {
    "calorie_target_kcal": 2100,
    "macro_targets_g": {
      "protein_g": 150,
      "carbs_g": 220,
      "fat_g": 60,
      "fiber_g": 25
    },
    "meal_structure": {
      "meals_per_day": 4,
      "slots": [
        {"slot": "breakfast", "kcal_ratio": 0.25, "protein_floor_g": 25},
        {"slot": "lunch", "kcal_ratio": 0.35, "protein_floor_g": 40},
        {"slot": "dinner", "kcal_ratio": 0.30, "protein_floor_g": 35},
        {"slot": "snack", "kcal_ratio": 0.10, "protein_floor_g": 15}
      ]
    }
  },
  "constraints": {
    "hard_bans": [],
    "soft_avoid": [],
    "soft_prefer": [],
    "medical_caps": {}
  },
  "medical_flags": {...},
  "rule_notes": []
}
```

### 14.2. Calorie targets

Theo goal:

- maintain: `target = TDEE`
- cut standard: `TDEE - 15%`
- cut aggressive: `TDEE - 20%`, không dưới BMR quá sâu
- bulk standard: `TDEE + 10%`
- recomp: `TDEE - 5%` hoặc gần maintenance

Guardrail:

- Không khuyến nghị deficit quá mạnh.
- Nếu BMI thấp hoặc bodyfat thấp thì cảnh báo không nên cut.
- Nếu có bệnh lý, thêm warning cần tham khảo chuyên gia.

### 14.3. Macro targets

Protein:

- cut/recomp: 1.8–2.2 g/kg
- bulk: 1.6–2.0 g/kg
- maintain/health: 1.2–1.8 g/kg

Fat:

- tối thiểu 0.6 g/kg, thường 20–30% kcal.

Carb:

- phần kcal còn lại sau protein + fat.

Fiber:

- tối thiểu 20–30g/ngày nếu không có chống chỉ định.

### 14.4. Bệnh lý và hạn chế dinh dưỡng

Rulebase phải xử lý rõ bệnh lý/hạn chế. Đây là phần quan trọng.

#### Cao huyết áp / tăng huyết áp

Flags:

```json
{"low_sodium": true}
```

Hard/soft rules:

- Soft avoid: đồ mặn, đồ chế biến sẵn, xúc xích, mì gói, nước chấm nhiều muối.
- Medical cap: sodium nên thấp hơn bình thường.
- Prompt meal plan phải ưu tiên hấp/luộc/nướng ít muối.
- Warning: không thay thế tư vấn bác sĩ.

#### Tiểu đường / đái tháo đường

Flags:

```json
{"low_sugar": true, "carb_control": true}
```

Rules:

- Hạn chế đường đơn, nước ngọt, bánh kẹo.
- Ưu tiên carb chậm: gạo lứt, yến mạch, khoai lang, rau.
- Chia carb đều theo bữa.
- Không để snack toàn đường.
- Macro carb có thể giảm theo restriction level.

#### Gout / acid uric cao

Flags:

```json
{"low_purine": true}
```

Rules:

- Soft/hard avoid tùy mức: nội tạng, hải sản purine cao, thịt đỏ quá nhiều.
- Ưu tiên protein từ trứng, sữa, đậu phụ mức vừa phải, thịt trắng.
- Không generate thực đơn quá nhiều thịt đỏ/hải sản.

#### Mỡ máu / cholesterol / triglyceride cao

Flags:

```json
{"low_sat_fat": true}
```

Rules:

- Hạn chế mỡ động vật, bơ, chiên rán.
- Ưu tiên cá, ức gà, đậu, rau, dầu olive lượng vừa phải.
- Fat target có thể giữ vừa phải nhưng chọn nguồn fat tốt.

#### Bệnh thận / suy thận / CKD

Flags:

```json
{"renal_caution": true}
```

Rules:

- Đây là red flag.
- Không tự đẩy protein cao.
- Nếu renal_caution true thì protein target không được tự đặt 2.2 g/kg.
- Trả warning cần bác sĩ/dietitian.
- Meal plan nên ở chế độ thận trọng, không nhiều đạm, không supplement protein.

#### Dị ứng

Rules:

- Allergies là hard ban.
- Không được sinh ingredient chứa allergy.
- Nếu allergy là sữa thì tránh milk, yogurt, whey, cheese.
- Nếu allergy là hải sản thì tránh shrimp, fish nếu user ghi rõ seafood.

#### Disliked foods / avoid ingredients

Rules:

- `disliked_foods`: soft avoid, cố gắng không dùng.
- `avoid_ingredients`: hard ban nếu user ghi rõ.

#### Vegetarian / vegan / halal / keto / low carb

Rules:

- vegetarian: không thịt/cá/hải sản, có thể dùng trứng/sữa nếu không vegan.
- vegan: không tất cả sản phẩm động vật.
- halal: tránh pork.
- keto: carb rất thấp, nhưng chỉ áp dụng nếu user chọn rõ.
- low_carb: giảm carb, tăng protein/fat vừa phải.

---

## 15. Profile Advice Prompt

Trang Profile cần nút hoặc section AI Advice. Sau khi user nhập chỉ số cơ thể, backend gọi OpenAI để đưa lời khuyên ngắn.

Endpoint:

```http
POST /api/profile/advice/
```

Input:

```json
{
  "profile": {...},
  "metrics": {...},
  "preferences": {...},
  "medical": {...}
}
```

Output:

```json
{
  "summary": "...",
  "risks": ["..."],
  "recommendations": ["..."],
  "suggested_goal": {
    "goal_type": "recomp",
    "reason": "..."
  },
  "safety_note": "..."
}
```

Prompt system:

```text
You are a cautious fitness and nutrition coach. Give practical, non-medical advice from body metrics and preferences. Do not diagnose disease. If medical conditions are present, advise the user to consult a qualified professional. Return strict JSON only.
```

---

## 16. Nutrition Plan Generate

Endpoint:

```http
POST /api/nutrition/plan/generate/
```

Input:

```json
{
  "derived_targets": {...},
  "constraints": {...},
  "preferences": {...},
  "medical_flags": {...},
  "extra_restrictions": [],
  "options": {
    "optimizer_iters": 200,
    "max_llm_retries": 1
  }
}
```

### 16.1. OpenAI meal prompt

System:

```text
You are a nutrition meal planner. Create a one-day meal draft using ingredient-level recipes. Do not calculate final calories. Do not claim macros. Respect hard bans, allergies, diet style, and medical restrictions. Return strict JSON only.
```

Meal draft schema:

```json
{
  "version": "draft_v1",
  "mode": "day",
  "days": [
    {
      "day_index": 1,
      "meals": [
        {
          "slot": "breakfast",
          "title": "...",
          "recipes": [
            {
              "recipe_name": "...",
              "ingredients": [
                {
                  "ingredient_name": "oats",
                  "quantity": "1 part",
                  "role": "carb",
                  "notes": "dry"
                }
              ],
              "instructions": ["..."]
            }
          ]
        }
      ],
      "draft_notes": []
    }
  ]
}
```

### 16.2. Ingredient resolver cơ bản

Không dùng RAG phức tạp. Resolver làm:

1. Chuẩn hóa tên ingredient: lower, bỏ dấu tiếng Việt nếu cần.
2. Tìm exact `canonical_name`.
3. Tìm trong `aliases`.
4. Tìm `display_name_vi__icontains`.
5. Fuzzy match bằng rapidfuzz nếu chưa thấy.
6. Nếu vẫn không thấy, chọn fallback theo role:
   - protein → chicken_breast / egg / tofu
   - carb → cooked_white_rice / sweet_potato / oats
   - fat → olive_oil / avocado / peanut_butter
   - veg → broccoli / spinach / cucumber
   - fruit → banana / apple

Nếu fallback dùng, thêm warning.

### 16.3. Calculator

Tính theo gram:

```text
nutrient = grams / 100 × nutrient_per_100g
```

Tính total theo:

- ingredient
- recipe
- meal
- day

### 16.4. Optimizer grams

Optimizer là deterministic.

Khởi tạo:

- Mỗi meal có kcal target theo `meal_structure.slots`.
- Trong meal, phân grams theo role:
  - protein: 100–180g
  - carb: 100–250g cooked
  - veg: 100–250g
  - fat/oil: 5–15g
  - fruit: 80–150g

Loop tối đa `optimizer_iters`:

1. Tính totals.
2. Nếu protein thấp:
   - tăng protein ingredients 10% mỗi vòng.
   - nếu vẫn thấp, thêm protein snack từ atom phù hợp.
3. Nếu kcal vượt:
   - giảm fat trước nếu fat cao.
   - giảm carb sau.
   - không giảm protein nếu protein đang thiếu.
4. Nếu kcal thiếu:
   - tăng carb nếu không low_carb/diabetes.
   - tăng fat tốt nếu cần.
5. Nếu carb quá cao với diabetes/low_carb:
   - giảm carb, tăng protein/veg/fat tốt vừa phải.
6. Dừng khi:
   - kcal trong ±10% target.
   - protein đạt >=95% target.

### 16.5. Evaluator nutrition

Hard fail:

- allergy xuất hiện.
- avoid_ingredients xuất hiện.
- không resolve được quá nhiều nguyên liệu.
- protein dưới 90% sau optimize.
- kcal lệch quá 15% sau optimize.

Warn:

- sodium cao.
- fiber thấp.
- quá ít variety.
- dùng fallback ingredient.
- bệnh lý có rủi ro.

Output final:

```json
{
  "meal_plan": {...},
  "totals": {
    "kcal": 2100,
    "protein_g": 150,
    "carbs_g": 220,
    "fat_g": 60,
    "fiber_g": 25,
    "sodium_mg": 1800
  },
  "shopping_list": [
    {"atom_id": 1, "name": "Ức gà", "grams": 300}
  ],
  "issues": [],
  "warnings": [],
  "constraint_report": {...}
}
```

---

## 17. API endpoints tổng hợp

### Auth

```text
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

### Profile

```text
GET    /api/profile/
PUT    /api/profile/
PATCH  /api/profile/
POST   /api/profile/advice/
```

### Workout

```text
GET  /api/workout/exercises/
GET  /api/workout/exercises/search/?q=&muscles=
POST /api/workout/intent/analyze/
POST /api/workout/plan/generate/
POST /api/workout/plan/generate-from-goal/  # optional convenience: gọi intent rồi generate
```

### Nutrition

```text
POST /api/nutrition/metrics/
POST /api/nutrition/rulebase/preview/
POST /api/nutrition/plan/generate/
GET  /api/nutrition/atoms/
GET  /api/nutrition/atoms/search/?q=
```

---

## 18. Frontend cần dựng

### Pages

```text
/login
/register
/profile
/workout
/nutrition
/dashboard
```

### Layout

- Sidebar hoặc top navigation.
- Màu chủ đạo xanh lá + trắng.
- Icon style Feather/lucide.
- Animation nhẹ khi chuyển trang/card hover.

### Profile page

Gồm:

- Avatar
- Full name
- Sex
- Birth year / age
- Height, weight
- Waist, neck, hip
- Activity level
- Experience level
- Goal type + goal text
- Dietary style
- Allergies
- Favorite foods
- Disliked foods
- Medical conditions
- Button: Analyze body metrics
- Button: AI advice

### Workout page

Không generate trực tiếp. UI nên có 2 bước rõ:

1. Analyze Intent
   - nhập goal text, days/week, session minutes, training days, equipment
   - hiện focus muscles/internal goal
2. Generate Plan
   - dùng internal goal vừa phân tích
   - hiện plan theo từng ngày, card bài tập, ảnh, sets/reps/rest

### Nutrition page

- Lấy chỉ số từ Profile.
- Preview metrics/rulebase.
- Generate meal plan.
- Hiển thị totals, macro, shopping list, warnings.

---

## 19. Thứ tự code MVP bắt buộc

Không nhảy vào AI ngay. Thứ tự:

1. Bootstrap backend/frontend.
2. PostgreSQL kết nối thành công.
3. Auth register/login/me.
4. Profile CRUD + preferences.
5. Import `exercises.csv`.
6. Import `nutrition_atoms_seed.csv`.
7. Exercise list/search.
8. Nutrition atom list/search.
9. Metrics + rulebase.
10. Workout intent analyze OpenAI.
11. Backfill exercise embeddings.
12. Workout retrieval RAG.
13. Workout generate OpenAI.
14. Workout evaluator/repair.
15. Profile AI advice.
16. Nutrition meal draft OpenAI.
17. Nutrition resolver/calculator/optimizer/evaluator.
18. Frontend pages nối API.
19. Save plan history.
20. Deploy sau cùng.

---

## 20. Lệnh chạy cuối cùng

Backend:

```bash
cd backend
copy .env.example .env
# điền OPENAI_API_KEY sau
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py import_exercises --csv seed/exercises.csv
python manage.py seed_nutrition_atoms --csv seed/nutrition_atoms_seed.csv
python manage.py backfill_exercise_embeddings --batch-size 64
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Test:

```text
http://localhost:5173
http://127.0.0.1:8000/api/docs/
```

---

## 21. Definition of Done

Dự án phục dựng đạt yêu cầu khi:

- Register/login hoạt động.
- Profile lưu được chỉ số cơ thể.
- PostgreSQL có dữ liệu Exercise và NutritionAtom.
- Workout intent analysis trả focus muscles đúng.
- Workout generate dùng OpenAI + RAG, không bịa exercise ID.
- Nutrition metrics tính được BMI/BMR/TDEE/bodyfat nếu đủ số đo.
- Rulebase xử lý bệnh lý/hạn chế rõ ràng.
- Nutrition generate tạo meal plan, resolve atom, optimize grams và trả totals.
- Frontend hiển thị được Profile, Workout, Nutrition.
- Không lộ API key ra frontend.
