# Kiến trúc hệ thống - AI Personal Trainer

## Tổng quan

Dự án được xây dựng theo mô hình **Domain-Driven Design (DDD)** với Django backend và LangGraph cho workflow orchestration. Hệ thống hỗ trợ tạo workout plan tự động dựa trên user profile, với khả năng mở rộng để thêm các domain khác (meal planning, sleep tracking, etc.).

## Cấu trúc thư mục và mô tả chi tiết

```



backend/



├── core/                    # Core infrastructure (dùng chung cho mọi domain)



├── shared/                  # Shared services (dùng chung cho mọi domain)



├── domains/                 # Domain-specific agents



├── services/               # Legacy services (low-level utilities)



├── management/             # Django management commands



├── migrations/             # Database migrations



├── models.py               # Django models



├── views.py                # Django REST API views



├── urls.py                 # URL routing



├── serializers.py          # DRF serializers



└── serializers_plan.py     # Workout plan serializers



```

---

## 📁 `core/` - Core Infrastructure

Thư mục chứa các thành phần cốt lõi được dùng chung bởi tất cả các domain.

### `core/state.py`

**Mục đích**: Định nghĩa base state và result classes cho tất cả graphs.

**Các thành phần chính**:

- `BaseGraphState`: TypedDict base cho state của mọi graph

  - `request_id`: ID duy nhất cho mỗi request

  - `raw_input`: Input gốc từ user

  - `iteration`: Số lần iteration hiện tại

  - `max_iter`: Số lần iteration tối đa

  - `issues`: Danh sách các vấn đề cần sửa

  - `warnings`: Danh sách cảnh báo

  - `audit`: Audit trail để tracking

- `BaseResult`: Dataclass base cho kết quả của mọi domain

  - Chứa `request_id`, `issues`, `warnings`, `audit`

- `generate_request_id()`: Tạo UUID cho mỗi request

**Cách hoạt động**: Tất cả domain-specific states (như `WorkoutGraphState`) kế thừa từ `BaseGraphState` để đảm bảo consistency.

---

### `core/audit.py`

**Mục đích**: Utilities để logging và tracking quá trình execution của graph.

**Các hàm chính**:

- `append_event(audit, name, payload)`: Thêm event vào audit trail

  - `audit`: Dict chứa audit data

  - `name`: Tên event (ví dụ: "profile_done", "retrieval_done")

  - `payload`: Dữ liệu kèm theo event

- `append_iteration(audit, iteration)`: Thêm iteration vào audit trail

  - Dùng để track các lần retry/repair của graph

**Cách hoạt động**: Mỗi node trong graph gọi `append_event()` để log các bước quan trọng, giúp debug và monitoring.

---

### `core/execution.py`

**Mục đích**: Generic graph executor cho mọi domain.

**Các thành phần chính**:

- `GraphExecutor`: Class static để execute graph

  - `execute(graph, init_state, to_result)`: Execute graph và convert state sang result

    - `graph`: LangGraph StateGraph instance

    - `init_state`: Initial state dict

    - `to_result`: Function để convert final state sang result object

**Cách hoạt động**: Wrapper đơn giản quanh `graph.invoke()` để đảm bảo pattern nhất quán.

---

## 📁 `shared/` - Shared Services

Thư mục chứa các services dùng chung cho mọi domain.

### `shared/simple_cache.py`

**Mục đích**: In-memory TTL cache đơn giản để cache kết quả và giảm chi phí API calls.

**Các hàm chính**:

- `cache_get(cache_name, key)`: Lấy giá trị từ cache

  - `cache_name`: Tên bucket cache (ví dụ: "retrieval_candidates", "plan_prompt")

  - `key`: Key để lookup

  - Trả về `None` nếu hết hạn hoặc không có

- `cache_set(cache_name, key, value, ttl_seconds)`: Ghi giá trị vào cache

  - `ttl_seconds`: Thời gian sống (mặc định 600 giây = 10 phút)

  - Tự động cleanup khi hết hạn

**Cách hoạt động**: Sử dụng dict in-memory với tuple `(expires_at, value)`. Tự động xóa khi hết hạn để tránh memory leak.

**Sử dụng**: 

- Cache retrieval candidates theo profile

- Cache LLM prompts/results cho intent và plan để tránh gọi lại khi user spam cùng input

---

### `shared/llm/` - LLM Infrastructure

#### `shared/llm/config.py`

**Mục đích**: Configuration cho LLM clients.

**Các thành phần chính**:

- `LLMConfig`: Dataclass chứa config

  - `provider`: "gemini" hoặc "openai"

  - `openai_api_key`, `openai_model`: Config cho OpenAI

  - `gemini_api_key`, `gemini_model`: Config cho Gemini

  - `temperature`: Temperature cho generation

  - `max_retries`: Số lần retry tối đa

- `LLMConfig.from_env()`: Factory method đọc từ environment variables

  - `LLM_PROVIDER`: "gemini" hoặc "openai"

  - `OPENAI_API_KEY`, `OPENAI_MODEL`

  - `GEMINI_API_KEY` (hoặc `GOOGLE_API_KEY`), `GEMINI_MODEL`

  - `LLM_TEMPERATURE`, `LLM_MAX_RETRIES`

**Cách hoạt động**: Centralized config để dễ quản lý và switch giữa các providers.

---

#### `shared/llm/client.py`

**Mục đích**: Generic LLM client wrapper cho mọi domain.

**Các thành phần chính**:

- `LLMClient`: Main client class

  - `__init__(cfg)`: Nhận `LLMConfig` hoặc tự đọc từ env

  - `generate_structured(prompt, schema_model)`: Generate structured JSON theo Pydantic schema bất kỳ

  - `generate_plan_json(prompt, response_schema)`: Backward-compatible wrapper cho plan (dùng `WorkoutPlan`)

    - Hỗ trợ Gemini và OpenAI

    - Sử dụng `with_structured_output()` để đảm bảo output đúng schema

**Các method private**:

- `_gemini_generate_structured(prompt, schema_model)`: Implementation cho Gemini

  - Sử dụng `ChatGoogleGenerativeAI` từ `langchain_google_genai`

  - Ưu tiên `method="json_schema"` cho structured output

- `_openai_generate_structured(prompt, schema_model)`: Implementation cho OpenAI

  - Sử dụng `ChatOpenAI` từ `langchain_openai`

  - Tương thích nhiều version của SDK

