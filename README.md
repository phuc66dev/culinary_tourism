# Hệ Thống Du Lịch Ẩm Thực Quận 4 (Quan4 Culinary Tourism)

> Website dành cho chủ quán và quản trị viên, gồm Cổng Chủ quán tích hợp AI Advisor và Hệ thống Quản trị RBAC. Ứng dụng mobile dành cho du khách phát triển ở repo riêng và dùng API, bản đồ, âm thanh cùng các dịch vụ từ backend trong repo này.

---

## 1. Cấu trúc Thư mục Dự án (Monorepo Skeleton)

```text
culinary_tourism/
├── backend/                        # FastAPI Modular Monolith (Python 3.11+)
│   ├── app/
│   │   ├── core/                   # Config, Database (Motor/Redis), Security (Cookie JWT/Fernet), RBAC
│   │   ├── modules/                # 10 Router Lanes tách biệt theo domain
│   │   │   ├── content/            # [Lane 1] POI CRUD, Delta Sync, 3-Tier Content Fallback
│   │   │   ├── audio/              # [Lane 2] Edge-TTS, Deep-Translator, AudioTaskManager + SSE
│   │   │   ├── admin/              # [Lane 3] Admin Auth, RBAC, Review Registrations/Submissions, Audit
│   │   │   ├── owner/              # [Lane 4] Owner Portal APIs, Menu Items, Submissions, Notifications
│   │   │   ├── ai_advisor/         # [Lane 5] Gemini 2.5 Flash / ProxyPal, Rate Limit (10/ngày)
│   │   │   ├── localization/       # [Lane 6] On-demand TTS, Hotset 1.5km, Warmup
│   │   │   ├── ui_i18n/            # [Lane 7] Dynamic UI Translation Bundles
│   │   │   ├── maps/               # [Lane 8] PMTiles Manifest, Glyphs, Sprites, Path Guard
│   │   │   ├── analytics/          # [Lane 9] Consent-gated Public Analytics
│   │   │   └── runtime_observability/ # [Lane 10] Public Location Ingest & Observability Window
│   │   ├── static/                 # Lưu trữ tĩnh (audio/, images/poi/, maps/)
│   │   └── main.py                 # Entry point FastAPI & Lifespan Manager
│   ├── scripts/
│   │   └── seed_pois.py            # Script khởi tạo 5 quán ăn mẫu Quận 4 & Indexes
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/                       # React 19 + Vite + TailwindCSS
│   ├── src/
│   │   ├── api/                    # Axios Client (httpOnly Cookie credentials)
│   │   ├── store/                  # Zustand Auth Store
│   │   ├── features/               # Hai phân hệ web
│   │   │   ├── owner-portal/       # [Phúc] Cổng Chủ quán B2B & AI Advisor
│   │   │   └── admin-dashboard/    # [Vũ] Bảng điều khiển Quản trị viên
│   │   ├── App.jsx                 # React Router cho website chủ quán và quản trị
│   │   └── main.jsx                # Frontend Entry Point
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
│
├── data/                           # Dữ liệu mẫu & Bản đồ ngoại tuyến (.pmtiles)
│   ├── maps/
│   └── seed/
├── docker-compose.yml              # Khởi chạy nhanh MongoDB & Redis local
└── README.md
```

---

## 2. Phân công Nhánh Git & Phạm vi Công việc (Team of 3 Devs)

Để tránh xung đột mã nguồn (merge conflict), mỗi thành viên làm việc trên nhánh tính năng riêng và phụ trách thư mục độc lập:

| Thành viên | Nhánh Git (`branch`) | Thư mục Frontend chính | Module Backend chính |
| :--- | :--- | :--- | :--- |
| **Bảo** *(Ứng dụng du khách)* | Repo mobile riêng | Ứng dụng mobile | Dùng API của các module content, localization, maps và ui_i18n |
| **Phúc** *(Owner Portal)* | `feature/owner-portal` | `frontend/src/features/owner-portal/` | `owner`, `ai_advisor` |
| **Vũ** *(Admin & Core)* | `feature/admin-core` | `frontend/src/features/admin-dashboard/` | `core`, `admin`, `audio`, `analytics`, `runtime_observability` |

---

## 3. Hướng dẫn Khởi động Nhanh (Getting Started)

### Bước 1: Khởi chạy Cơ sở dữ liệu (MongoDB & Redis)
```bash
docker-compose up -d
```

### Bước 2: Thiết lập Backend (FastAPI)
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

C

# Chạy server phát triển:
uvicorn app.main:app --reload --port 8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Swagger API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Bước 3: Thiết lập Frontend (React + Vite)
```bash
cd frontend
npm install
cp .env.example .env

# Chạy giao diện phát triển:
npm run dev
```
- Ứng dụng chạy tại: `http://localhost:5173`
- Đăng nhập chung: /admin/login
- Đăng ký chủ quán: /register/owner
- Cổng chủ quán: /owner
- Quản trị: /admin
