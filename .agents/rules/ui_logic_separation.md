# Quy Định Phân Tách Giao Diện (UI) & Nghiệp Vụ (Logic)

## 1. Nguyên Tắc Cốt Lõi (Core Principles)
1. **Single Responsibility Principle (SRP)**:
   - Mỗi file widget hoặc component chỉ phụ trách một vùng giao diện độc lập (VD: Card, Grid, FilterBar, Dialog, Modal, Banner).
   - Tuyệt đối không để một file View chính phình to (giữ file View chính < 250 dòng, đóng vai trò Scaffold/Layout tổng thể).
2. **UI & Business Logic Separation**:
   - **View / Widget (Dumb / Presentational)**: Chỉ chịu trách nhiệm về giao diện hiển thị, animation, layout, binding state và bắt sự kiện người dùng (onTap, onChanged).
   - **Controller (GetxController / State Manager)**: Nắm giữ toàn bộ trạng thái phản ứng (`RxList`, `RxString`, `RxBool`), gọi Service, xử lý validation, dữ liệu và điều hướng.
   - Không thực hiện tính toán phức tạp hay gọi trực tiếp `http`/`ApiClient` bên trong Widget. Mọi tương tác phải thông qua `controller.method()`.
3. **Cấu trúc Module Chuẩn (Standard Module Layout)**:
   ```
   lib/modules/<feature_name>/
   ├── bindings/
   │   └── <feature>_binding.dart
   ├── controllers/
   │   └── <feature>_controller.dart
   ├── views/
   │   └── <feature>_view.dart          <-- Chỉ chứa Scaffold, AppBar và lắp ghép các Widget
   └── widgets/
       ├── <feature>_<component_1>.dart <-- Widget độc lập
       ├── <feature>_<component_2>.dart
       └── dialogs/                      <-- (Nếu có các popup/dialog lớn)
           └── <feature>_<dialog_name>.dart
   ```

## 2. Quy Tắc Viết Widget (Widget Rules)
* **Kích thước file**: Mỗi component/widget trong thư mục `widgets/` nên nằm trong khoảng 50 - 300 dòng code.
* **Truy xuất State**: Widget nên nhận trực tiếp `Controller` hoặc gọi `Get.find<FeatureController>()`, sử dụng `Obx(() => ...)` bao quanh phần tử reactive thay vì bao quanh toàn bộ widget lớn.
* **Tái sử dụng Dialog & Modal**: Các modal phức tạp (Form nhập liệu, Studio, Hub) phải được tổ chức thành static helper methods hoặc StatefulWidget/StatelessWidget riêng, không nhồi nhét vào cuối file View chính.
