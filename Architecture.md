# Architecture.md - AI Personal Trainer

> Updated: 2026-05-12.
> Tai lieu nay mo ta kien truc hien tai cua du an. Agent phai doc cung `Agent.md` truoc khi code.

---

## 1. System Overview

AI Personal Trainer la ung dung ca nhan hoa tap luyen va dinh duong.

```text
React Frontend
  -> Token Auth REST API
Django REST Framework Backend
  -> Domain Services
  -> PostgreSQL + pgvector
  -> OpenAI API
```

Domain chinh:

- Auth/Profile
- Workout AI Agent
- Nutrition AI Agent
- Plan History / Audit

Backend la noi duy nhat goi OpenAI. Frontend khong goi OpenAI truc tiep.

---

## 2. Core Decisions

- Database chinh la PostgreSQL, co pgvector cho exercise retrieval.
- OpenAI duoc dung cho workout intent, workout generation, nutrition draft, profile advice, embeddings.
- Workout tach 2 buoc: intent analysis -> plan generation.
- Nutrition dung rulebase + NutritionAtom, khong dung RAG phuc tap.
- Profile la nguon du lieu chinh cho body metrics, goal type, experience level, diet preferences, medical constraints.
- Profile luu country/city hoac GPS latitude/longitude va weather snapshot de Nutrition co the sinh thuc don theo vi tri/thoi tiet.
- `goal_text` chi la input cua Workout, khong phai truong nguoi dung can hoan thien trong Profile UI.
- Workout plan generation dung `focus_muscles/internal_goal`; `goal_text` chi bat buoc khi user muon Analyze Intent moi.
- `equipment` khong con la input Workout. Equipment chi la metadata cua Exercise va co the duoc dung noi bo trong retrieval.
- User can hoan thien profile de dung chinh xac Workout, Nutrition, va Profile Advice.
- Plan generate phai duoc luu DB va load lai khi mo trang.
- Audit duoc luu noi bo cho debug, khong hien tren UI nguoi dung.
- Nutrition meal draft co the sinh nhieu recipe/mon trong mot bua; bua chinh thuong gom mon dam chinh, mon tinh bot, va mon rau/soup/side neu phu hop.
- API co 3 lop bao ve user data: rate-limit middleware, PostgreSQL Row Level Security cho bang co `user_id`, va app-layer ownership checks de chong IDOR khi client gui plan payload/reference.

---

## 3. Repository Architecture

```text
AI-Personal-Trainer/
|-- backend/
|   |-- config/
|   |-- apps/
|   |   |-- accounts/
|   |   |-- profiles/
|   |   |-- workout/
|   |   |-- nutrition/
|   |   `-- common/
|   |-- seed/
|   |   |-- exercises.csv
|   |   `-- nutrition_atoms_seed.csv
|   `-- manage.py
|-- frontend/
|   |-- src/
|   |   |-- api/
|   |   |-- components/
|   |   |-- layouts/
|   |   |-- pages/
|   |   |-- styles/
|   |   |-- App.jsx
|   |   `-- main.jsx
|   `-- package.json
|-- Agent.md
`-- Architecture.md
```

---

## 4. Backend Responsibilities

### accounts

- register
- login
- logout
- me
- token auth

Khong chua business logic fitness/nutrition.

### profiles

- Luu body profile va preferences.
- Tinh BMI, BMR, TDEE, body fat.
- Luu location: country, city, latitude, longitude, source.
- Lay current weather tu WeatherAPI va luu `weather_snapshot`.
- WeatherAPI chi duoc goi toi da 1 lan/ngay cho cung city/country; GPS chi goi lai khi di xa khoi vung city cu hoac backend resolve ra city/country moi.
- Sau khi lay weather moi, backend sinh va luu dashboard greeting theo weather hien tai.
- Luu `metrics_snapshot` moi lan save profile.
- Luu `advice_snapshot` sau khi user xin advice.
- Tra ve bundle gom profile, preferences, metrics, advice, completeness.
- Kiem tra profile completeness cho cac flow can du lieu chinh xac.