- `_log_prompt_stats(tag, prompt)`: Log thống kê prompt (chars, lines, tokens ước lượng)

**Cách hoạt động**: 

1. Client được khởi tạo với config

2. Khi gọi `generate_structured()` hoặc `generate_plan_json()`, nó tạo LLM instance tương ứng với provider

3. Sử dụng `with_structured_output()` để bind với Pydantic schema

4. Trả về dict từ Pydantic model

---

## 📁 `domains/` - Domain-Specific Agents

Thư mục chứa các domain agents. Hiện tại chỉ có `workout/`, nhưng có thể mở rộng thêm `meal/`, `sleep/`, etc.

### `domains/workout/` - Workout Planning Domain

#### `domains/workout/state.py`

**Mục đích**: Định nghĩa state và result classes cho workout planning graph.

**Các thành phần chính**:

- `WorkoutGraphState`: TypedDict kế thừa `BaseGraphState`

  - `profile`: User profile đã normalize

  - `constraints`: Constraints cho workout plan

  - `candidates`: List các exercise candidates

  - `candidate_ids`: Set các candidate IDs (để validation)

  - `documents`: LangChain Documents từ candidates

  - `draft_plan`: Draft plan từ LLM

  - `final_plan`: Final plan sau khi enrich

  - `internal_goal`: Structured internal goal (goal_style, priority_targets, priority_muscles, training_days, weekly_focus_by_day, risk_notes) từ bước intent

- `WorkoutPlanResult`: Dataclass kế thừa `BaseResult`

  - Chứa tất cả thông tin về workout plan result (bao gồm `internal_goal`)

- `init_workout_state(raw_input)`: Khởi tạo state từ raw input

  - Tạo `request_id`

  - Set default values cho các fields

- `to_workout_result(state)`: Convert graph state sang result object

**Cách hoạt động**: State được truyền qua các nodes trong graph, mỗi node update state và pass tiếp.

---

#### `domains/workout/schemas.py`

**Mục đích**: Pydantic schemas để validate và structure workout plan output.

**Các schemas**:

- `ExerciseItem`: Schema cho một exercise trong plan

  - `exercise_id`: ID của exercise (>= 1)

  - `sets`: Số sets (1-12)

  - `reps`: String mô tả reps (ví dụ: "8-12", "AMRAP")

  - `rest_sec`: Thời gian nghỉ (0-600 giây)

  - `notes`: Ghi chú

- `DayPlan`: Schema cho một ngày tập

  - `day`: Tên ngày (ví dụ: "Monday", "Day 1")

  - `exercises`: List `ExerciseItem`

- `WorkoutPlan`: Schema cho toàn bộ workout plan

  - `goal`: Mục tiêu (ví dụ: "hypertrophy", "fat_loss")

  - `days_per_week`: Số ngày tập mỗi tuần (1-7)

  - `session_minutes`: Thời lượng mỗi buổi (10-240 phút)

  - `split`: Loại split (ví dụ: "push/pull/legs")

  - `days`: List `DayPlan`

- `MuscleEnum`, `GoalStyleEnum`, `TrainingDayEnum`: Enum taxonomy for muscle groups, goal style, training days (mon..sun)

- `MuscleRankItem`: Item `{muscle, rank}` cho mỗi ngày

- `WeeklyFocusByDayItem`: Item `{training_day, focus:[{muscle, rank}]}`

- `IntentInternalGoal`: Schema cho internal_goal

  - `goal_style`: Enum goal style

  - `priority_targets`: List string (ưu tiên thẩm mỹ)

  - `priority_muscles`: List muscle từ taxonomy

  - `training_days`: List mon..sun (unique, length = days_per_week)

  - `weekly_focus_by_day`: List per day; each item is `{training_day, focus}`

  - `risk_notes`: List string (logic warnings)

  - Validator ensures training_days/weekly_focus_by_day unique and no duplicate muscle/rank per day

**Cách hoạt động**: 

- LLM client sử dụng `WorkoutPlan` schema để đảm bảo output plan đúng format.

- Intent node sử dụng `IntentInternalGoal` để nhận structured internal_goal.

---

#### `domains/workout/contract.py`

**Mục đích**: Định nghĩa taxonomy/contract cho Intent → Internal Goal và helper validation.

**Các thành phần chính**:

- `MUSCLE_TAXONOMY`, `GOAL_STYLE_ENUM`, `TRAINING_DAY_ENUM`: Enum lists for muscles, goal styles, training days

- `PRIORITY_TARGET_SUGGESTIONS`: Gợi ý target cho UI/autocomplete

- `MUSCLE_ALIASES`: Canonicalization (glutes -> hips)

- `is_valid_muscle()`, `is_valid_goal_style()`, `is_valid_training_day()`: Helper validation

- `validate_priority_muscles()`, `validate_training_days()`, `validate_weekly_focus_by_day()`, `validate_intent_internal_goal()`: Validate output internal_goal

**Cách hoạt động**: Contract này được dùng bởi schema và planning để đồng bộ FE/BE và validate output LLM trước khi dùng.

---

#### `domains/workout/graph.py`

**Mục đích**: Định nghĩa và build workout planning graph.

**Các thành phần chính**:

- `build_workout_graph()`: Build LangGraph StateGraph

  - Tạo graph với các nodes: profile, constraints, intent, retrieval, plan, evaluate, enrich

  - Định nghĩa edges và conditional routing

  - Return compiled graph

- `get_workout_graph()`: Lazy load singleton graph instance

- `run_workout_planning_pipeline(raw_input)`: Main entry point

  - Khởi tạo state từ raw input

  - Execute graph

  - Convert state sang result

  - Return `WorkoutPlanResult`

**Graph flow**:

```



START → profile → constraints → intent → retrieval → plan → evaluate



                                                      ↓



                                                   (có issues?)



                                                      ↓



                                              plan (retry) hoặc enrich



                                                      ↓



                                                    END



```

**Cách hoạt động**:

1. `run_workout_planning_pipeline()` được gọi từ view

2. Khởi tạo state và thêm audit event "pipeline_start"

3. Graph execute từng node theo thứ tự (profile → constraints → intent → retrieval → plan → evaluate)

4. Node `intent` sinh internal_goal từ goal_text (goal_style, priority_muscles, training_days, weekly_focus_by_day; fail -> warning, fallback taxonomy)

5. Node `evaluate` quyết định có cần retry không

