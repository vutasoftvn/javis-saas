# COSA OS — Local Data & Autonomous Agent Platform

Hệ điều hành doanh nghiệp AI tích hợp kiến trúc Hybrid: **PostgreSQL Local (Data Plane)** + **Supabase Central (Control Plane)**.

---

## ⚡ Cài Đặt Nhanh Local Data Plane (1-Click)

### Trên macOS / Linux / WSL:
```bash
./install.sh
```

### Trên Windows (PowerShell):
```powershell
.\install.ps1
```

> Chi tiết hướng dẫn xem tại: [docs/LOCAL_INSTALLATION_GUIDE.md](file:///Volumes/SSD/javis-saas/docs/LOCAL_INSTALLATION_GUIDE.md)

---

## 🛠️ Quản Trị Hệ Thống Nhanh (COSA CLI)

```bash
./cosa.sh start    # Khởi động dịch vụ
./cosa.sh stop     # Dừng dịch vụ
./cosa.sh status   # Kiểm tra trạng thái
./cosa.sh doctor   # Chẩn đoán sức khỏe hệ thống
./cosa.sh backup   # Sao lưu toàn bộ dữ liệu Local
./cosa.sh restore  # Khôi phục dữ liệu
```

---

## 🖥️ Khởi Động Ứng Dụng Frontend Desktop (Flutter macOS)

```bash
cd frontend
flutter run -d macos
```

Hoặc build bản đóng gói:
```bash
cd frontend
flutter build macos --debug
open build/macos/Build/Products/Debug/frontend.app
```