### workout

- Quan ly Exercise.
- Import `exercises.csv`.
- Backfill embeddings.
- Analyze intent tu `goal_text`.
- Luu focus muscles vao profile.
- Retrieval exercise candidates bang filter + pgvector semantic rank.
- Generate, evaluate, repair, enrich workout plan.
- Luu workout plan vao `Plan`.
- Tra latest workout plan tu DB.
- Luu ngay tap da hoan thanh vao `WorkoutCompletion`.
- Tra summary gom `today_completed`, `completed_days_this_week`, va `streak_days`.

### nutrition

- Quan ly NutritionAtom.
- Seed `nutrition_atoms_seed.csv`.
- Tinh metrics neu can.
- Build deterministic rulebase targets.
- Generate meal draft bang OpenAI.
- Dua `location_context` gom country/city va weather hien tai vao prompt sinh thuc don.
- Resolve ingredient ve NutritionAtom.
- Tinh recipe/meal/day/totals tu NutritionAtom.
- Optimize grams.
- Evaluate warnings/issues.
- Recipe co the co `image_url` do LLM tra ve neu la direct public HTTPS image URL. Neu thieu/khong hop le, backend enrich recipe image URLs tu `image_search_query`. Backend uu tien Openverse, fallback Wikimedia Commons; neu loi mang/khong co ket qua thi de placeholder trong.
- Luu nutrition plan vao `Plan`.
- Tra latest nutrition plan tu DB.
- Tra calories theo thang tu lich su `Plan` nutrition da luu, lay ban moi nhat moi ngay.

### common

- OpenAI client wrapper.
- Prompt definitions.
- Plan / PlanAudit models.
- Audit helper.
- API request log middleware/models.
- Rate-limit middleware.
- PostgreSQL RLS current-user middleware.
- Plan ownership helper cho cac mutation can source plan reference.
- Text utilities.

---

## 5. Database Architecture

Core tables:

```text
auth_user
user_profile
user_preferences
exercise
workout_intent_analysis
workout_completion
nutrition_atom
nutrition_completion
plan
plan_audit
api_request_log
short_term_memory_entry
```

### user_profile

Luu du lieu dung chung cho Workout, Nutrition, Profile Advice.

Important fields:

- `full_name`
- `sex`
- `birth_year`
- `height_cm`
- `weight_kg`
- `waist_cm`
- `neck_cm`
- `hip_cm`
- `activity_level`
- `experience_level`
- `goal_type`
- `focus_muscles`
- `country`
- `city`
- `latitude`
- `longitude`
- `location_source`
- `weather_snapshot`
- `weather_updated_at`
- `dashboard_greeting_snapshot`
- `dashboard_greeting_updated_at`
- `metrics_snapshot`
- `metrics_updated_at`
- `advice_snapshot`
- `advice_updated_at`

Notes:

- `experience_level` duoc hoan thien trong Profile va Workout generation se doc tu profile.
- `goal_text` co the con trong DB tu schema cu, nhung UI va completeness khong dung. Workout goal text la state rieng cua Workout page.
- Metrics duoc tinh va luu khi save profile; GET profile se tinh va luu neu snapshot con thieu.
- Advice duoc luu va hien lai cho den khi user xin advice moi.

### user_preferences

Fields:

- `dietary_style`
- `allergies`
- `favorite_foods`
- `disliked_foods`
- `avoid_ingredients`
- `medical_conditions`
- `notes`

Preferences duoc dung trong nutrition rulebase va profile advice.

### exercise

Nguon seed: `exercises.csv`.

Important fields:

- `title`
- `body_part_raw`
- `muscle_groups`
- `equipment`
- `level`
- `image_url`
- `image_file`
- `embedding`
- `embedding_text`
- `embedding_model`

`equipment` la metadata cua exercise, khong phai form field Workout.
`image_url` duoc seed tu Lyfta/APILyfta va frontend dung truc tiep lam thumbnail bai tap; neu URL thieu/loi thi hien placeholder trong.