6. Cuối cùng node `enrich` làm giàu plan với metadata

7. Convert state sang result và return

---

#### `domains/workout/nodes.py`

**Mục đích**: Định nghĩa các nodes (functions) trong workout graph.

**Các nodes**:

- `node_profile(state)`: Normalize user input thành profile

  - Gọi `normalize_profile()` từ `services/profile.py`

  - Log event "profile_done"

  - Return updated state với `profile`

- `node_constraints(state)`: Build constraints từ profile

  - Gọi `build_constraints()` từ `services/constraints.py`

  - Set `max_iter` từ constraints

  - Log event "constraints_done"

  - Return updated state với `constraints` và `max_iter`

- `node_intent(state)`: Intent → Internal Goal

  - Gọi `parse_intent_internal_goal_with_llm()` từ `services/planning.py`

  - Lưu `internal_goal` vào state và profile

  - Nếu fail: add warning + audit, không block pipeline (retrieval fallback taxonomy)

  - Log event "intent_done" hoặc "intent_failed"

- `node_retrieval(state)`: Retrieve exercise candidates

  - Gọi `build_candidate_pack()` từ `services/retrieval.py`

  - Convert candidates sang LangChain Documents

  - Log event "retrieval_done" với candidate count

  - Return updated state với `candidates`, `candidate_ids`, `documents`

- `node_plan(state)`: Generate workout plan với LLM

  - Lấy iteration number

  - Gọi `generate_plan_with_llm()` từ `services/planning.py`

  - Pass `issues` và `prev_plan` nếu đang retry

  - Log event "draft_done"

  - Return updated state với `draft_plan`

- `node_evaluate(state)`: Evaluate plan và tìm issues

  - Gọi `evaluate_plan()` từ `services/evaluation.py`

  - Check issues: invalid exercise_id, min/max exercises per day (constraints)

  - Warnings: duration > session_minutes; missing rank1 focus coverage (weekly_focus_by_day)

  - Quyết định có cần retry không

  - Log event "evaluate_done"

  - Return updated state với `issues`, `warnings`, `iteration`

- `route_after_eval(state)`: Conditional routing sau evaluate

  - Nếu không có issues → "enrich"

  - Nếu có issues nhưng đã hết iteration → "enrich" (stop)

  - Nếu có issues và còn iteration → "plan" (retry)

- `node_enrich(state)`: Enrich plan với exercise metadata

  - Gọi `enrich_plan()` từ `services/formatting.py`

  - Thêm title, muscle_groups, image_url vào mỗi exercise

  - Log event "pipeline_end"

  - Return updated state với `final_plan`

**Cách hoạt động**: Mỗi node là một function nhận state, xử lý, và return updated state. LangGraph tự động merge states.

---

#### `domains/workout/services/` - Business Logic

##### `domains/workout/services/profile.py`

**Mục đích**: Normalize và validate user input thành profile chuẩn.

**Các hàm chính**:

- `normalize_profile(raw)`: Normalize raw input

  - Parse `goal_text` (fallback từ `goal` legacy nếu có)

  - Parse `days_per_week` và `session_minutes` thành int

  - Canonicalize training_days (mon..sun); fallback default per days_per_week if missing/invalid

  - Parse optional metrics: `sex`, `height`, `weight`, `waist`, `hip`, `chest`

  - Parse `experience` và `equipment` (CSV string → list)

  - Giữ `user_id`, `internal_goal` (nếu có), `seed` (optional)

  - Return dict với các fields đã normalize

**Cách hoạt động**: Đảm bảo input luôn có format nhất quán trước khi xử lý.

---

##### `domains/workout/services/constraints.py`

**Mục đích**: Build constraints cho workout plan generation.

**Các hàm chính**:

- `build_constraints(profile)`: Build constraints dict

  - `max_repair_iterations`: Số lần retry tối đa (2)

  - `max_exercises_per_day`: Số bài tối đa mỗi ngày (6)

  - `max_repeat_same_exercise_per_week`: Số lần lặp lại exercise (1)

**Cách hoạt động**: Constraints được pass vào LLM prompt để guide generation.

---

##### `domains/workout/services/retrieval.py`

**Mục đích**: Retrieve và rerank exercise candidates từ database.

**Các hàm chính**:

- `build_candidate_pack(profile, constraints)`: Build candidate pack

  - Lấy `goal_text` và `internal_goal` (goal_style, priority_muscles) từ profile

  - Ưu tiên `priority_muscles`; nếu trống → fallback `MUSCLE_TAXONOMY`

  - Với mỗi muscle group:

    - Tạo semantic query: `"{goal_style hoặc goal_text} exercise for {muscle}"`

    - Gọi `retrieve_exercises()` với semantic search (nếu Postgres + pgvector)

    - Fallback sang muscle-only search nếu quá ít results

  - Global fallback nếu pool quá nhỏ (< 30)

  - **Rerank candidates** với `RerankService` (nếu enabled)

    - Tạo query từ goal_style/goal_text + top priority muscles

    - Rerank để cải thiện relevance

  - Cache kết quả theo profile/user_id để tránh spam

  - Return list candidates với format: `{id, title, muscle_groups, image_url, image_file, score, reason}`

- `candidate_pack_to_documents(candidates)`: Convert candidates sang LangChain Documents

  - Tạo `Document` với `page_content` (title + muscles + equipment + level)

  - Metadata chứa id, title, muscle_groups, equipment, level

  - Dùng cho LLM context

**Các constants**:

- `DEFAULT_K = 55`: Giới hạn số candidates

- `RETRIEVAL_CACHE_TTL = 900`: Cache TTL (15 phút)

- `USE_RERANK = True`: Bật/tắt rerank

- `RERANK_TOP_N = 30`: Số lượng candidates sau rerank

**Cách hoạt động**:

1. Build query từ profile

2. Retrieve exercises từ database (semantic hoặc keyword)

3. Rerank để cải thiện relevance

4. Cache kết quả

5. Convert sang Documents cho LLM

---

##### `domains/workout/services/planning.py`

**Mục đích**: Generate workout plan với LLM.

**Các hàm chính**:

- `parse_intent_internal_goal_with_llm(llm, profile)`: Parse goal_text -> internal_goal (goal_style, training_days, weekly_focus_by_day)

  - Build intent prompt với `_build_intent_prompt()`

  - Gọi `llm.generate_structured()` với schema `IntentInternalGoal`

  - Validate with `validate_intent_internal_goal()` (days_per_week/training_days), canonicalize glutes->hips; if fail return error dict

  - Cache theo hash prompt (bucket `intent_prompt`)

