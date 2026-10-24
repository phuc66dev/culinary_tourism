# MASTER PROMPT: THIẾT KẾ UI/UX HỆ THỐNG DU LỊCH ẨM THỰC QUẬN 4

## FULL-STACK OFFLINE-FIRST PWA

## 1. VAI TRÒ

Bạn là một nhóm chuyên gia gồm:

- Senior Product Designer chuyên về ứng dụng bản đồ, du lịch và ẩm thực.
- UX Researcher có kinh nghiệm thiết kế cho người dùng đa ngôn ngữ và người ít quen công nghệ.
- Design System Designer chuyên xây dựng giao diện nhất quán trên web và thiết bị di động.
- Frontend Engineer thành thạo React 19, Vite, Tailwind CSS và MapLibre GL JS.

Hãy thiết kế sản phẩm có trải nghiệm đẹp, dễ hiểu, dễ dùng và khả thi khi triển khai thực tế. Không chỉ tạo giao diện bắt mắt; mọi lựa chọn về bố cục, màu sắc, hình ảnh và tương tác phải phục vụ nhu cầu của người dùng.

## 2. BỐI CẢNH SẢN PHẨM

- Tên sản phẩm: Hệ Thống Du Lịch Ẩm Thực Quận 4
- Tên tiếng Anh: Quan4 Culinary Tourism — Pocket Audio Tour Guide
- Loại sản phẩm: Progressive Web App (PWA), ưu tiên hoạt động ngoại tuyến.
- Công nghệ frontend mục tiêu: React 19, Vite, Tailwind CSS, MapLibre GL JS.
- Bản đồ: Vector tiles và PMTiles.
- Tính năng chính:
  - Khám phá quán ăn quanh vị trí hiện tại.
  - Tìm kiếm theo tên quán, món ăn và khu vực.
  - GPS geofencing tự động kích hoạt thuyết minh khi khách đến gần quán.
  - Audio đa ngôn ngữ theo nhiều tầng ưu tiên.
  - Lưu dữ liệu để sử dụng khi mất mạng.
  - Cổng dành cho chủ quán.
  - Bảng quản trị dành cho ban quản trị.
  - AI hỗ trợ soạn nội dung giới thiệu quán.

## 3. MỤC TIÊU THIẾT KẾ

Tạo một sản phẩm mang cảm giác:

- Hiện đại, thân thiện và đáng tin cậy.
- Gợi không khí khám phá ẩm thực đường phố Sài Gòn, nhưng không rập khuôn bằng hình ảnh hoặc họa tiết trang trí quá mức.
- Dễ sử dụng khi khách đang đi bộ, cầm điện thoại bằng một tay hoặc đứng ngoài trời.
- Rõ ràng với chủ quán lớn tuổi và người ít quen công nghệ.
- Hiệu quả khi ban quản trị cần xử lý nhiều dữ liệu trên màn hình desktop.
- Nhất quán giữa ứng dụng du khách, cổng chủ quán và bảng quản trị.

Ưu tiên thứ tự sau trong mọi quyết định thiết kế:

1. Dễ hiểu.
2. Dễ thao tác.
3. Dễ đọc và có độ tương phản tốt.
4. Nhất quán giữa các màn hình.
5. Đẹp mắt và có bản sắc.

Không hy sinh khả năng đọc hoặc thao tác để tạo hiệu ứng thị giác.

## 4. NGƯỜI DÙNG VÀ NHU CẦU

### 4.1. Du khách — Public Tourist PWA

- Khách trong nước và quốc tế khám phá ẩm thực Quận 4.
- Thường dùng điện thoại khi đang đi bộ, đôi khi chỉ có thể thao tác bằng một tay.
- Có thể gặp mạng yếu trong hẻm hoặc khi di chuyển.
- Cần chọn ngôn ngữ, xem quán gần mình, biết quán đang mở hay không và nghe giới thiệu mà không phải thao tác phức tạp.
- Ngôn ngữ: Tiếng Việt, Anh, Trung, Nhật, Hàn.

### 4.2. Chủ quán — Owner Portal

- Chủ quán và tiểu thương, một số người ít quen sử dụng ứng dụng.
- Cần chữ dễ đọc, nút lớn, biểu mẫu ngắn và hướng dẫn rõ ràng.
- Cần quản lý thông tin quán, thực đơn, trạng thái mở cửa và nội dung giới thiệu.
- Cần hiểu dữ liệu cá nhân nào được thu thập và được bảo vệ ra sao.

### 4.3. Ban quản trị — Admin Dashboard

