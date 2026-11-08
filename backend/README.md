# Quan4 Culinary Tourism — Backend

Backend API cho hệ thống **Du lịch Ẩm thực Quận 4**, xây dựng bằng FastAPI và MongoDB, hỗ trợ quản lý địa điểm ẩm thực, xác thực người dùng, phân quyền, kiểm duyệt nội dung và tạo thuyết minh đa ngôn ngữ.

## 1. Tech Stack

| Công nghệ | Mục đích |
|---|---|
| Python 3.11 + FastAPI | REST API bất đồng bộ |
| MongoDB + Motor | Database, GeoJSON, Transactions |
| Redis | Cache và Rate Limiting |
| JWT + RBAC | Xác thực và phân quyền |
| deep-translator | Dịch nội dung đa ngôn ngữ |
| Edge-TTS | Tổng hợp giọng nói |
| Docker | Chạy MongoDB và Redis |
| Pytest | Automated Testing |

## 2. Project Structure

```text
backend/
├── app/
│   ├── main.py             # FastAPI entry point
│   ├── core/               # Config, Database, Auth, RBAC
│   ├── modules/            # API modules
│   └── static/             # Audio, Images, Maps
├── scripts/                # Database seeding
├── tests/                  # Automated tests
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── README.md
```

Backend sử dụng kiến trúc **Modular Monolith** với 10 router modules.

## 3. Getting Started

**Yêu cầu:** Python 3.11, Docker Desktop và Git.

### Step 1 — Start Docker Services

Tại thư mục gốc `culinary_tourism/`:

```powershell
docker compose up -d
docker compose ps
```

Docker khởi động MongoDB và Redis. MongoDB sử dụng Replica Set `rs0` để hỗ trợ Transactions.

Kiểm tra khởi tạo MongoDB:

```powershell
docker compose logs --tail=50 mongo-init
```

### Step 2 — Install Dependencies

Di chuyển vào `backend/`:

```powershell
cd backend

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements-dev.txt
```

### Step 3 — Environment Configuration

Tạo `.env` từ `.env.example` nếu chưa có:

```powershell
Copy-Item .env.example .env
```

Kiểm tra các biến cấu hình quan trọng:

```dotenv
APP_ENV=development
MONGO_URI=mongodb://localhost:27017/?directConnection=true
DB_NAME=quan4_culinary
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:5173
```

Các biến JWT, Fernet và Super Admin phải được cấu hình riêng theo `.env.example`.

**Không commit `.env`, mật khẩu hoặc API keys lên Git.** Không thay `FERNET_KEY` khi còn dữ liệu CCCD đã mã hóa cần sử dụng.

### Step 4 — Run Backend

Trong thư mục `backend/`:

```powershell
uvicorn app.main:app --reload --port 8000
```

Kiểm tra:

- API Health: http://localhost:8000/health
- Database Readiness: http://localhost:8000/health/ready
- Swagger UI: http://localhost:8000/docs

Swagger UI cung cấp tài liệu API, request schema và response schema cho các thành viên tích hợp.
### Step 5 — Run Frontend

Mở terminal mới và di chuyển vào thư mục `frontend/` từ thư mục gốc dự án:

```powershell
cd frontend
```

Cài đặt dependencies (chỉ cần thực hiện lần đầu):

```powershell
npm install
```

Khởi động frontend:

```powershell
npm run dev
```

Truy cập ứng dụng:

- **Admin Dashboard:** http://localhost:5173/admin
- **Admin Login:** http://localhost:5173/admin/login

**Lưu ý:**
- Cần cài đặt Node.js và npm.
- Backend phải đang chạy tại `http://localhost:8000`.
- Giữ hai terminal riêng biệt cho Backend và Frontend.

## 4. Seed Data

Tại thư mục `backend/`:

```powershell
python -m scripts.seed_pois --no-demo-users
```

Dữ liệu mẫu gồm 5 quán ăn Quận 4:

1. Nem Nướng Nia
2. Quán Phở Mùi 241
3. Phá Lấu Bò Cô Thảo
4. Quán Ốc Thảo
5. Dừa Tắc Cô Út

Các POI ban đầu chưa được công khai và cần hoàn thành Audio EN trước khi kích hoạt.

Tạo tài khoản demo bổ sung (chỉ dùng môi trường phát triển):

```powershell
python -m scripts.seed_pois
```

Tạo hồ sơ đăng ký chủ quán mẫu:

```powershell
python -m scripts.seed_registrations
```

## 5. API Modules

Base URL:

```text
http://localhost:8000/api/v1
```

Các endpoint được bảo vệ bằng JWT Authentication và RBAC Permissions.

## 6. Testing

Chạy toàn bộ tests trong `backend/`:

```powershell
python -m pytest -q
```

Kiểm thử MongoDB Transactions thực tế (yêu cầu Replica Set):

```powershell
$env:RUN_MONGO_TX_INTEGRATION = "1"

python -m pytest -q tests/test_mongo_transaction_integrtion.py

Remove-Item Env:RUN_MONGO_TX_INTEGRATION
```

Chỉ merge code sau khi đã kiểm tra API liên quan và xử lý các test thất bại.

## 7. Database Reset

**Cảnh báo: Sao lưu dữ liệu trước khi reset. Chỉ thực hiện trên database local, không chạy trên database dùng chung.**

Khôi phục 5 POI mẫu:

```powershell
python -m scripts.seed_pois --reset --no-demo-users
```

Lệnh này xóa dữ liệu trong `poi` và `poi_localizations` trước khi seed lại. Các Audio Tasks, Submissions và hồ sơ cũ có thể vẫn còn liên kết đến POI đã xóa.

Để reset toàn bộ database local bằng Docker, dừng backend và chạy tại thư mục gốc:

```powershell
docker compose down -v
docker compose up -d
```

**Lệnh `down -v` xóa Docker volumes của project**, bao gồm dữ liệu MongoDB và Redis trong các volume đó. Các tệp MP3 lưu ngoài volumes không tự bị xóa.

Sau khi MongoDB sẵn sàng, chạy seed lại theo mục 4.

## 8. Development Notes

- **Authentication:** Access Token 30 phút, Refresh Token 7 ngày.
- **RBAC:** 32 permissions thuộc 9 domains.
- **Audio:** Hỗ trợ tiếng Việt, Anh, Trung, Nhật và Hàn; có cache MP3.
- **Translation:** Google Translate có thể giới hạn request (`429`); hệ thống hỗ trợ retry và bản dịch thủ công.
- **Activation Gate:** POI cần bản dịch EN và Audio EN hợp lệ để công khai.
- **Timezone:** Backend lưu UTC, frontend hiển thị `Asia/Ho_Chi_Minh`.
- **Audit Logs:** Ghi nhận các thao tác quản trị nhạy cảm.
- **Static Security:** Kiểm tra đường dẫn khi truy cập tài nguyên tĩnh.

---

**Quan4 Culinary Tourism — Backend Development Guide**  
*Python 3.11 · FastAPI · MongoDB · Redis*