- `_build_intent_prompt(profile)`: Build prompt cho Intent → Internal Goal

  - Include goal_text, taxonomy muscles, enum goal_style/training_days, rules for weekly_focus_by_day + risk_notes

- `generate_plan_with_llm(llm, profile, constraints, candidates, ...)`: Main function

  - Gọi `_guard_before_llm()` để validate input

  - Nếu guard fail, return error dict (không gọi LLM)

  - Build prompt với `_build_prompt()`

  - Cache prompt theo hash để tránh spam

  - Gọi `llm.generate_plan_json()` với prompt

  - Cache result

  - Return plan dict

- `_guard_before_llm(profile, constraints, candidates)`: Hard validation

  - Check `days_per_week` trong [1, 7]

  - Check `session_minutes` trong [10, 240]

  - Validate `internal_goal` (nếu có) theo contract

  - Check `max_exercises_per_day` trong [1, 20]

  - Check `len(candidates) >= 20`

  - Return error dict nếu fail, `None` nếu pass

- `_build_prompt(profile, constraints, candidates, ...)`: Build LLM prompt

  - Include profile, constraints, candidate list

  - Include `prev_plan` và `issues` nếu đang retry

  - If training_days present, enforce day/training_day labels in mon..sun order

  - Recommend primary_muscle + min_exercises_per_day (if set)

  - Format candidates từ Documents hoặc fallback

  - Return prompt string

- `_format_candidate_lines_from_docs(documents, max_items)`: Format từ Documents

  - Format: `id={id} | {title} | muscles={...} | equip={...} | level={...}`

  - Giới hạn `max_items=45` để tránh prompt quá dài

- `_format_candidate_lines_fallback(candidates)`: Format từ candidates dict

  - Fallback nếu không có Documents

**Cách hoạt động**:

1. Validate input trước khi gọi LLM (bao gồm internal_goal nếu có)

2. Build prompt với đầy đủ context

3. Cache để tránh duplicate calls

4. Gọi LLM với structured output

5. Return plan dict

---

##### `domains/workout/services/evaluation.py`

**Mục đích**: Evaluate workout plan và tìm issues/warnings.

**Các hàm chính**:

- `evaluate_plan(draft_plan, candidates, profile, constraints)`: Main function

  - Validate exercise_id in candidate pack

  - Check exercises per day against min_exercises_per_day / max_exercises_per_day

  - Estimate duration with `_estimate_minutes()` -> warning if > session_minutes

  - Warn if a day has no rank1 muscle coverage (weekly_focus_by_day)

  - Primary muscle inferred from candidate pack (fallback from plan field if present)

  - Return dict với `issues` và `warnings`

- `_estimate_minutes(day)`: Estimate thời lượng một ngày

  - Formula: `sets * (1.0 + rest_sec/60.0)` cho mỗi exercise

  - Sum tất cả exercises

**Cách hoạt động**:

1. Validate plan theo các rules

2. Tìm issues (bắt buộc sửa) và warnings (cảnh báo)

3. Return để graph quyết định có retry không

---

##### `domains/workout/services/formatting.py`

**Mục đích**: Enrich workout plan với exercise metadata.

**Các hàm chính**:

- `enrich_plan(draft_plan, candidates)`: Enrich plan

  - Tạo lookup dict từ candidates theo id

  - Với mỗi exercise trong plan:

    - Lookup metadata từ candidates

    - Thêm `title`, `muscle_groups`, `image_url`, `image_file`

  - Return enriched plan

**Cách hoạt động**: Plan từ LLM chỉ có `exercise_id`, function này thêm metadata để frontend hiển thị.

---

## 📁 `services/` - Legacy Services

Thư mục chứa các low-level services được dùng bởi nhiều components.

### `services/retriever.py`

**Mục đích**: Low-level exercise retrieval từ database.

**Các hàm chính**:

- `retrieve_exercises(q, muscles, limit, use_semantic)`: Retrieve exercises

  - `q`: Query string (optional)

  - `muscles`: List muscle groups (optional)

  - `limit`: Số lượng kết quả (default 20, max 100)

  - `use_semantic`: Bật semantic search (nếu Postgres + pgvector)

**Cách hoạt động**:

- **Semantic path** (nếu `use_semantic=True` và Postgres):

  - Embed query với `embed_query()`

  - Query với `CosineDistance` trên `embedding` field

  - Filter theo `muscle_groups` nếu có

  - Order by distance, limit results

- **Fallback path** (SQLite hoặc không có embedding):

  - Filter theo `title__icontains` nếu có query

  - Filter theo `muscle_groups__contains` nếu có muscles

  - Order by id, limit results

**Sử dụng**: Được gọi bởi `retrieval.py` để lấy exercises từ database.

---

### `services/embedding_service.py`

**Mục đích**: Generate embeddings cho exercises và queries.

**Các hàm chính**:

- `embed_texts(texts, task_type, model, output_dim, ...)`: Embed list texts

  - Sử dụng OpenAI Embeddings API

  - Support `text-embedding-3-*` với custom dimensions

  - Retry logic với exponential backoff

  - Parse `Retry-After` header từ errors

  - Return list of embedding vectors

- `embed_document(texts, output_dim)`: Wrapper cho document embedding

  - Default `task_type="RETRIEVAL_DOCUMENT"`

- `embed_query(text, output_dim)`: Embed single query

  - Wrapper cho `embed_texts([text], ...)`

  - Return single vector

- `get_client()`: Get OpenAI client singleton

  - Lazy initialization

  - Read `OPENAI_API_KEY` từ env

**Các constants**:

- `DEFAULT_EMBED_MODEL`: "text-embedding-3-small"

- `DEFAULT_DIM`: 1536

**Cách hoạt động**:

1. Get OpenAI client

2. Call `embeddings.create()` với texts

3. Handle rate limits với retry

4. Return embeddings

**Sử dụng**: 

- Generate embeddings cho exercises (management command)

- Embed queries cho semantic search

---

### `services/rerank_service.py`

**Mục đích**: Rerank candidates để cải thiện relevance.

**Các thành phần chính**:

- `RerankService`: Main service class

  - Hỗ trợ providers: "cohere", "jina", "none"

  - Config từ env: `RERANK_PROVIDER`, `COHERE_API_KEY`/`RERANK_API_KEY`, `RERANK_MODEL`

