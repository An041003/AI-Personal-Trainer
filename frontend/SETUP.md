# Hướng dẫn Setup Frontend

## Lỗi Proxy Connection

Nếu bạn gặp lỗi `ECONNREFUSED` khi chạy frontend, có nghĩa là backend Django chưa được khởi động.

## Cách khắc phục

### Bước 1: Khởi động Backend Django

Mở terminal mới và chạy:

```bash
# Từ thư mục gốc của dự án
python manage.py runserver
```

Backend sẽ chạy tại `http://127.0.0.1:8000` hoặc `http://localhost:8000`

### Bước 2: Khởi động Frontend

Trong terminal khác:

```bash
cd frontend
npm install  # Nếu chưa cài đặt
npm run dev
```

Frontend sẽ chạy tại `http://localhost:3000`

## Kiểm tra

1. Backend đang chạy: Truy cập `http://localhost:8000/api/docs/` để xem Swagger UI
2. Frontend đang chạy: Truy cập `http://localhost:3000`

## Lưu ý

- Backend phải chạy trước khi frontend có thể gọi API
- Đảm bảo cả hai đang chạy trên các port khác nhau (8000 cho backend, 3000 cho frontend)
- Nếu vẫn gặp lỗi, kiểm tra firewall hoặc các ứng dụng khác đang sử dụng port 8000


