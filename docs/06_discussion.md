# 6. THẢO LUẬN (DISCUSSION)

## 6.1 Phân Tích Kết Quả

### 6.1.1 Về Phát Hiện Mũ Bảo Hiểm

**Điểm mạnh:**

- Unified model đạt mAP 0.847, vượt trội so với approach 2-model truyền thống
- Thời gian inference giảm 50% do chỉ cần 1 lần forward pass
- Xử lý tốt trường hợp nhiều người trên một xe nhờ associate_riders algorithm

**Điểm yếu và nguyên nhân:**

- Recall của class `without_helmet` (79%) thấp hơn các class khác
  - _Nguyên nhân_: Head region nhỏ, dễ bị che khuất
  - _Giải pháp tiềm năng_: Sử dụng attention mechanism hoặc higher resolution input

**Case study thú vị:**

- Hệ thống phát hiện chính xác trường hợp 3 người trên một xe, trong đó chỉ 1 người không đội mũ
- False positive phổ biến: Người đội nón lá bị nhận nhầm là không đội mũ bảo hiểm

### 6.1.2 Về Phát Hiện Vượt Đèn Đỏ

**Điểm mạnh:**

- HSV dual-range xử lý tốt cả 2 spectrum của màu đỏ
- Direction-aware detection giúp adapting cho các góc camera khác nhau
- Precision cao (93.1%) nhờ kết hợp YOLO detection và ROI fallback

**Điểm yếu:**

- Hiệu suất giảm khi trời mưa (85.1%) do phản xạ ánh sáng
- Đèn LED đôi khi có tần số nhấp nháy gây nhận diện sai

**Quan sát:**

- Thời điểm chuyển đèn (vàng → đỏ) có tỷ lệ false positive cao nhất
- Camera đặt ở góc 30-45° cho kết quả tốt nhất

### 6.1.3 Về Phát Hiện Lấn Làn

**Điểm mạnh:**

- ROI-based approach không cần lane detection model riêng
- Phân biệt solid/dashed line cho phép xử lý đúng quy định

**Điểm yếu:**

- Cần cấu hình thủ công cho mỗi camera
- Không xử lý được làn cong (curved lanes)

## 6.2 Phân Tích Hiệu Suất Hệ Thống

### 6.2.1 Latency Analysis

Tổng độ trễ ~60ms tương đương với ~16 FPS perceived, đủ cho ứng dụng real-time. Bottleneck chính là YOLO inference (25ms).

### 6.2.2 Scalability Analysis

Với 1 GPU RTX 3060, hệ thống có thể xử lý:

- 4 cameras ổn định (38 FPS tổng, latency 35ms)
- 6 cameras với giảm FPS (28 FPS tổng, latency 48ms)

Để scale beyond 6 cameras, cần:

- Multiple GPU nodes
- Kafka partition theo camera
- Load balancing

## 6.3 Hạn Chế (Limitations)

### 6.3.1 Hạn Chế Kỹ Thuật

1. **Góc camera cố định**: ROI cần cấu hình thủ công khi camera thay đổi
2. **Không nhận dạng biển số**: Chưa tích hợp OCR để xác định danh tính phương tiện
3. **Single-node processing**: Chưa hỗ trợ distributed processing across nodes
4. **GPU dependency**: Hiệu suất giảm đáng kể khi chỉ dùng CPU

### 6.3.2 Hạn Chế Dataset

1. **Bias địa lý**: Phần lớn data từ Việt Nam, có thể không generalize tốt cho quốc gia khác
2. **Thiếu extreme conditions**: Ít data về đêm tối, thời tiết xấu
3. **Unbalanced classes**: Số lượng `without_helmet` ít hơn `with_helmet`

### 6.3.3 Hạn Chế Triển Khai

1. **Privacy concerns**: Cần xem xét các quy định về quyền riêng tư khi thu thập hình ảnh
2. **Infrastructure requirements**: Cần đường truyền internet ổn định từ camera
3. **Maintenance**: Cần reconfigure khi camera thay đổi vị trí hoặc góc quay

## 6.4 Ứng Dụng Thực Tế

### 6.4.1 Triển Khai Thí Điểm

Hệ thống đã được triển khai thí điểm tại:

- **3 ngã tư tại TP.HCM** (quận 1, quận 3, quận 7)
- **Thời gian**: 2 tuần
- **Kết quả**: Phát hiện ~150 vi phạm/ngày, trong đó:
  - 65% không đội mũ bảo hiểm
  - 25% vượt đèn đỏ
  - 10% lấn làn

### 6.4.2 Phản Hồi Từ Cơ Quan Chức Năng

- Tính năng real-time dashboard được đánh giá cao
- Yêu cầu bổ sung: Tích hợp nhận diện biển số, export báo cáo

### 6.4.3 Tiềm Năng Mở Rộng

1. **Tích hợp hệ thống xử phạt tự động**: Kết nối với database đăng ký xe qua biển số
2. **Smart city platform**: Cung cấp API cho các ứng dụng thành phố thông minh
3. **Traffic analysis**: Sử dụng data thu thập để phân tích mật độ giao thông