- `rerank(query, candidates, top_n)`: Main method

  - Rerank candidates dựa trên query

  - Update `score` với relevance score từ rerank

  - Return reranked list

- `_cohere_rerank()`: Implementation cho Cohere

  - Sử dụng `cohere.Client.rerank()`

  - Format documents từ candidates

  - Map results về candidates với scores

- `_jina_rerank()`: Implementation cho Jina

  - HTTP POST đến Jina API

  - Similar flow như Cohere

**Cách hoạt động**:

1. Format candidates thành documents

2. Call rerank API với query

3. Map results về candidates với new scores

4. Return top N candidates

**Sử dụng**: Được gọi bởi `retrieval.py` sau khi retrieve candidates.

---

## 📁 `management/commands/` - Django Management Commands

### `management/commands/import_exercises.py`

**Mục đích**: Import exercises từ CSV vào database.

**Các hàm chính**:

- `Command.handle()`: Main command handler

  - Đọc CSV file

  - Parse rows

  - Normalize muscles với `normalize_muscles()`

  - Infer equipment với `infer_equipment()`

  - Create/update Exercise objects

- `normalize_muscles(body_part_raw)`: Normalize muscle groups

  - Parse comma-separated string

  - Map một số values (ví dụ: "waist" → "core")

- `infer_equipment(title)`: Infer equipment từ title

  - Check keywords trong title

  - Return equipment type

**Cách sử dụng**:

```bash



python manage.py import_exercises --csv exercises.csv



```

---

### `management/commands/backfill_exercise_embeddings.py`

**Mục đích**: Generate embeddings cho exercises đã có trong database.

**Các hàm chính**:

- `Command.handle()`: Main command handler

  - Query exercises (filter null embeddings nếu không `--rebuild`)

  - Batch process với `--batch-size`

  - Build embedding text với `_build_embedding_text()`

  - Call `embed_document()` để generate embeddings

  - Bulk update database

- `_build_embedding_text(ex)`: Build text để embed

  - Format: `{title} | {body_part_raw} | {muscle_groups}`

**Các options**:

- `--limit`: Số lượng exercises tối đa

- `--batch-size`: Batch size (default 32)

- `--rebuild`: Overwrite existing embeddings

- `--dim`: Embedding dimensions (default 1536)

**Cách sử dụng**:

```bash



python manage.py backfill_exercise_embeddings --batch-size 32



```

---

## 📁 Root Files

### `models.py`

**Mục đích**: Django models cho database.

**Các models**:

- `Exercise`: Model cho exercise

  - `title`: Tên exercise

  - `body_part_raw`: Body part gốc từ CSV

  - `muscle_groups`: JSONField chứa list muscle groups

  - `image_url`, `image_file`: URLs và paths cho images

  - `embedding`: VectorField (pgvector) cho semantic search

  - `embedding_text`: Text đã dùng để embed

  - `embedding_model`: Model name đã dùng

  - `created_at`: Timestamp

**Indexes**:

- HNSW index trên `embedding` field cho fast similarity search

---

### `views.py`

**Mục đích**: Django REST API views.

**Các views**:

- `ExerciseListView`: List tất cả exercises

  - GET `/api/backend/exercises/`

  - Return paginated list

- `ExerciseSearchView`: Search exercises

  - GET `/api/backend/exercises/search/`

  - Query params: `q` (query), `muscles` (comma-separated), `limit`

  - Gọi `retrieve_exercises()`

  - Return results với metadata

- `WorkoutPlanGenerateAgentView`: Generate workout plan

  - POST `/api/backend/plan/generate-agent/`

  - Validate input với `WorkoutPlanGenerateSerializer`

  - Gọi `run_workout_planning_pipeline()`

  - Return plan với warnings, issues, audit

---

### `urls.py`

**Mục đích**: URL routing cho backend app.

**URLs**:

- `/exercises/` → `ExerciseListView`

- `/exercises/search/` → `ExerciseSearchView`

- `/plan/generate-agent/` → `WorkoutPlanGenerateAgentView`

---

### `serializers.py`

**Mục đích**: DRF serializers cho API.

**Các serializers**:

- `ExerciseSerializer`: Serialize Exercise model

  - Fields: `id`, `title`, `muscle_groups`, `image_url`, `image_file`

---

### `serializers_plan.py`

**Mục đích**: Serializers cho workout plan generation.

**Các serializers**:

- `WorkoutPlanGenerateSerializer`: Validate input cho plan generation

  - `goal_text`: CharField (bắt buộc)

  - `days_per_week`: IntegerField (1-7)

  - `session_minutes`: IntegerField (10-240)

  - `training_days`: List mon..sun (optional; unique; length = days_per_week; default if missing)

  - `sex`: ChoiceField ["male", "female"] (optional)

  - `height`, `weight`, `waist`, `hip`, `chest`: FloatField (optional)

  - `experience`: ChoiceField ["beginner", "intermediate", "advanced"] (optional)

  - `equipment`: CharField (optional, CSV string)

  - `seed`: IntegerField (optional, cho reproducibility)

---

## 📁 `config/` - Django Project Config

### `config/settings.py`

**Mục đích**: Django settings.

**Các settings quan trọng**:

- Database: PostgreSQL với pgvector

- Installed apps: `backend`, `rest_framework`, `corsheaders`, `drf_spectacular`

- CORS: Allow all origins (development)

- API docs: Swagger với drf-spectacular

---

### `config/urls.py`

**Mục đích**: Root URL configuration.

**URLs**:

- `/admin/` → Django admin

- `/api/schema/` → OpenAPI schema

- `/api/docs/` → Swagger UI

- `/api/backend/` → Include backend URLs

---

## Workflow tổng thể

### 1. User gửi request

```



POST /api/backend/plan/generate-agent/



{



    "goal_text": "Giảm mỡ, rõ cơ bụng, vai rộng hơn",



    "days_per_week": 4,



    "session_minutes": 60,



    "training_days": ["mon", "wed", "fri", "sat"],



    "experience": "intermediate",



    "equipment": "dumbbell, pullup_bar"



}



```

### 2. View xử lý

- Validate với `WorkoutPlanGenerateSerializer`

- Gọi `run_workout_planning_pipeline()`

### 3. Graph execution

```



profile → constraints → intent → retrieval → plan → evaluate → (retry?) → enrich



```