### nutrition_atom

Nguon seed: `nutrition_atoms_seed.csv`.

Important fields:

- `canonical_name`
- `display_name_vi`
- `category`
- `food_role`
- `edible_form`
- `kcal_per_100g`
- `protein_g_per_100g`
- `carb_g_per_100g`
- `fat_g_per_100g`
- `fiber_g_per_100g`
- `sodium_mg_per_100g`
- `default_serving_g`
- `aliases`
- `source`
- `is_active`

NutritionAtom la source of truth cho calories va macro. LLM khong duoc tu tinh totals.

### plan

Luu plan sau khi generate.

- `user`
- `plan_type`: `workout`, `nutrition`, `full`
- `title`
- `payload`
- `created_at`

`payload` luu response day du de frontend load lai duoc:

- Workout: `request_id`, `plan`, `warnings`, `issues`
- Nutrition: `request_id`, `meal_plan`, `totals`, `derived_targets`, `shopping_list`, `warnings`, `issues`, `constraint_report`
- Nutrition recipes co the co `image_search_query`, `image_url`, va `image` metadata. `image_url` co the den tu LLM neu hop le hoac tu backend enrich Openverse/Wikimedia Commons.

### workout_completion

Luu mot ngay user xac nhan da hoan thanh workout.

- `user`
- `workout_date`
- `plan` nullable FK toi workout Plan gan nhat luc xac nhan
- `created_at`, `updated_at`

Unique theo `(user, workout_date)`.

### nutrition_completion

Luu mot ngay user xac nhan da hoan thanh thuc don.

- `user`
- `nutrition_date`
- `plan` nullable FK toi nutrition Plan gan nhat luc xac nhan
- `created_at`, `updated_at`

Unique theo `(user, nutrition_date)`.

Daily streak dung `workout_completion` + `nutrition_completion`:

- Neu ngay do la training day theo latest workout plan: can hoan thanh ca workout va nutrition.
- Neu ngay do la rest day: chi can hoan thanh nutrition.
- Neu chua co workout plan: streak chi yeu cau nutrition.

### plan_audit

Luu debug trace noi bo:

- `request_id`
- `domain`
- `step`
- `payload`
- `plan`
- `created_at`

Audit khong hien tren UI nguoi dung.

Audit `step=final` cua cac flow co goi OpenAI luu them `token_usage` de debug chi phi/request:

```json
{
  "prompt_tokens": 0,
  "completion_tokens": 0,
  "total_tokens": 0,
  "calls": [
    {
      "operation": "chat.completions",
      "model": "gpt-4.1-mini",
      "prompt_tokens": 0,
      "completion_tokens": 0,
      "total_tokens": 0
    }
  ]
}
```

### short_term_memory_entry

Luu STM tam thoi cho Nutrition va Workout trong 7 ngay.

Important fields:

- `user`
- `domain`: nutrition/workout
- `scope`: plan/meal/recipe/replace_exercise
- `entity_type`: recipe/ingredient/atom_id/exercise_id/exercise_title
- `entity_key`: key da normalize de upsert
- `raw_label`: label goc de debug
- `reason_code`
- `source_action`
- `expires_at`
- `hit_count`
- `metadata`
- `created_at`, `updated_at`

Backend purge ban ghi het han khi doc/ghi STM. Command cleanup nen chay dinh ky:

```powershell
python manage.py purge_short_term_memory
```

---

## 6. Profile Architecture

### Profile flow

