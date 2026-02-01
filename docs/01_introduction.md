# 1. GIỚI THIỆU (INTRODUCTION)

## 1.1 Bối Cảnh và Tầm Quan Trọng

Theo thống kê của Ủy ban An toàn Giao thông Quốc gia Việt Nam, mỗi năm có khoảng **8.000-9.000 người tử vong** do tai nạn giao thông, trong đó hơn **60% liên quan đến xe máy**. Các nguyên nhân chính bao gồm: không đội mũ bảo hiểm (chiếm 35% số ca tử vong), vượt đèn đỏ (18%), và lấn làn đường (12%). Chi phí kinh tế do tai nạn giao thông ước tính lên đến **2.5-3% GDP** hàng năm [1].

Hiện nay, việc giám sát vi phạm giao thông tại Việt Nam chủ yếu dựa vào lực lượng cảnh sát giao thông tuần tra thủ công. Phương pháp này có nhiều hạn chế:

- **Độ phủ thấp**: Không thể giám sát 24/7 tại tất cả các điểm nóng
- **Chi phí nhân lực cao**: Cần hàng nghìn cán bộ cho mỗi thành phố lớn
- **Độ chính xác dao động**: Phụ thuộc vào yếu tố con người
- **Khó xử lý dữ liệu**: Không có hệ thống tổng hợp và phân tích

## 1.2 Khoảng Trống Nghiên Cứu (Research Gap)

Các hệ thống phát hiện vi phạm giao thông tự động hiện có trên thế giới chủ yếu tập trung vào một loại vi phạm đơn lẻ (chỉ phát hiện vượt đèn đỏ hoặc chỉ phát hiện không đội mũ). Hơn nữa, phần lớn các nghiên cứu sử dụng xử lý offline (batch processing), không đáp ứng được yêu cầu **phát hiện thời gian thực** để cảnh báo và xử lý kịp thời.

Các hạn chế cụ thể của các nghiên cứu trước:

1. **Xử lý đơn luồng**: Chỉ xử lý được 1 camera tại một thời điểm
2. **Độ trễ cao**: Thường từ 2-5 giây, không phù hợp cho ứng dụng thực tế
3. **Không có khả năng mở rộng**: Khó triển khai cho hệ thống camera lớn
4. **Thiếu tích hợp**: Không kết nối với hệ thống cơ sở dữ liệu và dashboard quản lý

## 1.3 Mục Tiêu và Câu Hỏi Nghiên Cứu

### Mục tiêu nghiên cứu:

Xây dựng hệ thống phát hiện vi phạm giao thông thời gian thực, có khả năng xử lý đồng thời nhiều luồng camera với độ trễ thấp (<500ms), phát hiện đa loại vi phạm và tích hợp hoàn chỉnh từ thu thập dữ liệu đến hiển thị kết quả.

### Câu hỏi nghiên cứu:

1. Làm thế nào để kết hợp nhiều mô hình phát hiện đối tượng để nhận diện đồng thời nhiều loại vi phạm giao thông?
2. Kiến trúc hệ thống nào phù hợp để xử lý stream video thời gian thực từ nhiều camera với độ trễ thấp?
3. Các thuật toán và kỹ thuật nào giúp giảm thiểu false positive trong phát hiện vi phạm?

## 1.4 Đóng Góp Chính

Nghiên cứu này đóng góp các điểm mới sau:

1. **Hệ thống phát hiện đa vi phạm (Multi-violation Detection)**:
   - Phát hiện đồng thời 3 loại vi phạm: không đội mũ bảo hiểm, vượt đèn đỏ, lấn làn
   - Sử dụng unified model 8 classes cho phát hiện mũ bảo hiểm, kết hợp YOLOv8 cho các vi phạm khác

2. **Kiến trúc xử lý stream thời gian thực**:
   - Sử dụng Apache Kafka làm message broker cho stream processing
   - Đạt throughput 15 FPS với độ trễ end-to-end <500ms
   - Hỗ trợ xử lý đồng thời nhiều camera

3. **Thuật toán giảm false positive**:
   - Violation Deduplicator: Tránh đếm trùng khi track ID thay đổi
   - Multi-strategy verification: Kết hợp nhiều nguồn thông tin (person, vehicle, helmet)
   - ROI-based filtering: Chỉ xử lý trong vùng quan tâm được cấu hình

4. **Hệ thống tích hợp hoàn chỉnh**:
   - Dashboard real-time với WebSocket
   - Cơ sở dữ liệu PostgreSQL cho lưu trữ và truy vấn
   - Cấu hình ROI linh hoạt cho từng camera

## 1.5 Cấu Trúc Bài Báo Cáo

Bài báo cáo được tổ chức như sau:

- **Phần 2**: Tổng quan các công trình liên quan
- **Phần 3**: Phương pháp đề xuất và kiến trúc hệ thống
- **Phần 4**: Chi tiết thuật toán phát hiện vi phạm
- **Phần 5**: Thực nghiệm và kết quả
- **Phần 6**: Thảo luận
- **Phần 7**: Kết luận và hướng phát triển
