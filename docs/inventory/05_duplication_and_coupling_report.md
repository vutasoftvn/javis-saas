# BÁO CÁO MÃ NGUỒN TRÙNG LẶP, DỮ LIỆU RÁC & MA TRẬN PHỤ THUỘC
## (PHASE 0 - INVENTORY REPORT 05)

> **Dự án:** COSA (Founder / Company Operating System)  
> **Ngày thực hiện:** 2026-08-20  
> **Trạng thái:** Hoàn tất khảo sát

---

## 1. DANH MỤC CÁC FILE RÁC & SCRIPT TẠM CẦN LOẠI BỎ (DEAD FILES / OBSOLETE DATA)

Đã rà soát toàn bộ thư mục gốc dự án và phát hiện các file scratch/tạm thời không còn sử dụng:

| Tên File / Thư mục | Vị trí hiện tại | Mục đích ban đầu | Đánh giá & Hành động |
| :--- | :--- | :--- | :--- |
| `gen_modules.py` | Root `/` | Script sinh scaffold module GetX mẫu | ✅ Đã xong nhiệm vụ $\rightarrow$ **Cần xóa** |
| `fix_imports.py` | Root `/` | Script thay thế import đường dẫn cũ | ✅ Đã chạy xong $\rightarrow$ **Cần xóa** |
| `split_models.py` | Root `/` | Script tách models tạm thời | ✅ Đã xong $\rightarrow$ **Cần xóa** |
| `split_models2.py` | Root `/` | Script tách models lần 2 | ✅ Đã xong $\rightarrow$ **Cần xóa** |
| `move_script.sh` | Root `/` | Script di chuyển file tạm thời | ✅ Đã chạy xong $\rightarrow$ **Cần xóa** |
| `home.png`, `image.png` | Root `/` | Ảnh chụp màn hình tạm thời | ✅ Di chuyển vào `docs/assets/` hoặc xóa nếu thừa |
| `backups/` | Root `/` | File backup nén cũ | ✅ Đã có Git history $\rightarrow$ **Cần dọn dẹp** |

---

## 2. MA TRẬN PHỤ THUỘC CHÉO CẦN CẮT ĐỨT TRONG PHASE 1

```text
HIỆN TRẠNG (COUPLING NGUY HIỂM):
[core/ (Business)] ──(import trực tiếp)──► [workforce/ (AI Prompts & Agents)]  ❌ VI PHẠM CLAUDE §5

MỤC TIÊU PHASE 1 (CLEAN ARCHITECTURE):
[core/ (Pure Business)]  ◄─── (KHÔNG PHỤ THUỘC) ───► [agent/ (Harness)]
                                                               │
                                                               ▼ (Gọi qua Tools)
                                                     [core/ Domain APIs]
```

1. **Cắt đứt vi phạm Business Core phụ thuộc AI:**
   - Trong `backend/app/business/marketing/` và `legal/`, cần loại bỏ các lệnh import runner AI trực tiếp.
   - Khi Agent cần xử lý dữ liệu Marketing hoặc Pháp lý, Agent sẽ gọi thông qua **Tools** (`tools/crm/`, `tools/knowledge/`) thay vì Business Core gọi Agent.

2. **Khắc phục trùng lặp DTO & Serializer (DRY):**
   - Hợp nhất các Pydantic DTO bị định nghĩa lặp lại giữa các sub-routers vào các module schema chuẩn trong `core/`.
