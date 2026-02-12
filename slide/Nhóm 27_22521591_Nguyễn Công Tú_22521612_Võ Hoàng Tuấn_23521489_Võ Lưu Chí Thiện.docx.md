**ĐẠI HỌC QUỐC GIA TP. HỒ CHÍ MINH**

**TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN**

**KHOA CÔNG NGHỆ PHẦN MỀM**

**![][image1]**

**BÁO CÁO ĐỒ ÁN MÔN HỌC**

**ĐỀ TÀI: PHÁT HIỆN VI PHẠM GIAO THÔNG**

**Môn học: Dữ liệu lớn (SE363)**  
**Giảng viên hướng dẫn:** Đỗ Trọng Hợp, Nguyễn Ngọc Quí  
**Nhóm: 27**  
**Danh sách thành viên**

* Nguyễn Công Tú (22521591)  

  * Võ Hoàng Tuấn (22521612)  

  * Võ Lưu Chí Thiện (23521489)

***Thành phố Hồ Chí Minh, ngày 20  tháng 12 năm 2025***

**Mục lục**

**[1\. Introduction (Giới thiệu)	3](#1.-introduction-\(giới-thiệu\))**

[1.1. Bối cảnh và tầm quan trọng của vấn đề	3](#1.1.-bối-cảnh-và-tầm-quan-trọng-của-vấn-đề)

[1.2. Khoảng trống nghiên cứu (Research Gap)	3](#1.2.-khoảng-trống-nghiên-cứu-\(research-gap\))

[1.3. Mục tiêu nghiên cứu và câu hỏi nghiên cứu	4](#1.3.-mục-tiêu-nghiên-cứu-và-câu-hỏi-nghiên-cứu)

[1.4. Đóng góp chính của đề tài	4](#1.4.-đóng-góp-chính-của-đề-tài)

[**2\. Related work (Công trình liên quan)	5**](#2.-related-work-\(công-trình-liên-quan\))

[2.1. Phát hiện vi phạm mũ bảo hiểm	5](#2.1.-phát-hiện-vi-phạm-mũ-bảo-hiểm)

[2.2. Nhận dạng đèn giao thông và phát hiện vi phạm vượt đèn đỏ	6](#2.2.-nhận-dạng-đèn-giao-thông-và-phát-hiện-vi-phạm-vượt-đèn-đỏ)

[2.3. Object Tracking và De-duplication	7](#2.3.-object-tracking-và-de-duplication)

[2.4. Tổng hợp khoảng trống nghiên cứu	7](#2.4.-tổng-hợp-khoảng-trống-nghiên-cứu)

[**3\. Methodology (Phương pháp đề xuất)	8**](#3.-methodology-\(phương-pháp-đề-xuất\))

[3.1. Tổng quan kiến trúc hệ thống	8](#3.1.-tổng-quan-kiến-trúc-hệ-thống)

[3.2. Module phát hiện vi phạm mũ bảo hiểm	8](#3.2.-module-phát-hiện-vi-phạm-mũ-bảo-hiểm)

[3.3. Module phát hiện vi phạm vượt đèn đỏ	12](#3.3.-module-phát-hiện-vi-phạm-vượt-đèn-đỏ)

[3.4. Kiến trúc Streaming Pipeline	14](#3.4.-kiến-trúc-streaming-pipeline)

[**4\. Experiments and Results (Thực nghiệm và kết quả)	15**](#4.-experiments-and-results-\(thực-nghiệm-và-kết-quả\))

[4.1. Dataset và Experimental Setup	15](#4.1.-dataset-và-experimental-setup)

[4.2. Evaluation Metrics	16](#4.2.-evaluation-metrics)

[4.3. Results	17](#4.3.-results)

[4.4. So sánh với các công trình liên quan	18](#4.4.-so-sánh-với-các-công-trình-liên-quan)

[**5\. Discussion (Thảo luận)	18**](#5.-discussion-\(thảo-luận\))

[5.1. Phân tích thiết kế hệ thống	18](#5.1.-phân-tích-thiết-kế-hệ-thống)

[5.2. Case Studies	19](#5.2.-case-studies)

[5.3. Limitations (Hạn chế)	19](#5.3.-limitations-\(hạn-chế\))

[5.4. Các yếu tố ảnh hưởng đến kết quả	20](#5.4.-các-yếu-tố-ảnh-hưởng-đến-kết-quả)

[**6\. Conclusion and Future Work (Kết luận và hướng phát triển)	20**](#6.-conclusion-and-future-work-\(kết-luận-và-hướng-phát-triển\))

[6.1. Tóm tắt	20](#6.1.-tóm-tắt)

[6.2. Đóng góp chính	20](#6.2.-đóng-góp-chính)

[6.3. Hướng phát triển	21](#6.3.-hướng-phát-triển)

[**References (Tài liệu tham khảo)	22**](#references-\(tài-liệu-tham-khảo\))

## **1\. Introduction (Giới thiệu)** {#1.-introduction-(giới-thiệu)}

### **1.1. Bối cảnh và tầm quan trọng của vấn đề** {#1.1.-bối-cảnh-và-tầm-quan-trọng-của-vấn-đề}

An toàn giao thông đường bộ là một trong những thách thức lớn nhất đối với các quốc gia đang phát triển, đặc biệt tại khu vực Đông Nam Á nơi xe gắn máy chiếm tỷ lệ chủ đạo trong phương tiện giao thông cá nhân. Theo báo cáo của Tổ chức Y tế Thế giới (WHO) năm 2023, Việt Nam ghi nhận hơn 11.000 ca tử vong do tai nạn giao thông mỗi năm, trong đó khoảng 60% liên quan đến xe gắn máy \[1\]. Đáng chú ý, nghiên cứu của Ủy ban An toàn Giao thông Quốc gia chỉ ra rằng 70% số ca tử vong trong tai nạn xe máy có nguyên nhân từ chấn thương sọ não do không đội mũ bảo hiểm hoặc đội mũ không đạt chuẩn \[2\].

Song song với vấn đề mũ bảo hiểm, vi phạm vượt đèn đỏ tại các giao lộ cũng là nguyên nhân hàng đầu gây ra các vụ tai nạn nghiêm trọng. Thống kê từ Công an TP. Hồ Chí Minh cho thấy 18% số vụ tai nạn nghiêm trọng tại các nút giao thông có tín hiệu đèn xuất phát từ hành vi vượt đèn đỏ \[3\]. Điều này đặt ra yêu cầu cấp thiết về việc triển khai các hệ thống giám sát tự động có khả năng phát hiện và ghi nhận vi phạm một cách liên tục, chính xác và không phụ thuộc vào nguồn nhân lực hạn chế.

Sự phát triển vượt bậc của deep learning trong thập kỷ qua, đặc biệt là các kiến trúc object detection như YOLO (You Only Look Once), đã mở ra cơ hội ứng dụng trí tuệ nhân tạo vào bài toán giám sát giao thông. Các hệ thống dựa trên YOLO có khả năng đạt được sự cân bằng giữa độ chính xác và tốc độ xử lý, phù hợp cho các ứng dụng thời gian thực \[4\].

### **1.2. Khoảng trống nghiên cứu (Research Gap)** {#1.2.-khoảng-trống-nghiên-cứu-(research-gap)}

Phân tích các công trình nghiên cứu liên quan, chúng tôi nhận diện được bốn khoảng trống chính mà đề tài này hướng đến giải quyết:

**Thứ nhất**, đa số các nghiên cứu hiện có tập trung vào một loại vi phạm đơn lẻ. Các công trình về phát hiện mũ bảo hiểm \[5, 6\] và phát hiện vượt đèn đỏ \[7, 8\] được phát triển độc lập, thiếu một framework thống nhất có khả năng xử lý đa loại vi phạm trong cùng một pipeline. Điều này dẫn đến việc triển khai thực tế đòi hỏi vận hành nhiều hệ thống song song, tăng chi phí và độ phức tạp.

**Thứ hai**, các hệ thống phát hiện mũ bảo hiểm hiện tại phụ thuộc hoàn toàn vào khả năng của model deep learning trong việc detect class "no helmet" hoặc "without helmet". Khi model không phát hiện được đối tượng này (do occlusion, lighting hoặc pose variation), vi phạm bị bỏ sót mà không có cơ chế bù đắp \[9\]. Thiếu chiến lược dự phòng (fallback) làm giảm recall của hệ thống trong điều kiện thực tế.

**Thứ ba**, trong bài toán nhận dạng trạng thái đèn giao thông, các phương pháp dựa trên CNN classification \[10\] đòi hỏi lượng dữ liệu huấn luyện lớn và chi phí tính toán cao, trong khi các phương pháp đơn giản như HSV thresholding \[11\] hoạt động tốt trong điều kiện chuẩn nhưng thiếu tính robust. Hiện chưa có nghiên cứu nào đề xuất cách kết hợp hiệu quả hai hướng tiếp cận này.

**Thứ tư**, phần lớn các nghiên cứu dừng lại ở mức prototype hoặc proof-of-concept, thiếu kiến trúc end-to-end sẵn sàng cho việc triển khai production với khả năng xử lý streaming, lưu trữ dữ liệu và giao diện giám sát thời gian thực \[12\].

### **1.3. Mục tiêu nghiên cứu và câu hỏi nghiên cứu** {#1.3.-mục-tiêu-nghiên-cứu-và-câu-hỏi-nghiên-cứu}

**Mục tiêu tổng quát:** Xây dựng hệ thống phát hiện vi phạm giao thông tự động, đa loại, hoạt động theo thời gian thực.

**Mục tiêu cụ thể:**

* Phát triển module phát hiện vi phạm không đội mũ bảo hiểm với chiến lược detection kép

* Phát triển module phát hiện vi phạm vượt đèn đỏ sử dụng phương pháp hybrid

* Xây dựng kiến trúc streaming pipeline xử lý video theo thời gian thực

* Triển khai giao diện dashboard giám sát với khả năng cảnh báo tức thì

Để đạt được các mục tiêu trên, nghiên cứu này đặt ra ba câu hỏi nghiên cứu (Discuss Questions):

**DQ1:** Làm thế nào để thiết kế chiến lược phát hiện vi phạm mũ bảo hiểm có thể xử lý được cả trường hợp model phát hiện trực tiếp và trường hợp model không phát hiện được?

**DQ2:** Làm thế nào để kết hợp phương pháp xử lý ảnh truyền thống (HSV) và deep learning (YOLO) để nhận dạng trạng thái đèn giao thông một cách hiệu quả?

**DQ3:** Làm thế nào để xây dựng kiến trúc streaming pipeline đáp ứng yêu cầu xử lý video thời gian thực?

### **1.4. Đóng góp chính của đề tài** {#1.4.-đóng-góp-chính-của-đề-tài}

Nghiên cứu này đóng góp vào lĩnh vực phát hiện vi phạm giao thông tự động thông qua bốn điểm chính:

1. **Unified Multi-Violation Framework:** Đề xuất kiến trúc hệ thống tích hợp cho phép xử lý đồng thời nhiều loại vi phạm (mũ bảo hiểm, đèn đỏ) trong một pipeline thống nhất, sử dụng chung unified model và infrastructure.

2. **Dual-Strategy Helmet Detection:** Đề xuất chiến lược phát hiện kép kết hợp direct detection (ưu tiên) và inference-based fallback, cải thiện recall mà không làm giảm đáng kể precision.

3. **HSV-YOLO Hybrid Light Detection:** Đề xuất phương pháp kết hợp xử lý ảnh truyền thống (HSV thresholding) với deep learning (YOLO object detection) cho nhận dạng trạng thái đèn giao thông, đạt được sự cân bằng giữa hiệu quả và chi phí tính toán.

4. **Production-Ready Architecture:** Xây dựng kiến trúc end-to-end hoàn chỉnh bao gồm video streaming (Kafka), xử lý phân tán (Spark), orchestration (Airflow), persistence (PostgreSQL), và real-time dashboard (Next.js \+ FastAPI).

## **2\. Related work (Công trình liên quan)** {#2.-related-work-(công-trình-liên-quan)}

*Phần này trình bày tổng quan các công trình nghiên cứu liên quan, được tổ chức theo ba hướng: phát hiện mũ bảo hiểm (2.1), nhận dạng đèn giao thông và phát hiện vi phạm vượt đèn đỏ (2.2), và theo dõi đối tượng (2.3). Trong mỗi hướng, chúng tôi phân tích các phương pháp đã có, so sánh điểm mạnh và hạn chế, từ đó xác định khoảng trống nghiên cứu mà đề tài hướng đến giải quyết.*

### **2.1. Phát hiện vi phạm mũ bảo hiểm** {#2.1.-phát-hiện-vi-phạm-mũ-bảo-hiểm}

Bài toán phát hiện mũ bảo hiểm (helmet detection) đã được nghiên cứu rộng rãi với hai hướng tiếp cận chính. **Phương pháp hai giai đoạn** (two-stage) sử dụng Faster R-CNN \[5\] đạt precision cao (89%) nhưng tốc độ chậm (12 FPS). **Phương pháp một giai đoạn** (one-stage) dựa trên kiến trúc YOLO cho hiệu suất cân bằng hơn giữa accuracy và speed.

Singh và cộng sự \[6\] là một trong những nghiên cứu đầu tiên áp dụng YOLOv3 cho helmet detection, đạt 87% accuracy. Jia và cộng sự \[7\] cải tiến với YOLOv5s, đạt mAP@50 là 91.3% và 45 FPS. Gần đây, các nghiên cứu so sánh cho thấy YOLOv8 đạt kết quả tốt nhất:

| Model | mAP@50 | FPS |
| :---- | :---- | :---- |
| YOLOv3 | 87.2% | 35 |
| YOLOv5s | 91.3% | 140 |
| YOLOv8s | 93.8% | 156 |

Đây là lý do chúng tôi lựa chọn YOLOv8s làm backbone detection cho đề tài. 

**Khoảng trống nghiên cứu**: Tất cả các phương pháp đều phụ thuộc vào **Single Detection** \- khi mô hình không phát hiện được lớp "without\_helmet", vi phạm bị bỏ sót mà không có cơ chế phục hồi. Đề tài này giải quyết vấn đề này thông qua **Dual-Strategy Detection** với cơ chế fallback.

### **2.2. Nhận dạng đèn giao thông và phát hiện vi phạm vượt đèn đỏ** {#2.2.-nhận-dạng-đèn-giao-thông-và-phát-hiện-vi-phạm-vượt-đèn-đỏ}

#### **2.2.1. Nhận dạng trạng thái đèn**

Bài toán nhận dạng đèn giao thông (Traffic Light Recognition \- TLR) có hai hướng tiếp cận: **Phương pháp HSV thresholding** \[8\] có tốc độ nhanh (\~5ms) nhưng nhạy cảm với điều kiện ánh sáng (accuracy 75-92% tùy điều kiện). **Phương pháp Deep Learning** như YOLOv8 \[9\] đạt accuracy cao hơn (98.3%) và robust hơn, nhưng cần GPU và training data.

| Phương pháp | Accuracy | Speed | Robustness |
| :---- | :---- | :---- | :---- |
| HSV threshold | 75-92% | \~5ms | Thấp |
| YOLOv8 | 98.3% | \~8ms | Cao |

#### **2.2.2. Phát hiện vi phạm vượt đèn đỏ**

Bài toán phát hiện vi phạm vượt đèn đỏ (Red Light Running Detection \- RLRD) đòi hỏi tích hợp ba thành phần: (1) nhận dạng trạng thái đèn, (2) xác định vị trí vạch dừng, và (3) theo dõi phương tiện.

Chen và cộng sự \[10\] đề xuất framework sử dụng YOLOv4 \+ Kalman Filter, đạt 94% detection rate trên dataset giao thông Trung Quốc. Tuy nhiên, phương pháp yêu cầu annotate stop line thủ công cho mỗi camera và không có cơ chế xử lý khi đèn không rõ ràng.

| Paper | Light Detection | Stop Line | Detection Rate |
| :---- | :---- | :---- | :---- |
| Chen \[10\] | YOLOv4 | Manual | 94% |
| Nguyen \[11\] | YOLOv5s | Virtual line | 92.3% |
| **Đề tài** | **HSV \+ YOLO** | **Manual ROI** | **90.1%** |

**Khoảng trống**: 

1. Chưa có paper kết hợp HSV và DL theo dạng **primary-fallback** như đề tài

2. Phần lớn nghiên cứu dừng ở detection, chưa có **end-to-end pipeline** hoàn chỉnh

### **2.3. Object Tracking và De-duplication** {#2.3.-object-tracking-và-de-duplication}

Object tracking giúp tránh đếm trùng violation. Các phương pháp phổ biến:

| Tracker | MOTA | FPS | Complexity |
| :---- | :---- | :---- | :---- |
| CentroidTracker | \~55% | 120+ | Low |
| DeepSORT \[12\] | \~65% | 40 | Medium |
| ByteTrack \[13\] | \~75% | 65 | Medium |

Đề tài sử dụng CentroidTracker vì ưu tiên speed, kết hợp với **ViolationDeduplicator** để giảm thiểu duplicate violations thông qua position matching và time window.

### **2.4. Tổng hợp khoảng trống nghiên cứu** {#2.4.-tổng-hợp-khoảng-trống-nghiên-cứu}

| Khoảng trống | Ảnh hưởng | Giải pháp của đề tài |
| :---- | :---- | :---- |
| Single detection strategy | Bỏ sót vi phạm khi model miss | Dual-Strategy Detection với fallback |
| HSV hoặc DL riêng lẻ | Trade-off speed/robustness | Hybrid: HSV primary \+ YOLO fallback |
| Thiếu multi-violation | Cần nhiều hệ thống | Unified pipeline cho helmet \+ red light |
| Thiếu production pipeline | Không scalable | Kafka \+ Spark \+ FastAPI \+ Next.js |

**Tóm lại**, các công trình hiện tại còn bốn khoảng trống chính mà đề tài hướng đến giải quyết: (1) thiếu cơ chế dự phòng khi detection thất bại, (2) chưa có phương pháp kết hợp hiệu quả giữa xử lý ảnh truyền thống và deep learning, (3) chưa tích hợp đa loại vi phạm trong một hệ thống, và (4) thiếu kiến trúc production-ready cho triển khai thực tế. Phần tiếp theo trình bày phương pháp đề xuất để giải quyết các khoảng trống này.

## **3\. Methodology (Phương pháp đề xuất)** {#3.-methodology-(phương-pháp-đề-xuất)}

*Phần này trình bày chi tiết phương pháp đề xuất, bao gồm: (3.1) tổng quan kiến trúc hệ thống, (3.2) module phát hiện vi phạm mũ bảo hiểm, (3.3) module phát hiện vi phạm vượt đèn đỏ, và (3.4) kiến trúc streaming pipeline.*

### **3.1. Tổng quan kiến trúc hệ thống** {#3.1.-tổng-quan-kiến-trúc-hệ-thống}

Hệ thống được thiết kế theo kiến trúc microservices với các thành phần chính được minh họa trong sơ đồ khối sau:

**![][image2]**

Giả định thiết kế:

* Camera có vị trí và góc nhìn cố định

* Video frame rate tối thiểu 15 FPS

* Network latency giữa các services \< 100ms

### **3.2. Module phát hiện vi phạm mũ bảo hiểm** {#3.2.-module-phát-hiện-vi-phạm-mũ-bảo-hiểm}

#### **3.2.1. Xây dựng Dataset**

Dataset được tổng hợp từ nhiều nguồn công khai và được merge thành một unified dataset:

| Nguồn | Số ảnh gốc | Sau augmentation |
| :---- | :---- | :---- |
| Helmet Detection Dataset (Roboflow) | 3,500 | \- |
| Motorbike Traffic Dataset | 2,200 | \- |
| Asian Helmet Dataset | 1,800 | \- |
| Tổng (merged) | 7,500 | \~15,000 |

**Class mapping:** Các class từ các nguồn khác nhau được normalize về 8 classes thống nhất: {car, motorcycle, bus, truck, person, with\_helmet, without\_helmet, traffic\_light}

#### **3.2.2. Huấn luyện Model**

**Kiến trúc:** YOLOv8s (Small variant) được chọn với các lý do:

* 11.1M parameters \- đủ capacity cho 8 classes

* 28.7 GFLOPs \- phù hợp với Google Colab Tesla T4

* Pretrained COCO weights cho transfer learning hiệu quả

**Hyperparameters:**

| Parameter | Giá trị | Lý do |
| :---- | :---- | :---- |
| Epochs | 100 | Đủ để converge với early stopping |
| Batch size | 16 | Tối đa cho 16GB VRAM |
| Image size | 640×640 | Cân bằng accuracy/speed |
| Learning rate | 0.01 | Default YOLO, giảm dần |
| Early stopping patience | 20 | Tránh overfitting |

**Data augmentation** (YOLOv8 built-in):

* Mosaic: p=1.0 (ghép 4 ảnh thành 1\)

* HSV jitter: hue ±0.015, saturation ±0.7, value ±0.4

* Horizontal flip: p=0.5

* Scale: ±0.5

* Translation: ±0.1

#### **3.2.3. Chiến lược phát hiện kép (Dual-Strategy Detection)**

Đề tài đề xuất chiến lược phát hiện kép với hai nhánh: **Direct Detection (Chiến lược 1\)** làm primary và **Inference-based Detection (Chiến lược 2\)** làm fallback.

**Chiến lược 1: Direct Detection (Ưu tiên)**

Model phát hiện trực tiếp class without\_helmet và xác định vi phạm dựa trên relationship với person và vehicle.

| Algorithm 1: Direct No-Helmet Detection      ────────────────────────────────────────      Input: frame, detections\[\] from YOLO      Output: violations\[\]      	   1: no\_helmet\_boxes ← filter(detections, class \= 'without\_helmet')      2: for each head\_box in no\_helmet\_boxes do      3:     person ← find\_parent\_person(head\_box)  // head in top 50% of person      4:     if person is None then continue      5:           6:     vehicle ← find\_associated\_vehicle(person)      7:     if vehicle is None then continue  // Person must be on vehicle      8:           9:     confidence ← 0.25 × P\_person \+ 0.25 × P\_vehicle \+ 0.50 × P\_no\_helmet      10:    if is\_on\_vehicle(person, vehicle) then      11:        confidence ← confidence \+ 0.1  // Bonus      12:          13:    if not is\_duplicate(person, recent\_violations) then      14:        violations.append(create\_violation(person, confidence))      15: return violations |
| :---- |

Giải thích các hàm:

* find\_parent\_person(head\_box): Tìm person box chứa head\_box trong phần trên 50%

* find\_associated\_vehicle(person): Tìm vehicle có IoU ≥ 0.15 với person hoặc bottom\_center của person nằm trong vehicle box

* is\_duplicate(): Kiểm tra trùng lặp dựa trên track\_id và vị trí

**Chiến lược 2: Fallback Inference**

Khi Chiến lược 1 không phát hiện được without\_helmet, hệ thống suy luận từ absence of helmet:

| Algorithm 2: Fallback Inference Detection      ─────────────────────────────────────────      Input: frame, detections\[\], persons\_without\_direct\_detection\[\]      Output: violations\[\]      	   1: for each person in persons\_without\_direct\_detection do      2:     if not is\_rider(person) then continue      3:           4:     head\_region ← extract\_head\_region(person)  // Top 35-40%      5:     helmet\_found ← search\_helmet\_in\_region(head\_region, detections)      6:           7:     if not helmet\_found then      8:         confidence ← 0.7 × base\_confidence  // Lower confidence      9:         violations.append(create\_violation(person, confidence, method='fallback'))      10: return violations |
| :---- |

**Lý do cần fallback:** Model có thể miss without\_helmet detection do:

* Người cúi đầu (pose variation)

* Đầu bị che khuất một phần (partial occlusion)

* Small object trong frame wide-angle

#### **3.2.4. Object Tracking**

Đề tài sử dụng **CentroidTracker** \[12\] để gán ID nhất quán cho đối tượng qua các frame. Thuật toán hoạt động theo 4 bước: (1) loại bỏ các track đã hết thời gian sống (TTL \= 1.0 giây), (2) tính ma trận khoảng cách giữa các detection hiện tại và các track đã có, (3) thực hiện Hungarian matching với ngưỡng max\_distance \= 80 pixels, và (4) cập nhật các track đã match hoặc tạo track mới cho detection chưa match.

**De-duplication:** Để tránh báo cùng một người nhiều lần, hệ thống kiểm tra: (1) cùng track\_id trong 3 giây → Duplicate, (2) cùng vị trí (\<50px) trong 3 giây → Duplicate (trường hợp re-ID).

### **3.3. Module phát hiện vi phạm vượt đèn đỏ** {#3.3.-module-phát-hiện-vi-phạm-vượt-đèn-đỏ}

#### **3.3.1. Phát hiện màu đèn giao thông (HSV-based)**

Đề tài sử dụng HSV color thresholding làm primary method cho nhận dạng màu đèn.

**Cơ sở lý thuyết:** Không gian màu HSV (Hue-Saturation-Value) tách biệt thông tin màu sắc (Hue) khỏi độ sáng (Value), giúp robust hơn so với RGB trong điều kiện ánh sáng thay đổi. 

**HSV Thresholds:**

| \# Red (wraps around HSV wheel, needs 2 ranges)      RED\_RANGE\_1 \= (\[0, 70, 50\], \[10, 255, 255\])      RED\_RANGE\_2 \= (\[170, 70, 50\], \[180, 255, 255\])      \# Green      GREEN\_RANGE \= (\[40, 70, 50\], \[90, 255, 255\])       \# Yellow      YELLOW\_RANGE \= (\[20, 70, 50\], \[30, 255, 255\]) |
| :---- |

Giải thích:

| Component | Range | Ý nghĩa |
| :---- | :---- | :---- |
| Hue | 0-10, 170-180 (đỏ), 40-90 (xanh) | Xác định màu cơ bản |
| Saturation | 70-255 | Loại bỏ màu nhạt/trắng |
| Value | 50-255 | Loại bỏ vùng tối |

| Algorithm 4: HSV Color Detection      ────────────────────────────────      Input: traffic\_light\_crop (BGR image)      Output: state ∈ {RED, GREEN, YELLOW, UNKNOWN}      	   1: hsv ← cvtColor(traffic\_light\_crop, BGR2HSV)      2:       3: mask\_red ← inRange(hsv, RED\_RANGE\_1) \+ inRange(hsv, RED\_RANGE\_2)      4: mask\_green ← inRange(hsv, GREEN\_RANGE)      5: mask\_yellow ← inRange(hsv, YELLOW\_RANGE)      6:       7: red\_pixels ← countNonZero(mask\_red)      8: green\_pixels ← countNonZero(mask\_green)      9: yellow\_pixels ← countNonZero(mask\_yellow)      10:      11: total\_pixels ← height × width of crop      12: threshold ← 0.05 × total\_pixels  // Minimum 5%      13:      14: if red\_pixels \> threshold AND red\_pixels \> green\_pixels then      15:     return RED      16: else if green\_pixels \> threshold AND green\_pixels \> red\_pixels then      17:     return GREEN      18: else if yellow\_pixels \> threshold then      19:     return YELLOW      20: else      21:     return UNKNOWN |
| :---- |

#### **3.3.2. Chiến lược phát hiện hỗn hợp (Hybrid Detection)**

Kết hợp hai chiến lược:

| Chiến lược | Mô tả | Ưu tiên |
| :---- | :---- | :---- |
| **A: Static ROI** | Sử dụng vùng cố định từ config | Primary |
| **B: Object Detection** | YOLO detect 'traffic light', sau đó HSV | Fallback |

Workflow:

| 1\. Load traffic\_light\_roi from config      2\. If ROI exists:         \- Crop frame at ROI coordinates         \- Apply HSV color detection      1\. If state \== UNKNOWN or no ROI:         \- Run YOLO to detect 'traffic light' class         \- For each detected light:      	 \- Crop bounding box region      	 \- Apply HSV color detection      	 \- Return first valid state |
| :---- |

#### **3.3.3. Kiểm tra vượt vạch dừng (Stop Line Crossing)**

| Algorithm 5: Stop Line Violation Check      ──────────────────────────────────────      Input: vehicle\_center (cx, cy), stop\_line \[\[x1,y1\], \[x2,y2\]\]      Output: is\_violation (boolean)      	   1: // Lane check \- vehicle must be within stop line X range      2: min\_x ← min(x1, x2)      3: max\_x ← max(x1, x2)      4: if cx \< min\_x OR cx \> max\_x then      5:     return false  // Vehicle not in this lane      6:      7: // Crossing check \- vehicle center must be past stop line Y      8: stop\_y ← (y1 \+ y2) / 2      9: if cy \> stop\_y then      10:    return true  // Vehicle crossed stop line      11: else      12:    return false |
| :---- |

**Giả định:** Camera nhìn từ trên xuống hoặc nghiêng, xe di chuyển theo hướng y tăng dần (từ trên xuống trong ảnh).

#### **3.3.4. Cấu hình ROI**

File config/roi.json chứa thông tin vùng quan tâm cho từng camera:

| {        "camera\_pasteur": {      	"stop\_line": \[\[371, 137\], \[444, 147\]\],      	"traffic\_light\_roi": \[428, 90, 450, 104\]        }      } |
| :---- |

### **3.4. Kiến trúc Streaming Pipeline** {#3.4.-kiến-trúc-streaming-pipeline}

#### **3.4.1. Kafka Topics**

| Topic | Producer | Consumer | Mô tả |
| :---- | :---- | :---- | :---- |
| video\_frames | Video Producer | Detectors | Frames encoded base64 |
| helmet\_violations | Helmet Detector | Backend | Helmet violation events |
| traffic\_violations | Redlight Detector | Backend | Red light violation events |

#### **3.4.2. Message Format**

Video Frame:

| {        "camera\_id": "camera\_01",        "timestamp": "2024-12-29T15:30:00.123Z",        "frame\_number": 12345,        "image\_base64": "\<base64-encoded-jpg\>"      } |
| :---- |

Helmet Violation:

| {        "violation\_id": "uuid",        "timestamp": "2024-12-29T15:30:01.456Z",        "camera\_id": "camera\_01",        "track\_id": 42,        "confidence": 0.78,        "detection\_method": "direct\_no\_helmet",        "bounding\_box": {"x": 250, "y": 180, "w": 120, "h": 240}      } |
| :---- |

## **4\. Experiments and Results (Thực nghiệm và kết quả)** {#4.-experiments-and-results-(thực-nghiệm-và-kết-quả)}

### **4.1. Dataset và Experimental Setup** {#4.1.-dataset-và-experimental-setup}

#### **4.1.1. Dataset**

| Thuộc tính | Giá trị |
| :---- | :---- |
| Tổng số ảnh | 7,500 |
| Số classes | 8 |
| Image size | 640×640 |
| Format | YOLO (txt annotations) |
| Split | 80% train / 12% val / 8% test |

Class distribution trong test set:

| Class | Số instances |
| :---- | :---- |
| person | 1,847 |
| motorcycle | 1,523 |
| with\_helmet | 1,102 |
| without\_helmet | 689 |
| car | 845 |
| traffic\_light | 234 |

#### **4.1.2. Hardware và Software**

Mô hình được huấn luyện trên Google Colab Pro với GPU Tesla T4 (16GB VRAM) trong khoảng 3.5 giờ. Hệ thống inference chạy trên máy tính với CPU Intel i7-10750H, GPU GTX 1660 Ti (6GB), và 16GB RAM.

Phần mềm sử dụng: Python 3.10, Ultralytics 8.0.196, OpenCV 4.8.0, Kafka 3.x, PostgreSQL 15\.

### **4.2. Evaluation Metrics** {#4.2.-evaluation-metrics}

#### **4.2.1. Detection Metrics**

| Metric | Công thức | Mô tả |
| :---- | :---- | :---- |
| Precision | TP / (TP \+ FP) | Tỷ lệ detection đúng trong tổng predictions |
| Recall | TP / (TP \+ FN) | Tỷ lệ phát hiện được trong tổng ground truth |
| F1-Score | 2 × (P × R) / (P \+ R) | Harmonic mean của P và R |
| mAP@50 | Mean AP at IoU=0.5 | Standard object detection metric |
| mAP@50-95 | Mean AP at IoU=\[0.5:0.95:0.05\] | Stricter evaluation |

#### **4.2.2. System Metrics**

| Metric | Target |
| :---- | :---- |
| End-to-end latency | \< 500ms |
| Processing FPS | ≥ 25 FPS |
| Kafka throughput | ≥ 100 msg/s |

### **4.3. Results** {#4.3.-results}

#### **4.3.1. Model Performance (YOLOv8s Unified Model)**

**mAP@50 per class trên test set:**

| Class | mAP@50 | Precision | Recall |
| :---- | :---- | :---- | :---- |
| all | 86.6% | 84.3% | 82.1% |
| car | 94.7% | 92.1% | 91.5% |
| motorcycle | 64.9% | 71.2% | 63.8% |
| person | 94.4% | 91.8% | 90.2% |
| with\_helmet | 95.8% | 93.5% | 92.7% |
| without\_helmet | 89.9% | 87.4% | 85.6% |
| traffic\_light | 78.3% | 82.1% | 74.5% |
| **mAP@50-95** | **57.7%** | \- | \- |

**Nhận xét:**

* Các lớp có đặc trưng phân biệt rõ ràng (car, person, with\_helmet) đạt mAP \> 90%

* Lớp motorcycle có mAP thấp hơn (64.9%) do sự đa dạng cao giữa các loại xe

* Lớp traffic\_light đạt 78.3%, có thể cải thiện bằng tăng cường dữ liệu

#### **4.3.4. System Performance**

| Metric | Measured Value | Target | Status |
| :---- | :---- | :---- | :---- |
| End-to-end latency | 380ms | \< 500ms | ✓ |
| Processing FPS | 28 FPS | ≥ 25 FPS | ✓ |
| Kafka throughput | 156 msg/s | ≥ 100 msg/s | ✓ |
| Dashboard refresh | 1s | ≤ 2s | ✓ |

### **4.4. So sánh với các công trình liên quan** {#4.4.-so-sánh-với-các-công-trình-liên-quan}

Do không có quyền truy cập dataset của các công trình khác, chúng tôi so sánh các chỉ số được báo cáo trong các bài báo với kết quả mô hình trên tập dữ liệu của đề tài:

**Helmet Violation Detection:**

| Công trình | Phương pháp | mAP@50 | FPS | Dataset |
| :---- | :---- | :---- | :---- | :---- |
| Silva \[5\] | Faster R-CNN | 89.2% | 12 | Private (Brazil) |
| Singh \[6\] | YOLOv3 | 87.0% | 35 | 5,000 images |
| Jia \[7\] | YOLOv5s | 91.3% | 45 | 10,000 images |
| **Đề tài** | **YOLOv8s** | **89.9%** | **28** | 7,500 images |

**Nhận xét:** Đề tài đạt mAP tương đương với các công trình trước đó. FPS thấp hơn do xử lý thêm logic Dual-Strategy Detection và CentroidTracker trong pipeline thời gian thực.

## **5\. Discussion (Thảo luận)** {#5.-discussion-(thảo-luận)}

### **5.1. Phân tích thiết kế hệ thống** {#5.1.-phân-tích-thiết-kế-hệ-thống}

#### **5.1.1. DQ1: Dual-Strategy Detection**

Chiến lược phát hiện kép được thiết kế để giải quyết vấn đề khi mô hình không phát hiện được lớp \`without\_helmet\`. Cơ chế hoạt động:

- **Direct Detection (Ưu tiên):** Sử dụng kết quả trực tiếp từ YOLO khi phát hiện \`without\_helmet\`  
- **Fallback Inference:** Khi không tìm thấy mũ bảo hiểm trong vùng đầu của người đi xe, hệ thống suy luận vi phạm với confidence thấp hơn (0.7×)

**Ưu điểm:** Tăng khả năng phát hiện trong các trường hợp người cúi đầu hoặc bị che khuất một phần.

#### **5.1.2. DQ2: HSV-YOLO Hybrid**

Phương pháp hybrid sử dụng HSV làm primary method vì:

- Tốc độ nhanh (\~8ms so với \~45ms của YOLO)  
- Không cần training model riêng cho traffic light

YOLO fallback được kích hoạt khi HSV trả về UNKNOWN (ánh sáng khó, overexposure).

#### **5.1.3. DQ3: Kafka Streaming Architecture**

Kiến trúc streaming cho phép xử lý video thời gian thực với độ trễ \~380ms, đáp ứng yêu cầu \< 500ms. Bottleneck chính là suy luận YOLO (\~180ms), có thể tối ưu bằng TensorRT.

### **5.2. Case Studies** {#5.2.-case-studies}

#### **Case Study 1: Nhiều người ngồi trên một xe máy**

**Tình huống:** 3 người trên 1 xe máy, 2 người không đội mũ.

**Kết quả Direct Only:** Phát hiện 1/2 vi phạm (50%)

* Người phía sau bị che khuất

**Kết quả Dual-Strategy:** Phát hiện 2/2 vi phạm (100%)

* Fallback phát hiện người thứ 2 do không tìm thấy mũ trong vùng đầu

#### **Case Study 2: Đèn giao thông chuyển trạng thái**

**Tình huống:** Đèn chuyển từ vàng sang đỏ, xe tăng tốc vượt.

**Kết quả HSV:** Trả về YELLOW → Không phát hiện vi phạm

**Kết quả Hybrid:** 

* Frame N: YELLOW (không vi phạm)

* Frame N+5: RED (phát hiện vi phạm)

* Hệ thống ghi nhận chính xác thời điểm vi phạm

### **5.3. Limitations (Hạn chế)** {#5.3.-limitations-(hạn-chế)}

1. **Thiên lệch tập dữ liệu (Dataset bias):** Đa số ảnh chụp ban ngày, cần mở rộng tập dữ liệu với điều kiện ban đêm và thời tiết xấu

2. **Đơn camera:** Chưa hỗ trợ kết hợp nhiều camera để theo dõi phương tiện qua các góc nhìn khác nhau

3. **CentroidTracker đơn giản:** Có thể nhầm lẫn ID khi hai xe giao nhau. DeepSORT sẽ cải thiện độ chính xác theo dõi

4. **Không có nhận dạng biển số:** Chưa xác định được phương tiện vi phạm

5. **Ngưỡng HSV cố định:** Cần hiệu chỉnh riêng cho từng camera để đạt hiệu quả tối ưu

### **5.4. Các yếu tố ảnh hưởng đến kết quả** {#5.4.-các-yếu-tố-ảnh-hưởng-đến-kết-quả}

| Yếu tố | Mức độ ảnh hưởng | Giải pháp khắc phục |
| :---- | :---- | :---- |
| Ánh sáng | Cao | Điều chỉnh ngưỡng HSV theo vị trí |
| Góc camera | Trung bình | Cấu hình vùng quan tâm (ROI) |
| Mật độ giao thông | Trung bình | Điều chỉnh tham số theo dõi |
| Thời tiết | Cao | Cần thêm dữ liệu huấn luyện đa dạng |

## **6\. Conclusion and Future Work (Kết luận và hướng phát triển)** {#6.-conclusion-and-future-work-(kết-luận-và-hướng-phát-triển)}

### **6.1. Tóm tắt** {#6.1.-tóm-tắt}

Đề tài này trình bày một hệ thống phát hiện vi phạm giao thông tự động, tích hợp hai loại vi phạm (không đội mũ bảo hiểm và vượt đèn đỏ) trong một pipeline thống nhất. Hệ thống sử dụng YOLOv8s làm nền tảng phát hiện (đạt mAP@50 là 89.9% trên lớp without\_helmet), kết hợp với các chiến lược xử lý đặc thù cho từng loại vi phạm.

Các đóng góp chính bao gồm:

* **Dual-Strategy Detection:** Kết hợp phát hiện trực tiếp và suy luận dự phòng để tăng khả năng phát hiện vi phạm mũ bảo hiểm  
* **HSV-YOLO Hybrid:** Kết hợp phân ngưỡng màu HSV (nhanh) và YOLO fallback (chính xác) cho nhận dạng đèn giao thông  
* **Kafka Streaming Architecture:** Đạt độ trễ đầu-cuối \~380ms và thông lượng \~28 FPS, đáp ứng yêu cầu giám sát thời gian thực

### **6.2. Đóng góp chính** {#6.2.-đóng-góp-chính}

1. **Unified Multi-Violation Framework:** Framework cho phép mở rộng thêm các loại vi phạm khác mà không thay đổi architecture

2. **Dual-Strategy Detection:** Giải pháp cải thiện recall cho helmet detection thông qua cơ chế fallback có kiểm soát

3. **HSV-YOLO Hybrid:** Cân bằng hiệu quả giữa accuracy và speed cho traffic light recognition

4. **Production-Ready Pipeline:** Kiến trúc hoàn chỉnh từ video ingestion đến real-time dashboard

### **6.3. Hướng phát triển** {#6.3.-hướng-phát-triển}

Dựa trên các hạn chế đã xác định, đề tài đề xuất các hướng phát triển theo ba giai đoạn:

**Ngắn hạn (1-2 tháng):**

* Thay thế CentroidTracker bằng DeepSORT để cải thiện độ chính xác theo dõi

* Thu thập thêm dữ liệu ban đêm và điều kiện thời tiết xấu

* Triển khai ngưỡng HSV tự thích ứng theo điều kiện ánh sáng

**Trung hạn (3-6 tháng):**

* Tích hợp nhận dạng biển số xe để xác định phương tiện vi phạm

* Theo dõi đa camera với tái nhận dạng phương tiện

* Huấn luyện bộ phân loại đèn giao thông riêng để thay thế hoàn toàn HSV

**Dài hạn (6-12 tháng):**

* Edge deployment với tối ưu hóa TensorRT

* Ứng dụng di động cho cảnh sát giao thông

* Tích hợp với hệ thống xử phạt nguội quốc gia

## **References (Tài liệu tham khảo)** {#references-(tài-liệu-tham-khảo)}

\[1\] World Health Organization, "Global Status Report on Road Safety 2023," WHO, Geneva, 2023\.

\[2\] Ủy ban An toàn Giao thông Quốc gia, "Báo cáo tình hình an toàn giao thông năm 2023," Hà Nội, 2024\.

\[3\] Công an Thành phố Hồ Chí Minh, "Thống kê tai nạn giao thông tại các nút giao thông," Báo cáo nội bộ, 2023\.

\[4\] R. Kumar and S. Sharma, "Deep learning approaches for traffic violation detection: A comprehensive survey," *IEEE Access*, vol. 12, pp. 45678-45695, 2024\.

\[5\] M. Silva, J. Almeida, and R. Santos, "A deep learning approach for detecting red light infringements," *Pattern Recognition Letters*, vol. 165, pp. 112-120, 2024\.

\[6\] A. Singh, P. Kumar, and R. Gupta, "Motorcycle helmet detection using YOLOv3 deep learning algorithm," in *Proc. IEEE CVPR Workshops*, 2020, pp. 234-241.

\[7\] W. Jia, Y. Chen, and L. Zhang, "Real-time motorcycle helmet detection using YOLOv5," *Sensors*, vol. 21, no. 8, pp. 2668, 2021\.

\[8\] H. Kim, S. Park, and J. Lee, "Adaptive HSV-based traffic light recognition for autonomous vehicles," *Journal of Real-Time Image Processing*, vol. 18, no. 4, pp. 1123-1135, 2021\.

\[9\] S. Ozturk, M. Yilmaz, and A. Kaya, "Traffic light detection using YOLOv8 with depth-wise separable convolution," *IEEE Transactions on Intelligent Transportation Systems*, vol. 25, no. 3, pp. 2341-2355, 2024\.

\[10\] X. Chen, H. Wang, and K. Li, "Red light running detection using video analysis and deep learning," *Transportation Research Part C: Emerging Technologies*, vol. 145, pp. 103876, 2022\.

\[11\] T. Nguyen, H. Le, and V. Pham, "Automatic traffic red-light violation detection using YOLOv5s," *Traitement du Signal*, vol. 40, no. 5, pp. 2145-2153, 2023\.

\[12\] N. Wojke, A. Bewley, and D. Paulus, "Simple online and realtime tracking with a deep association metric," in *Proc. IEEE ICIP*, 2017, pp. 3645-3649.

\[13\] Y. Zhang, P. Sun, Y. Jiang, D. Yu, F. Weng, Z. Yuan, P. Luo, W. Liu, and X. Wang, "ByteTrack: Multi-object tracking by associating every detection box," in *Proc. ECCV*, 2022, pp. 1-21.

\[14\] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, "You only look once: Unified, real-time object detection," in *Proc. IEEE CVPR*, 2016, pp. 779-788.

\[15\] G. Jocher et al., "Ultralytics YOLOv8," GitHub repository, 2023\. \[Online\]. Available: [https://github.com/ultralytics/ultralytics](https://github.com/ultralytics/ultralytics)

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>