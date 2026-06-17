# ScriptNova — Backend

Django REST API powering the ScriptNova AI blog generation platform. Built with Django 5.2, Django REST Framework, MySQL, and NVIDIA NIM inference APIs.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 5.2 + Django REST Framework |
| Database | MySQL |
| AI Models | NVIDIA NIM API (meta/llama-3.1-8b-instruct, meta/llama-3.3-70b-instruct) |
| Auth | Custom token-based middleware |
| CORS | django-corsheaders |

---

## Project Structure

```
ScriptNova-Backend/
├── config/
│   ├── settings.py          # Django settings (DB, installed apps, CORS)
│   ├── urls.py              # Root URL config — includes ScriptNova.urls
│   ├── wsgi.py
│   └── asgi.py
├── ScriptNova/
│   ├── models.py            # User + Blog models
│   ├── urls.py              # All API routes
│   ├── admin.py
│   ├── middleware/
│   │   └── auth.py          # Token auth middleware (@require_token decorator)
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_user_delete_product.py
│   │   ├── 0003_blog.py
│   │   ├── 0004_blog_prompt.py
│   │   └── 0005_blog_favourite.py
│   └── views/
│       ├── __init__.py      # Auth views (signup, login, getById, update)
│       ├── Authentication.py
│       └── Blogs.py         # All blog + AI generation views
├── manage.py
└── create_db.py             # Helper script to create the MySQL database
```

---

## Database Models

### User
| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | Primary key |
| username | CharField(20) | |
| email | EmailField | Unique |
| password | CharField(100) | Hashed |
| first_name | CharField(20) | |
| last_name | CharField(20) | |
| token | CharField(200) | Auth token, nullable |
| profile | CharField(100) | Profile image path, nullable |
| created_at | DateTimeField | Auto |
| updated_at | DateTimeField | Auto |

### Blog
| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Primary key |
| user | ForeignKey(User) | CASCADE delete |
| prompt | CharField(500) | Original user topic |
| title | CharField(500) | AI-suggested title |
| content | TextField | Markdown content |
| keywords | CharField(1000) | Comma-separated SEO keywords |
| tone | CharField(100) | e.g. Professional, Casual |
| length_preference | CharField(100) | e.g. Medium (1000-1500 words) |
| word_count | PositiveIntegerField | Auto-calculated on save |
| slug | SlugField(600) | Unique, auto-generated from title + UUID |
| favourite | CharField(20) | `'normal'` or `'favourite'` (like WhatsApp star) |
| created_at | DateTimeField | Auto |
| updated_at | DateTimeField | Auto |

**Auto-behaviours on `Blog.save()`:**
- `word_count` is auto-calculated from content if not provided
- `slug` is auto-generated as `slugify(title)[:550]-{uuid4[:8]}` if not set
- When title is updated via PATCH, slug is cleared and regenerated

---

## Setup