- Cán bộ quản lý du lịch và quản trị viên hệ thống.
- Làm việc trên desktop với lượng dữ liệu lớn.
- Cần lọc, so sánh, duyệt và theo dõi trạng thái tác vụ nhanh chóng.
- Các thao tác quan trọng như duyệt bài, từ chối hoặc kích hoạt quán phải có trạng thái và phản hồi rõ ràng.

## 5. DESIGN SYSTEM

### 5.1. Nguyên tắc thị giác

Xây dựng một hệ thống giao diện thống nhất cho cả ba phân hệ:

- Bố cục sạch, có khoảng trắng hợp lý.
- Dùng lưới, căn lề và khoảng cách nhất quán.
- Ưu tiên bề mặt phẳng hoặc đổ bóng nhẹ; tránh hiệu ứng nổi quá mạnh.
- Dùng góc bo vừa phải và nhất quán.
- Hạn chế đường viền trang trí, gradient, glow, texture và hiệu ứng không phục vụ chức năng.
- Không tạo một phong cách hình ảnh riêng cho từng phân hệ. Có thể thay đổi mật độ thông tin và bố cục theo thiết bị, nhưng vẫn phải dùng chung design system.

### 5.2. Bảng màu

Dùng bảng màu tiết chế, dễ đọc và nhất quán:

- Màu nhấn thương hiệu: Cam `#E65100`
  - Dùng cho nút hành động chính, trạng thái được chọn, marker đang được chọn và điểm nhấn quan trọng.
  - Không dùng màu cam cho mọi nút hoặc toàn bộ thành phần trên màn hình.
- Nền chính: Trắng `#FFFFFF`.
- Nền phụ: Xám rất nhạt `#F5F5F5`.
- Bề mặt thẻ: Trắng `#FFFFFF`.
- Chữ chính: Than chì `#263238`.
- Chữ phụ: Xám `#616161`.
- Đường viền và phân cách: Xám nhạt `#E0E0E0`.
- Khu vực tối như Audio Player hoặc sidebar: Than chì `#263238`, dùng chữ trắng và màu trung tính.

Màu trạng thái chỉ dùng khi cần truyền đạt ý nghĩa:

- Thành công: xanh lá trầm.
- Đang xử lý hoặc chờ duyệt: vàng hổ phách trầm.
- Lỗi hoặc từ chối: đỏ trầm.

Quy tắc sử dụng màu:

- Mỗi màn hình chỉ có một màu nhấn thương hiệu nổi bật là màu cam.
- Màu trạng thái chỉ xuất hiện tại thành phần cần báo trạng thái.
- Không dùng màu riêng cho từng loại món ăn hoặc từng loại marker.
- Phân biệt danh mục bằng biểu tượng, tên và hình dạng; không phụ thuộc vào màu sắc.
- Không dùng cầu vồng màu, nền nhiều màu, gradient sặc sỡ hoặc hiệu ứng phát sáng nhiều màu.

### 5.3. Typography

Dùng một họ font nhất quán cho toàn sản phẩm:

- Font ưu tiên: Montserrat.
- Có thể dùng font dự phòng tương thích hệ thống nếu Inter không khả dụng.
- Hỗ trợ hiển thị tiếng Việt, Anh, Trung, Nhật và Hàn.
- Dùng thang kích thước chữ rõ ràng cho tiêu đề, nội dung, nhãn và thông tin phụ.
- Cỡ chữ nội dung thông thường từ 14px trở lên; giao diện du khách ngoài trời nên ưu tiên chữ 16px.
- Chữ nút và nhãn trạng thái phải đủ rõ, không dùng chữ quá nhỏ.
- Dùng độ đậm vừa phải; dành chữ đậm cho tiêu đề, giá, trạng thái hoặc hành động quan trọng.
- Đảm bảo độ tương phản giữa chữ và nền đạt mức dễ đọc.

### 5.4. Hình ảnh và biểu tượng

Hình ảnh cần tạo cảm giác chân thực, gần gũi và liên quan đến ẩm thực Quận 4:

- Ưu tiên ảnh món ăn và không gian quán thật, ánh sáng tự nhiên, màu sắc trung thực.
- Tránh ảnh stock quá bóng bẩy, ảnh món ăn không giống món Việt, ảnh minh họa giả lập hoặc hình ảnh sai địa điểm.
- Không dùng ảnh nền lớn phía sau chữ hoặc biểu mẫu quan trọng.
- Ảnh món ăn phải có tỉ lệ khung hình thống nhất, bo góc nhẹ và cách cắt ảnh phù hợp.
- Khi chưa có ảnh thật, dùng placeholder trung tính có nhãn rõ ràng; không tự tạo ảnh giả làm tư liệu thật của quán.
- Dùng một bộ icon nhất quán, ưu tiên icon đơn giản, dễ nhận biết.
- Trên bản đồ, dùng cùng phong cách marker; phân biệt quán bằng trạng thái chọn, icon hoặc nhãn chứ không dùng nhiều màu.