```text
GET /api/profile/
  -> ensure profile + preferences
  -> calculate/save metrics_snapshot if missing
  -> return profile bundle

PATCH /api/profile/
  -> save profile + preferences
  -> calculate/save metrics_snapshot
  -> return profile bundle

POST /api/profile/advice/
  -> require complete profile
  -> use current/stored metrics
  -> call OpenAI profile advice
  -> save advice_snapshot
  -> return advice

POST /api/profile/weather/
  -> receive latitude/longitude from browser GPS or city/country from manual input
  -> call WeatherAPI current weather in backend only if no same-day cache exists for the same city/country
  -> save normalized location + weather_snapshot
  -> trigger dashboard greeting generation immediately after a fresh WeatherAPI fetch
  -> return profile bundle plus dashboard_greeting

GET /api/profile/dashboard-greeting/
  -> return one short LLM-generated Vietnamese dashboard greeting using profile goal and cached weather context
  -> persist and cache per user/date/weather snapshot to avoid repeated LLM calls on every dashboard reload
```

### Profile completeness

Required:

- full name
- sex
- birth year
- height
- weight
- waist
- neck
- activity level
- experience level
- goal type
- hip if sex is female

Not required:

- workout `goal_text`
- equipment

Completeness gate applies to:

- Workout intent/generation
- Nutrition generation
- Profile AI advice

### Profile UI

- Body/goals form.
- Nutrition preferences form.
- Location and weather section:
  - button uses browser geolocation permission and sends latitude/longitude to backend
  - manual country/city input for users who do not grant GPS permission
  - GPS results are stored at city/country level, not ward/district level
  - weather card shows current condition, temperature, humidity
- Current workout focus.
- Metrics section: card display for BMI, BMR, TDEE, body fat.
- Advice section: green advice text, robust renderer for nested JSON, loading "Analyzing..." state.
- Metrics and Advice are stacked vertically.

---

## 7. Workout Architecture

### Workout flow

```text
WorkoutPage mount
  -> GET /api/profile/
  -> GET /api/workout/plan/latest/
  -> show saved latest plan if exists

User enters goal_text
  -> POST /api/workout/intent/analyze/
  -> OpenAI intent service
  -> save focus_muscles to profile

User chooses days/session settings and has focus_muscles
  -> POST /api/workout/plan/generate/
  -> retrieval candidates
  -> OpenAI plan generation
  -> evaluator + repair
  -> enrich exercise metadata
  -> save Plan
  -> return plan
```

### Workout API

```text
GET  /api/workout/exercises/
GET  /api/workout/exercises/search/
POST /api/workout/intent/analyze/
POST /api/workout/plan/generate/
GET  /api/workout/plan/latest/
GET  /api/workout/completion/summary/
POST /api/workout/completion/today/
POST /api/workout/plan/generate-from-goal/
```

### Intent service

Input:

- `goal_text`

Output:

- `focus_muscles`

Intent does not create a workout plan and does not output equipment/training days/risk notes.

### Plan generation

Inputs:

- `internal_goal` from intent
- `focus_muscles` is required, either from the current intent or from the saved profile focus
- `days_per_week`
- `session_minutes`
- `training_days`
- constraints

Backend enriches:

- `experience_level` from profile
- `equipment: []` by default

Output plan schema:

```json
{
  "goal": "mixed",
  "days_per_week": 4,
  "session_minutes": 60,
  "split": "upper/lower",
  "days": [
    {
      "day": "mon",
      "title": "Training day",
      "exercises": [
        {
          "exercise_id": 1,
          "sets": 3,
          "reps": "8-12",
          "rest_sec": 90,
          "notes": "Keep 1-2 reps in reserve."
        }
      ]
    }
  ]
}
```

### Workout UI

- Focus muscles card.
- Goal text textarea for analyzing/updating focus muscles only.
- Analyze intent button.
- Plan settings.
- Training days are selectable day buttons:
  - gray when not selected
  - green when selected
- Generate plan button is green.
- Generate plan does not require goal text if focus muscles already exist.
- Weekly plan cards.
- Warnings/issues/audit khong hien thanh raw JSON/log block tren UI nguoi dung.

---

## 8. Nutrition Architecture

### Nutrition flow