### Prerequisites
- Python 3.10+
- MySQL server running locally
- NVIDIA NIM API key from [build.nvidia.com](https://build.nvidia.com)

### 1. Clone and create virtual environment
```bash
git clone <repo-url>
cd ScriptNova-Backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install django djangorestframework django-cors-headers mysqlclient python-dotenv requests
```

### 3. Create the MySQL database
```bash
mysql -u root -p
CREATE DATABASE ScriptNova CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit;
```
Or run the helper script:
```bash
python create_db.py
```

### 4. Configure environment
Create a `.env` file in the root:
```env
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Update `config/settings.py` if your MySQL credentials differ:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ScriptNova',
        'USER': 'root',
        'PASSWORD': 'root123',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Start the development server
```bash
python manage.py runserver
```

Server runs at `http://localhost:8000`

---

## API Reference

All endpoints are prefixed at the root (e.g. `http://localhost:8000/signup/`).

Protected endpoints require the header:
```
Authorization: Bearer <token>
```

---

### Auth

#### `POST /signup/`
Register a new user.
```json
// Request
{ "username": "john", "email": "john@example.com", "password": "pass123", "first_name": "John", "last_name": "Doe" }

// Response
{ "success": true, "token": "abc123...", "user": { ... } }
```

#### `POST /login/`
Login with email and password.
```json
// Request
{ "email": "john@example.com", "password": "pass123" }

// Response
{ "success": true, "token": "abc123...", "user": { ... } }
```

#### `GET /user/<id>/`
Get user by ID. Protected.

#### `PATCH /user/update/`
Update user profile. Protected.

---

### AI Generation

#### `POST /generate-keywords/`
Generate 8 SEO keywords for a topic. Uses fast 8B model.
```json
// Request
{ "title": "ai in medical science" }

// Response
{ "success": true, "data": ["AI diagnostics", "machine learning healthcare", ...] }
```

#### `POST /generate-blog/`
Generate a full blog from a topic. Model suggests title, then writes article.
```json
// Request
{ "prompt": "ai in medical science", "keywords": ["..."], "tone": "Professional", "length": "Medium (1000-1500 words)" }

// Response
{ "success": true, "data": { "prompt": "...", "suggested_title": "...", "keywords": [...], "content": "..." } }
```

**Length options:** `Short (500-800 words)` / `Medium (1000-1500 words)` / `Long (2000+ words)`

**Tone options:** `Informative & Friendly` / `Professional` / `Casual` / `Humorous`

#### `POST /generate-title/`
Regenerate title for an existing article without rewriting the content.
```json
// Request
{ "prompt": "ai in medical science", "article_content": "...", "keywords": ["..."] }

// Response
{ "success": true, "data": { "suggested_title": "How AI Is Revolutionizing Modern Medicine" } }
```

#### `POST /rephrase-blog/`
Rephrase, rearrange, or regenerate an article.
```json
// Request
{ "article_content": "...", "mode": "rephrase" }
// mode: "rephrase" | "rearrange" | "regenerate"
// For "regenerate": also pass prompt, keywords, tone, length

// Response
{ "success": true, "data": { "content": "..." } }
```

---

### Blog CRUD

#### `GET /blogs/?limit=N&favourite=true`
List all user blogs. Optional filters:
- `?limit=5` — return only 5 most recent (used by generator sidebar)
- `?favourite=true` — return only starred blogs

```json
// Response
{ "success": true, "data": [ { "id": 1, "title": "...", "slug": "...", "favourite": "normal", "is_favourite": false, ... } ] }
```

Note: list response does **not** include `content` for performance. Fetch individual blog for full content.

#### `POST /blogs/`
Save a blog to the database.
```json
// Request
{ "prompt": "...", "title": "...", "content": "...", "keywords": "k1, k2", "tone": "...", "length_preference": "...", "word_count": 1200 }

// Response 201
{ "success": true, "data": { "id": 5, "slug": "how-ai-is-revolutionizing-a3f2b1c4", ... } }
```

#### `GET /blogs/<id>/`
Get a single blog including full content.

#### `PATCH /blogs/<id>/`
Update any blog fields. Partial updates supported — only send fields you want to change.
```json
// Request — update title only
{ "title": "New Better Title" }
// Slug auto-regenerates when title changes
```

Updatable fields: `prompt`, `title`, `content`, `keywords`, `tone`, `length_preference`, `word_count`, `favourite`

#### `DELETE /blogs/<id>/`
Delete a blog. Returns 204.

#### `GET /blogs/slug/<slug>/`
Fetch a blog by its slug instead of ID. Useful for clean URL navigation.
```json
// Response
{ "success": true, "data": { "id": 5, "slug": "how-ai-is-revolutionizing-a3f2b1c4", ... } }
```

#### `POST /blogs/<id>/favourite/`
Toggle the favourite status between `'normal'` and `'favourite'`.
```json
// Response
{ "success": true, "id": 5, "favourite": "favourite", "is_favourite": true }
```

#### `GET /blogs/stats/`
Dashboard stats for the current user.
```json
// Response
{ "success": true, "data": { "total": 12, "favourites": 3, "total_words": 14500 } }
```

---

## AI Model Strategy

| Task | Model | Timeout | Why |
|------|-------|---------|-----|
| Keywords, Title suggestion | `meta/llama-3.1-8b-instruct` | 180s | Fast — small output |
| Blog generation, Rephrase, Rearrange | `meta/llama-3.3-70b-instruct` | 360s | Quality — long output |

All API calls use `stream: False` explicitly and retry up to 3 times with backoff on timeout/connection errors.

One NVIDIA API key (`nvapi-...`) works for all models on [build.nvidia.com](https://build.nvidia.com).

---

## Authentication

ScriptNova uses a custom token middleware rather than Django's built-in auth system. Every request to a protected endpoint must include:

```
Authorization: Bearer <token>
```

The token is generated on signup/login and stored in the `User.token` field. The `@require_token` decorator on each view validates it and attaches the user to `request.auth_user`.

---

## CORS

CORS is fully open in development (`CORS_ALLOW_ALL_ORIGINS = True`). For production, restrict this in `settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "https://yourfrontenddomain.com",
]
```

---

## Migration History

| Migration | Change |
|-----------|--------|
| 0001_initial | User model |
| 0002_user_delete_product | Cleaned up old Product model |
| 0003_blog | Blog model (initial) |
| 0004_blog_prompt | Added `prompt` field to store original user topic |
| 0005_blog_favourite | Removed `status`, added `favourite` CharField |