### 5.5. Thành phần dùng chung

Thiết kế và sử dụng nhất quán các thành phần:

- Nút chính, nút phụ, nút văn bản và nút nguy hiểm.
- Trường nhập liệu, ô tìm kiếm, dropdown và bộ lọc.
- Thẻ quán, thẻ món ăn và thẻ thông báo.
- Thanh điều hướng, bottom sheet, dialog và toast.
- Badge trạng thái, chỉ báo tải, trạng thái rỗng và trạng thái lỗi.
- Focus state rõ ràng khi dùng bàn phím.
- Touch target đủ lớn cho thao tác trên điện thoại; nút chính nên cao ít nhất 44px.

## 6. KIẾN TRÚC VÀ BỐ CỤC BA PHÂN HỆ

### 6.1. Phân hệ du khách — `public-app`

Thiết kế mobile-first cho khung điện thoại khoảng 375 × 812px. Bố cục phải thuận tiện cho vùng ngón tay cái và sử dụng ngoài trời.

Các màn hình và thành phần:

1. **Splash và chọn ngôn ngữ**
   - Màn hình đơn giản, tải nhanh, tập trung vào tên sản phẩm, lựa chọn ngôn ngữ và tiến trình đồng bộ.
   - Năm lựa chọn ngôn ngữ: VI, EN, ZH, JA, KO.
   - Nút lớn, có nhãn ngôn ngữ dễ hiểu.
   - Hiển thị tiến trình tải dữ liệu ngoại tuyến với trạng thái và dung lượng rõ ràng.

2. **Màn hình bản đồ**
   - Bản đồ là nội dung chính và chiếm phần lớn màn hình.
   - Thanh trên gồm tìm kiếm, chọn ngôn ngữ và truy cập gói ngoại tuyến.
   - Có nút định vị hiện tại, bộ lọc danh mục và chỉ báo trạng thái GPS.
   - Marker quán dùng một phong cách thống nhất.
   - Marker đang chọn có thể dùng màu cam và trạng thái được chọn dễ nhận biết.
   - Khu vực geofence bán kính 30m dùng nét đứt màu cam; tránh glow hoặc hoạt ảnh gây rối.
   - Khi bản đồ chưa tải được, hiển thị trạng thái ngoại tuyến và danh sách quán đã lưu nếu có.

3. **Audio Player**
   - Thanh phát âm thanh dễ nhận biết, có Play/Pause, tên quán và trạng thái ngôn ngữ.
   - Dùng nền than chì, chữ trắng và màu cam tiết chế cho trạng thái phát.
   - Hiển thị rõ nguồn âm thanh, chẳng hạn “Đã tải ngoại tuyến” hoặc “Đang phát trực tuyến”.
   - Nút điều khiển đủ lớn để sử dụng khi đi bộ.

4. **Chi tiết quán dạng Bottom Sheet**
   - Có các mức Peek, Half và Full.
   - Trình bày tên quán, ảnh món ăn, khoảng cách, giờ mở cửa, khoảng giá và món nổi bật.
   - Nội dung quan trọng hiển thị trước; thông tin phụ nằm ở phần mở rộng.
   - Có hành động rõ ràng: nghe giới thiệu, chỉ đường, xem thực đơn.
   - Không che mất toàn bộ bản đồ ở trạng thái mặc định.

5. **Gói ngoại tuyến**
   - Hiển thị dữ liệu nào sẽ được tải, dung lượng, tiến trình và thời điểm cập nhật.
   - Có trạng thái đang tải, hoàn tất, thiếu dung lượng, mất mạng và thử lại.
   - Giải thích ngắn gọn nội dung vẫn dùng được khi ngoại tuyến.

### 6.2. Phân hệ chủ quán — `owner-portal`

Thiết kế ưu tiên điện thoại, có thể dùng tốt trên tablet. Tập trung vào khả năng đọc và thao tác đơn giản.

Các màn hình và thành phần:

1. **Đăng ký chủ quán**
   - Quy trình ba bước: thông tin liên hệ, thông tin quán và vị trí, xác minh theo yêu cầu.
   - Có chỉ báo bước hiện tại và hướng dẫn ngắn.
   - Giải thích rõ việc thu thập và bảo vệ thông tin nhạy cảm.
   - Không đưa ra cam kết bảo mật, mã hóa hoặc thời hạn lưu trữ nếu các thông tin đó chưa được xác nhận bởi yêu cầu kỹ thuật.

2. **Trang quản lý quán**
   - Hiển thị tên quán và trạng thái hồ sơ ở vị trí dễ thấy.
   - Công tắc “Đang mở cửa” có nhãn chữ và trạng thái rõ ràng.
   - Lối tắt đến quản lý thực đơn, nội dung giới thiệu và thông báo duyệt.

3. **Quản lý thực đơn**
   - Danh sách món ăn dễ quét nhanh.
   - Cho phép thêm, sửa, xóa món và cập nhật giá.
   - Nhãn như “Bán chạy” hoặc “Món cay” thể hiện bằng chữ hoặc icon, không dựa riêng vào màu.

4. **Trợ lý viết nội dung AI**
   - Hướng dẫn chủ quán chọn từ khóa bằng các lựa chọn dễ hiểu.
   - Hiển thị số lượt sử dụng nếu có giới hạn thực tế.
   - Cho phép xem lại, chỉnh sửa và xác nhận nội dung trước khi gửi.
   - Nêu rõ nội dung do AI hỗ trợ soạn.
   - Nút hành động chính ghi rõ kết quả, ví dụ “Gửi nội dung để duyệt”.

5. **Thông báo**
   - Hiển thị kết quả duyệt và lý do từ chối bằng lời văn dễ hiểu.
   - Cung cấp hành động tiếp theo phù hợp, như sửa nội dung hoặc xem chi tiết hồ sơ.

### 6.3. Phân hệ quản trị — `admin-dashboard`

Thiết kế desktop-first, phù hợp màn hình rộng và có thể co giãn cho tablet. Ưu tiên khả năng đọc dữ liệu và thực hiện tác vụ chính xác.

Các màn hình và thành phần:

1. **Tổng quan quản trị**
   - Hiển thị số liệu cần thiết, tác vụ đang chờ xử lý và lỗi cần chú ý.
   - Tránh dùng quá nhiều thẻ KPI hoặc biểu đồ trang trí.
   - Mỗi chỉ số phải có nhãn và ngữ cảnh rõ ràng.

2. **Theo dõi tác vụ audio**
   - Hiển thị tiến trình dịch và tạo audio theo quán, ngôn ngữ và trạng thái.
   - Hỗ trợ các hành động phù hợp như tạm dừng, tiếp tục hoặc hủy nếu backend hỗ trợ.
   - Dùng màu trạng thái đúng ý nghĩa, kèm nhãn văn bản; không chỉ dùng màu để phân biệt.

3. **Bảng quản lý quán**
   - Có tìm kiếm, lọc, phân trang và sắp xếp.
   - Thể hiện trạng thái hồ sơ, ngôn ngữ đã có và tình trạng audio.
   - Activation Gate phải giải thích điều kiện chưa đạt và lý do không thể kích hoạt.

4. **Màn hình duyệt đề xuất**
   - So sánh bản hiện tại và bản đề xuất theo từng trường.
   - Làm nổi bật phần thay đổi bằng nền trung tính nhẹ, nhãn hoặc viền; không tô màu toàn bộ cột.
   - Nút duyệt và từ chối có nhãn hành động rõ ràng.
   - Khi từ chối, yêu cầu nhập lý do phù hợp và cho biết lý do đó sẽ được gửi cho chủ quán.

5. **Trạng thái hệ thống**
   - Thiết kế trạng thái tải, không có kết quả, lỗi kết nối và không đủ quyền.
   - Báo lỗi bằng ngôn ngữ dễ hiểu và nêu hành động có thể thực hiện tiếp theo.

## 7. QUY TẮC UX VÀ MICRO-INTERACTIONS

### 7.1. Geofence

- Khi khách đi vào vùng 30m, hiển thị tín hiệu trực quan nhẹ trên marker.
- Có thể phát audio tự động nếu người dùng đã cho phép và đã bật tính năng.
- Không làm phát âm thanh bất ngờ khi chưa có sự đồng ý.
- Tránh lặp lại thông báo liên tục khi khách đứng gần quán.
- Cho phép dừng, phát lại hoặc mở thông tin quán.

### 7.2. Chuyển ngôn ngữ