### 4. Các bước chi tiết

1. **Profile**: Normalize input

2. **Constraints**: Build constraints

3. **Intent**:

   - Parse goal_text → internal_goal (goal_style, priority_targets, priority_muscles, training_days, weekly_focus_by_day, risk_notes)

   - Nếu fail: warning, fallback taxonomy cho retrieval

4. **Retrieval**: 

   - Retrieve exercises từ database

   - Rerank candidates

   - Convert sang Documents

5. **Plan**: 

   - Build prompt với profile, constraints, candidates

   - Gọi LLM để generate plan

6. **Evaluate**: 

   - Check issues (invalid IDs, min/max exercises per day) + warnings (duration, rank1 focus coverage)

   - Nếu có issues và còn iteration → retry

7. **Enrich**: 

   - Thêm metadata vào exercises

   - Return final plan

### 5. Response

```json



{



  "request_id": "...",



  "plan": {



    "goal": "hypertrophy",



    "days_per_week": 4,



    "days": [...]



  },



  "warnings": [...],



  "issues": [...],



  "audit": {...}



}



```

---

## Mở rộng hệ thống

### Thêm domain mới (ví dụ: Meal Planning)

1. **Tạo folder** `domains/meal/`

2. **Tạo các file tương tự workout**:

   - `state.py`: `MealGraphState`, `MealPlanResult`

   - `schemas.py`: `MealPlan` Pydantic schema

   - `graph.py`: `build_meal_graph()`, `run_meal_planning_pipeline()`

   - `nodes.py`: Các nodes cho meal planning

   - `services/`: Business logic cho meal planning

3. **Export trong** `domains/meal/__init__.py`:

   ```python



   from .graph import run_meal_planning_pipeline



   from .state import MealPlanResult



   ```

4. **Thêm view trong** `views.py`:

   ```python



   from backend.domains.meal import run_meal_planning_pipeline



   ```

5. **Thêm URL trong** `urls.py`:

   ```python



   path("meal/plan/generate/", MealPlanGenerateView.as_view())



   ```

---

## Best Practices

1. **State management**: Luôn update state immutably, không mutate trực tiếp

2. **Error handling**: Sử dụng `issues` và `warnings` thay vì raise exceptions

3. **Caching**: Cache retrieval và LLM calls để giảm chi phí

4. **Validation**: Validate input sớm (guard functions) trước khi gọi LLM

5. **Audit**: Log tất cả events để debug và monitoring

6. **Type safety**: Sử dụng TypedDict và Pydantic schemas

7. **Separation of concerns**: Business logic trong `services/`, orchestration trong `nodes.py`

---

## Environment Variables

```bash



# LLM



LLM_PROVIDER=gemini  # hoặc "openai"



OPENAI_API_KEY=...



OPENAI_MODEL=gpt-4o-mini



GEMINI_API_KEY=...



GEMINI_MODEL=gemini-1.5-flash







# Embeddings



OPENAI_EMBED_MODEL=text-embedding-3-small



OPENAI_EMBED_DIM=1536







# Rerank



RERANK_PROVIDER=cohere  # hoặc "jina", "none"



COHERE_API_KEY=...



RERANK_API_KEY=...      # fallback cho provider "jina" hoặc custom



RERANK_MODEL=rerank-english-v3.0







# Django



DJANGO_SECRET_KEY=...



DJANGO_DEBUG=1







# Database



DB_NAME=aipt_db



DB_USER=aipt_user



DB_PASSWORD=...



DB_HOST=127.0.0.1



DB_PORT=5432



```

---

## Notes

- `services/retriever.py` và `services/embedding_service.py` được giữ lại vì được dùng bởi nhiều components

- Cache là in-memory, sẽ mất khi restart server (có thể upgrade sang Redis sau)

- Rerank có thể disable bằng `USE_RERANK = False` hoặc `RERANK_PROVIDER=none`

- Graph execution là synchronous, có thể upgrade sang async nếu cần

---

# Kiến trúc Frontend - AI Personal Trainer

## Tổng quan

Frontend được xây dựng với **React 18** và **Vite** làm build tool. Sử dụng **Tailwind CSS** cho styling và component-based architecture đơn giản. Frontend giao tiếp với Django backend qua REST API để tạo và hiển thị workout plans.

## Cấu trúc thư mục và mô tả chi tiết

```



frontend/



├── src/



│   ├── main.jsx              # Entry point



│   ├── App.jsx               # Root component



│   ├── index.css             # Global styles (Tailwind)



│   └── components/           # React components



│       ├── WorkoutPlanForm.jsx      # Form để nhập thông tin workout



│       └── WorkoutPlanResult.jsx    # Component hiển thị kết quả



├── index.html                # HTML template



├── vite.config.js            # Vite configuration



├── tailwind.config.js        # Tailwind CSS configuration



├── postcss.config.js         # PostCSS configuration



└── package.json              # Dependencies và scripts



```

---

## 📁 `src/` - Source Code

### `src/main.jsx`

**Mục đích**: Entry point của ứng dụng React.

**Các thành phần chính**:

- Import React và ReactDOM

- Import `App` component và global CSS

- Render `App` vào DOM element `#root` với `React.StrictMode`

**Cách hoạt động**: Vite bundle file này và inject vào `index.html`. `React.StrictMode` giúp phát hiện các vấn đề tiềm ẩn trong development.

---

### `src/App.jsx`

**Mục đích**: Root component quản lý state và orchestration cho toàn bộ ứng dụng.

**Các thành phần chính**:

- **State management**:

  - `result`: Kết quả workout plan từ API (null khi chưa có)

  - `loading`: Trạng thái đang loading (boolean)

  - `error`: Thông báo lỗi (string hoặc null)

- **Functions**:

  - `handleSubmit(formData)`: Xử lý submit form

    - Set loading = true, clear error và result

    - POST request đến `/api/backend/plan/generate-agent/`

    - Parse JSON response và set result

    - Handle errors (connection errors, API errors)

    - Set loading = false khi xong

**UI Structure**:

- Container với gradient background (blue-50 to indigo-100)

- Header với title "AI Personal Trainer"

- `WorkoutPlanForm` component (trong card trắng)

- Error display (nếu có)

- `WorkoutPlanResult` component (nếu có result)

**Cách hoạt động**:

1. User nhập form và submit

2. `handleSubmit` được gọi với form data

3. Gửi POST request đến backend