```text
Daily automation at 07:00 Asia/Saigon
  -> python manage.py run_daily_automation
  -> active users with complete profiles are processed even if they have not logged in today
  -> refresh weather from saved city/GPS when available
  -> generate and persist dashboard greeting
  -> generate and persist today's nutrition Plan when today's plan does not exist

NutritionPage mount
  -> GET /api/profile/
  -> use profile metrics snapshot
  -> GET /api/nutrition/plan/latest/
  -> if latest plan is from current local day, show it
  -> if latest plan is stale, save old recipe names into STM and return empty state

User clicks Generate menu
  -> POST /api/nutrition/metrics/ if current metrics missing
  -> POST /api/nutrition/rulebase/preview/
  -> POST /api/nutrition/plan/generate/
  -> backend refreshes weather only when no same-day cache exists or location changed city/country
  -> backend loads nutrition STM and sends avoid_recipe_names / avoid_ingredient_names to OpenAI
  -> backend sends location_context to OpenAI
  -> OpenAI meal draft
  -> resolve ingredients
  -> assign nutrients from NutritionAtom
  -> calculate recipe/meal/day/totals
  -> optimize grams
  -> evaluate
  -> save Plan
  -> return plan
```

### Nutrition API

```text
POST /api/nutrition/metrics/
POST /api/nutrition/rulebase/preview/
POST /api/nutrition/plan/generate/
GET  /api/nutrition/plan/latest/
GET  /api/nutrition/plan/monthly-calories/
POST /api/nutrition/completion/today/
GET  /api/nutrition/atoms/
GET  /api/nutrition/atoms/search/
```

### Daily automation

```text
python manage.py run_daily_automation
run-daily-automation.bat
install-daily-automation-task.bat
```

`install-daily-automation-task.bat` registers a Windows Task Scheduler job at 07:00.
The command is idempotent by default: it skips nutrition generation if a current-day nutrition Plan already exists.
Use `--force` only when intentionally regenerating today's greeting/menu.

### Metrics service

Deterministic calculation:

- BMI
- BMR
- TDEE
- body fat percent if enough data

UI does not show waist-to-height ratio or method.

### Rulebase service

Creates:

- `derived_targets.calorie_target_kcal`
- `derived_targets.macro_targets_g`
- `derived_targets.meal_structure`
- `constraints.hard_bans`
- `constraints.soft_avoid`
- `constraints.soft_prefer`
- `constraints.medical_caps`
- `medical_flags`
- `rule_notes`

Rulebase is deterministic and is the source for targets.

### Meal planning

OpenAI creates ingredient-level meal draft only.
Mot meal co the co nhieu `recipes`. Breakfast/lunch/dinner nen co 2-3 mon rieng khi hop ly, vi du mon dam chinh, mon tinh bot, va mon rau/soup/side. Snack co the chi co 1 recipe.

Before calling OpenAI, backend loads `short_term_memory_entry` for nutrition. Recipe names from stale previous-day menus are included in `short_term_memory.avoid_recipe_names` so a new day does not regenerate the same dishes.

LLM must not include final calories/macros/totals. Backend calculates these from NutritionAtom.

LLM may provide `image_search_query` and an optional direct public HTTPS `image_url` for each recipe. Backend accepts a valid direct URL, otherwise it tries to enrich each recipe with an online image from Openverse first, then Wikimedia Commons. This is best-effort and non-blocking for correctness: if no suitable image is found, frontend shows a blank placeholder instead of fake imagery.

Change menu supports a no-memory reason (`simple_dislike`) for cases where the user simply does not like the menu. This refreshes the menu without treating the old recipes or ingredients as dislikes and without writing ShortTermMemoryEntry records.

Dashboard Today's Meals supports "I ate something else" per meal. User can type a description, use browser speech-to-text, or attach a small meal image. Backend sends the evidence to the meal replacement LLM path, replaces that meal, recalculates totals through NutritionAtom, and saves a new nutrition Plan. Uploaded image data is passed to the LLM call when present but omitted from audit logs.

Resolved ingredients store:

- `name`: English canonical name
- `canonical_name`: English canonical name
- `grams`
- `role`
- `nutrients`