- Chuyển ngôn ngữ không làm mất vị trí đang xem, bộ lọc hoặc quán đang mở.
- Cập nhật nhãn, nội dung và trạng thái audio đồng bộ.
- Nếu nội dung ở ngôn ngữ đã chọn chưa có, thông báo rõ và gợi ý lựa chọn tiếp theo.

### 7.3. Ngoại tuyến

- Luôn phân biệt trạng thái trực tuyến, ngoại tuyến và đang đồng bộ.
- Khi mất mạng, không biến màn hình thành trạng thái lỗi toàn trang nếu dữ liệu đã lưu vẫn dùng được.
- Cho biết nội dung nào đang có sẵn ngoại tuyến và nội dung nào cần kết nối mạng.
- Có nút thử lại khi thao tác cần mạng.

### 7.4. Phản hồi thao tác

- Mọi nút và hành động phải có trạng thái mặc định, hover, focus, pressed, loading, disabled và error phù hợp.
- Dùng chuyển động ngắn, có mục đích và không gây phân tâm.
- Tôn trọng tùy chọn giảm chuyển động của hệ điều hành.
- Không dùng animation để thay thế thông báo bằng chữ.

## 8. YÊU CẦU VỀ ACCESSIBILITY

- Độ tương phản chữ và nền đủ rõ.
- Không truyền đạt trạng thái chỉ bằng màu sắc.
- Thành phần tương tác có nhãn dễ hiểu.
- Hỗ trợ bàn phím và focus state ở các màn hình desktop.
- Kích thước nút trên mobile đủ lớn để chạm.
- Form có nhãn, hướng dẫn và thông báo lỗi gắn với trường tương ứng.
- Ngôn ngữ và cách diễn đạt rõ ràng, tránh thuật ngữ kỹ thuật đối với du khách và chủ quán.

## 9. YÊU CẦU ĐẦU RA

Trả về kết quả theo trình tự:

1. **Tóm tắt hướng thiết kế**
   - Mô tả phong cách tổng thể, nguyên tắc thị giác và cách sản phẩm tạo cảm giác thống nhất.

2. **Design System**
   - Bảng màu và quy tắc sử dụng.
   - Font chữ, thang chữ và phân cấp tiêu đề.
   - Khoảng cách, góc bo, bóng đổ, icon và kiểu ảnh.
   - Các trạng thái nút, biểu mẫu, thẻ và thông báo.

3. **Cấu trúc giao diện**
   - Component hierarchy và bố cục cho từng màn hình.
   - Nêu rõ sự khác biệt giữa mobile, tablet và desktop.

4. **Luồng và tương tác**
   - Luồng chính của du khách, chủ quán và quản trị viên.
   - Các trạng thái tải, ngoại tuyến, thành công, lỗi và dữ liệu rỗng.

5. **Mã nguồn mẫu**
   - Tạo giao diện React + Tailwind CSS theo từng phân hệ hoặc từng nhóm màn hình.
   - Dùng dữ liệu mẫu phù hợp với các địa điểm như Ốc Oanh Vĩnh Khánh, Phá Lấu Cô Thảo Tôn Đản và Súp Cua Hằng Xóm Chiếu.
   - Không tự bịa địa chỉ, giờ hoạt động, giá hoặc thông tin xác thực nếu chưa có dữ liệu.
   - Tách thành component dễ bảo trì và dùng chung design tokens.
   - Không chỉ tạo một trang landing page đại diện cho toàn bộ hệ thống.

## 10. TIÊU CHÍ TỰ ĐÁNH GIÁ TRƯỚC KHI HOÀN TẤT

Trước khi trả kết quả, hãy kiểm tra:

- Ba phân hệ có dùng cùng một bảng màu, typography, icon và ngôn ngữ thiết kế không?
- Màu cam có được sử dụng tiết chế và có mục đích không?
- Có màu nào chỉ xuất hiện để trang trí mà không truyền đạt chức năng không?
- Hình ảnh có phù hợp với ẩm thực đường phố Quận 4 và được phân biệt rõ là ảnh thật hay placeholder không?
- Du khách có thể tìm và mở quán gần mình trong vài thao tác không?
- Chủ quán có thể hoàn thành tác vụ chính mà không cần hiểu thuật ngữ kỹ thuật không?
- Quản trị viên có thể nhận biết trạng thái và hành động tiếp theo nhanh không?
- Mất mạng, tải chậm, nội dung trống và lỗi đã có giao diện xử lý rõ chưa?
- Giao diện có dễ đọc và dễ chạm trên điện thoại không?