4. Update state (loading, error, result)

5. Re-render với kết quả mới

---

### `src/components/WorkoutPlanForm.jsx`

**Mục đích**: Form component để user nhập thông tin cho workout plan.

**Các thành phần chính**:

- **Props**:

  - `onSubmit`: Callback function nhận form data

  - `loading`: Boolean để disable form khi đang submit

- **State**:

  - `formData`: Object chứa form values

    - `goal_text`: String (required)

    - `days_per_week`: Number (default: 4, range: 1-7)

    - `session_minutes`: Number (default: 60, range: 10-240)

    - `sex`, `experience`: String (optional)

    - `height`, `weight`, `waist`, `hip`, `chest`: Number (optional)

    - `equipment`: String CSV (optional)

    - `seed`: Number (optional)

- **Functions**:

  - `handleChange(e)`: Update formData khi input thay đổi

    - Giữ giá trị thô trong state, tách xử lý số ở bước build payload

  - `buildPayload()`: Chuẩn hóa payload trước khi submit

    - Convert numeric fields về number

    - Chỉ gửi optional fields khi có giá trị

  - `handleSubmit(e)`: Validate và submit form

    - Prevent default form submission

    - Validate `goal_text` không rỗng

    - Gọi `onSubmit(payload)`

**Form Fields**:

1. **Goal text** (textarea):

   - Required

2. **Days per week** (number input):

   - Min: 1, Max: 7

   - Required

3. **Session minutes** (number input):

   - Min: 10, Max: 240

   - Required

4. **Sex** (select):

   - Optional

5. **Experience** (select):

   - Optional

6. **Body metrics** (number inputs):

   - `height`, `weight`, `waist`, `hip`, `chest`

   - Optional

7. **Equipment** (text input, CSV):

   - Optional

8. **Seed** (number input):

   - Optional, cho reproducibility

**Styling**: Sử dụng Tailwind CSS với:

- Responsive design (mobile-first)

- Focus states với ring indigo

- Disabled states cho button khi loading

---

### `src/components/WorkoutPlanResult.jsx`

**Mục đích**: Component hiển thị kết quả workout plan từ API.

**Các thành phần chính**:

#### `WorkoutPlanResult` Component

- **Props**:

  - `result`: Object chứa response từ API

    - `request_id`: UUID của request

    - `plan`: Workout plan object

    - `warnings`: Array các cảnh báo

    - `issues`: Array các vấn đề

    - `audit`: Audit trail object

- **UI Sections**:

  1. **Request ID**: Hiển thị request ID trong card indigo

  2. **Warnings**: Yellow alert box nếu có warnings

  3. **Issues**: Red alert box nếu có issues

  4. **Plan Display**: Gọi `WorkoutPlanDisplay` để render plan

  5. **Audit Info**: Collapsible details với JSON audit data

  6. **Full JSON**: Collapsible details với toàn bộ response JSON

#### `WorkoutPlanDisplay` Component

- **Props**:

  - `plan`: Workout plan object hoặc string

- **Rendering Logic**:

  - Nếu `plan` là string → render trong `<pre>` tag

  - Nếu `plan` là object:

    - Hiển thị metadata: goal, days_per_week, session_minutes, split

    - Render từng ngày trong `plan.days`:

      - Header với tên ngày

      - List exercises với:

        - Image (nếu có `image_url`)

        - Title, exercise_id, sets, reps, rest_sec

        - Muscle groups

        - Notes

    - Collapsible section cho các fields khác

- **Image Handling**:

  - Lazy loading

  - Error handling: Ẩn image và hiển thị placeholder nếu load fail

#### `JsonValue` Component

- **Props**:

  - `value`: Giá trị bất kỳ (string, number, boolean, object, array)

  - `level`: Depth level (default: 0) cho indentation

- **Rendering Logic**:

  - Recursive component để render nested JSON

  - Color coding:

    - Strings: green

    - Numbers: blue

    - Booleans: purple

    - Null: gray

  - Arrays và objects với indentation và borders

**Styling**: 

- Card-based layout với shadows

- Color-coded sections (indigo cho headers, gray cho content)

- Responsive grid cho exercise info

- Collapsible details với hover effects

---

### `src/index.css`

**Mục đích**: Global CSS styles và Tailwind directives.

**Nội dung**:

- `@tailwind base`: Tailwind base styles

- `@tailwind components`: Tailwind component classes

- `@tailwind utilities`: Tailwind utility classes

- Custom body styles:

  - Font family stack (system fonts)

  - Font smoothing (antialiased)

**Cách hoạt động**: Tailwind PostCSS plugin process file này và generate CSS từ các utility classes được sử dụng trong components.

---

## 📁 Root Files

### `index.html`

**Mục đích**: HTML template cho ứng dụng.

**Cấu trúc**:

- Standard HTML5 structure

- `<div id="root">` để React mount vào

- Vite inject script tags vào đây khi build

---

### `vite.config.js`

**Mục đích**: Configuration cho Vite build tool.

**Các thành phần chính**:

- **Plugins**:

  - `@vitejs/plugin-react`: Hỗ trợ React (JSX, HMR)

- **Server config**:

  - `port: 3000`: Dev server chạy trên port 3000

  - `proxy`: Proxy API requests đến Django backend

    - Path: `/api/*`

    - Target: `http://127.0.0.1:8000`

    - `changeOrigin: true`: Thay đổi Origin header

    - Event handlers để log proxy requests/responses

**Cách hoạt động**:

- Dev server chạy trên `http://localhost:3000`

- Requests đến `/api/*` được proxy đến Django backend

- Giúp tránh CORS issues trong development

---

### `tailwind.config.js`

**Mục đích**: Configuration cho Tailwind CSS.

**Cấu trúc** (mặc định):

- `content`: Array các file patterns để scan classes

  - `"./index.html"`

  - `"./src/**/*.{js,ts,jsx,tsx}"`

- `theme`: Custom theme (nếu có)

- `plugins`: Tailwind plugins (nếu có)

**Cách hoạt động**: Tailwind scan các file trong `content` và chỉ generate CSS cho các classes được sử dụng (purge unused).

---

### `package.json`

**Mục đích**: Dependencies và scripts cho project.

**Dependencies**:

- `react`: ^18.2.0

- `react-dom`: ^18.2.0

**DevDependencies**:

- `@types/react`, `@types/react-dom`: TypeScript types (cho IDE support)