Frontend displays each ingredient on its own line and uses English canonical names.

### Nutrition UI

- Generate menu button when no current-day plan exists; Change menu button only when today's plan is loaded.
- No profile-completion notice on Nutrition page; errors still appear if profile is incomplete.
- Meal Plan Overview:
  - Calories card alone on first row with progress bar.
  - Protein, Carbs, Fat, Fiber as simple metric cards.
  - Sodium is not shown.
- Meal cards show:
  - meal title
  - meal kcal
  - recipe rows with thumbnail, recipe name, recipe kcal, and Change dish action
  - meal total kcal
- Clicking a recipe row opens dish detail with ingredients, cooking instructions, and per-ingredient calories/macros.
- No debug JSON/audit block.

### Dashboard UI

- Profile completeness card is hidden after profile is complete.
- Header greets `Hi {displayName}` and shows a dynamic LLM-generated daily weather/training/nutrition message.
- Workout Plan card uses real `completed_days_this_week` from `WorkoutCompletion`.
- Streak card uses combined daily completion: workout + nutrition on training days, nutrition only on rest days.
- Today's Workout selects the latest workout plan day that matches the user's current weekday.
- If today is not a training day, Today's Workout shows a rest-day image card with a recovery and sleep message instead of exercise rows.
- Today's Workout and Workout page exercise cards use real `exercise.image_url` thumbnails when available.
- Today's Workout action confirms today's workout completion through `POST /api/workout/completion/today/`.
- Today's Meals lists all meals including snack, can mark today's meals complete through `POST /api/nutrition/completion/today/`, and can replace a meal actually eaten from text, speech-to-text, or image evidence.
- Calories This Month uses `GET /api/nutrition/plan/monthly-calories/`, based on saved nutrition `Plan` history.
- Dashboard top stat card replaces Workout Plan with Location/Weather from profile. Today's Workout panel remains the place for workout plan details.
- If no plan or image exists, dashboard shows an empty state or blank placeholder, not fake meals/exercises/images.

---

## 9. OpenAI Architecture

Environment:

```env
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBED_MODEL=text-embedding-3-small
OPENAI_EMBED_DIM=1536
WEATHERAPI_KEY=
```

`apps/common/openai_client.py`:

- `get_openai_client()`
- `generate_json(system_prompt, user_prompt, schema=None, max_retries=...)`
- `embed_texts(texts)`

All JSON-generating prompts must request strict JSON only.

---

## 10. Frontend Architecture

Pages:

```text
AuthPage
DashboardPage
ProfilePage
WorkoutPage
NutritionPage
LandingPage
```

API modules:

```text
src/api/client.js
src/api/auth.js
src/api/profile.js
src/api/workout.js
src/api/nutrition.js
```

All authenticated API calls attach:

```text
Authorization: Token <token>
```

Shared UI:

- `AppShell`
- sidebar/nav
- `ErrorBanner`
- `Field`, inputs
- `ProfileCompletionNotice`
- `FocusMuscles`

Visual style:

- green health theme with deep emerald brand tokens (`brand-50` through `brand-950`)
- neutral gray surfaces
- lucide icons
- app background uses a pale green-gray surface
- authenticated shell uses a collapsible floating rounded sidebar on desktop and bottom navigation on mobile
- cards use soft rounded translucent white surfaces with subtle green-tinted shadows
- `.section` uses `rounded-[1.5rem]`, border, translucent white background, and backdrop blur
- primary buttons use deep emerald, secondary buttons use white surfaces with black/neutral borders
- repeated inner cards usually use `rounded-2xl` or `rounded-[1.25rem]`

---

## 11. Seed Data

### exercises.csv

Used to seed Exercise.

Expected fields include:

- title
- body_part
- image_url
- image_file

Import process:

```text
CSV row
  -> normalize body_part
  -> infer muscle_groups
  -> infer equipment
  -> upsert Exercise
```

### nutrition_atoms_seed.csv

Used to seed NutritionAtom.

Expected fields:

```csv
canonical_name,display_name_vi,category,food_role,edible_form,kcal_per_100g,protein_g_per_100g,carb_g_per_100g,fat_g_per_100g,fiber_g_per_100g,sodium_mg_per_100g,default_serving_g,aliases,source,is_active
```

Import process:

```text
CSV row
  -> validate required fields
  -> convert numeric fields
  -> upsert by canonical_name
```

---

## 12. Audit and Safety

AI flows should record internal audit:

- request_id
- domain
- step
- payload summary
- plan link if available

Do not log API keys.
Avoid storing sensitive full prompts if not needed.

Safety:

- No medical diagnosis.
- Medical conditions should produce cautionary advice, not treatment.
- Nutrition must respect allergies and hard bans.
- Workout must avoid invalid exercise IDs and unsafe volume where evaluator can detect it.

Security:

- `apps.common.middleware.RateLimitMiddleware` rate limits `/api/` requests before view execution.
  - Defaults: `AIPT_RATE_LIMIT_DEFAULT=240/60`, `AIPT_RATE_LIMIT_READ=600/60`, `AIPT_RATE_LIMIT_AUTH=10/60`, `AIPT_RATE_LIMIT_AI=20/300`.
  - Safe read requests (`GET`, `HEAD`, `OPTIONS`) use the `read` scope so normal page navigation does not consume the stricter write/AI quota.
  - Identity is token hash when `Authorization: Token ...` exists, otherwise client IP hash.
  - `/api/docs/` and `/api/schema/` are excluded.
- `apps.common.middleware.CurrentUserRLSMiddleware` sets PostgreSQL session variable `app.current_user_id` per API request.
  - Token auth is resolved from the `Authorization` header before DRF view logic so DB RLS can evaluate user ownership.
  - The variable is reset after response/exception.
- Migration `common.0004_user_owned_row_level_security` enables and forces PostgreSQL RLS on user-owned tables:
  - `user_profile`
  - `user_preferences`
  - `plan`
  - `workout_intent_analysis`
  - `workout_completion`
  - `nutrition_completion`
  - `short_term_memory_entry`
- IDOR protection:
  - User-scoped reads use `filter(user=request.user, ...)`.
  - Plan mutation endpoints must include `source_request_id` or equivalent source plan reference.
  - Backend verifies that the referenced `Plan` row belongs to the current user before accepting a client-supplied `current_plan` payload.
  - After ownership verification, backend reloads the source plan payload from DB and ignores client-supplied `current_plan` as authority.

---

## 13. Acceptance Criteria

Backend:

- `/api/docs/` works.
- Register/login/me works.
- Profile saves body metrics and preferences.
- Profile GET/PATCH returns metrics/advice snapshots.
- Profile advice is saved and reloaded.
- Exercise and NutritionAtom seed data exist.
- Workout intent returns focus muscles.
- Workout generate saves Plan and latest endpoint returns it.
- Nutrition generate saves Plan and latest endpoint returns it.
- Nutrition totals are calculated from NutritionAtom.
- Workout completion summary and complete-today endpoints work.
- Nutrition monthly calories endpoint is based on saved Plan history.
- PlanAudit exists for debug, but is not exposed in user UI.

Frontend:

- Auth works.
- Profile can save body metrics/preferences.
- Profile metrics cards always show saved metrics after save/load.
- Profile advice renders saved LLM advice without blank screen.
- Workout can generate from saved focus muscles, uses profile experience level, and loads latest plan.
- Workout training days are selectable buttons.
- Nutrition loads latest plan only for the current local day; stale menus are moved into STM and the UI shows Generate menu.
- Nutrition overview shows calories progress only, no sodium.
- Nutrition meal cards show recipe kcal and English ingredients one per line.
- Dashboard does not render fake plan/calorie data when no backend data exists.
- UI does not show debug audit/JSON blocks to end users.

---

## 14. Build / Verification

Common local checks:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py check

cd ..\frontend
npm.cmd run build
```