- `@vitejs/plugin-react`: Vite plugin cho React

- `autoprefixer`: PostCSS plugin cho vendor prefixes

- `postcss`: CSS processor

- `tailwindcss`: Utility-first CSS framework

- `vite`: Build tool và dev server

**Scripts**:

- `dev`: Chạy Vite dev server

- `build`: Build production bundle

- `preview`: Preview production build

---

## Component Architecture

### Component Hierarchy

```



App (root)



├── WorkoutPlanForm



│   └── Form inputs (controlled components)



└── WorkoutPlanResult (conditional render)



    ├── WorkoutPlanDisplay



    │   └── JsonValue (recursive)



    └── Collapsible sections



```

### State Flow

1. **Form State**: Local state trong `WorkoutPlanForm`

2. **App State**: Lifted state trong `App` component

   - `result`, `loading`, `error`

3. **Data Flow**: Unidirectional

   - Form → `handleSubmit` → API → `setResult` → Re-render

### Props Flow

- **Down**: `onSubmit`, `loading` từ App → Form

- **Down**: `result` từ App → Result component

---

## API Integration

### Endpoint

- **URL**: `/api/backend/plan/generate-agent/`

- **Method**: POST

- **Headers**: `Content-Type: application/json`

### Request Format

```json



{



  "goal_text": "Giảm mỡ, rõ cơ bụng, vai rộng hơn",



  "days_per_week": 4,



  "session_minutes": 60,



  "experience": "intermediate",



  "equipment": "dumbbell, pullup_bar",



  "seed": 123  // optional



}



```

### Response Format

```json



{



  "request_id": "uuid",



  "plan": {



    "goal": "hypertrophy",



    "days_per_week": 4,



    "session_minutes": 60,



    "split": "push/pull/legs",



    "days": [



      {



        "day": "Monday",



        "exercises": [



          {



            "exercise_id": 1,



            "title": "Bench Press",



            "sets": 4,



            "reps": "8-12",



            "rest_sec": 90,



            "muscle_groups": ["chest", "triceps"],



            "image_url": "https://...",



            "notes": "..."



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

### Error Handling

- **Connection errors**: Hiển thị message về Django server không chạy

- **API errors**: Hiển thị `errorData.detail` từ response

- **Network errors**: Catch và hiển thị generic error message

---

## Styling Approach

### Tailwind CSS

- **Utility-first**: Sử dụng utility classes thay vì custom CSS

- **Responsive**: Mobile-first với breakpoints (md:, lg:, etc.)

- **Color scheme**: Indigo primary, gray neutrals

- **Components**: Card-based layout với shadows và borders

### Design Patterns

- **Gradient backgrounds**: `bg-gradient-to-br from-blue-50 to-indigo-100`

- **Card components**: `bg-white rounded-lg shadow-lg p-6`

- **Form inputs**: Focus states với `focus:ring-2 focus:ring-indigo-500`

- **Buttons**: Disabled states với `disabled:opacity-50`

---

## Development Workflow

### Local Development

1. **Start dev server**:

   ```bash



   cd frontend



   npm run dev



   ```

   - Server chạy trên `http://localhost:3000`

   - Hot Module Replacement (HMR) enabled

2. **Proxy setup**:

   - Requests đến `/api/*` tự động proxy đến Django backend

   - Đảm bảo Django chạy trên `http://127.0.0.1:8000`

3. **Build production**:

   ```bash



   npm run build



   ```

   - Output trong `frontend/dist/`

   - Optimized và minified

### File Structure Best Practices

- **Components**: Mỗi component trong file riêng

- **Naming**: PascalCase cho components, camelCase cho functions

- **Separation**: Logic và UI tách biệt rõ ràng

---

## Mở rộng Frontend

### Thêm Component mới

1. Tạo file trong `src/components/`

2. Export component

3. Import và sử dụng trong `App.jsx` hoặc component khác

### Thêm State Management

- **Hiện tại**: Local state với `useState`

- **Có thể nâng cấp**: 

  - Context API cho global state

  - Redux/Zustand nếu cần state management phức tạp

### Thêm Routing

- **Hiện tại**: Single page application

- **Có thể thêm**: React Router cho multi-page

  ```bash



  npm install react-router-dom



  ```

### Thêm API Service Layer

- **Hiện tại**: Direct fetch trong component

- **Có thể tạo**: `src/services/api.js` để centralize API calls

  ```javascript



  // src/services/api.js



  export const generateWorkoutPlan = async (formData) => {



    const response = await fetch('/api/backend/plan/generate-agent/', {



      method: 'POST',



      headers: { 'Content-Type': 'application/json' },



      body: JSON.stringify(formData),



    })



    return response.json()



  }



  ```

### Thêm Form Validation

- **Hiện tại**: HTML5 validation (required, min, max)

- **Có thể thêm**: 

  - React Hook Form

  - Yup/Zod cho schema validation

### Thêm Error Boundaries

- **Hiện tại**: Try-catch trong `handleSubmit`

- **Có thể thêm**: React Error Boundary component để catch render errors

---

## Best Practices

1. **Component composition**: Tách components nhỏ, reusable

2. **Props validation**: Có thể thêm PropTypes hoặc TypeScript

3. **Error handling**: Luôn handle errors và hiển thị user-friendly messages

4. **Loading states**: Disable form và hiển thị loading indicator

5. **Accessibility**: Sử dụng semantic HTML và ARIA attributes

6. **Performance**: 

   - Lazy loading images

   - Memoization nếu cần (React.memo, useMemo)

7. **Code organization**: Mỗi component trong file riêng, clear naming

---

## Environment Variables

Frontend không sử dụng environment variables hiện tại, nhưng có thể thêm:

```bash



# .env



VITE_API_BASE_URL=http://localhost:8000



VITE_APP_NAME=AI Personal Trainer



```

Sử dụng trong code:

```javascript



const API_BASE_URL = import.meta.env.VITE_API_BASE_URL



```

---

## Notes

- Frontend là single-page application (SPA) không có routing

- State management đơn giản với React hooks, chưa cần state management library

- API calls được thực hiện trực tiếp trong components, có thể refactor thành service layer

- Styling hoàn toàn dựa trên Tailwind CSS, không có custom CSS files

- Proxy setup trong Vite giúp tránh CORS issues trong development

- Production build có thể serve static files từ Django hoặc deploy riêng (CDN, Netlify, Vercel)
