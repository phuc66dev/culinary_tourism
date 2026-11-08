# PRD | Hệ thống Du lịch Ẩm thực Quận 4

**Phiên bản 2.0 · 08/11/2026**

Tài liệu yêu cầu sản phẩm cho website Chủ quán và Quản trị, backend dùng chung và ứng dụng Du khách trên điện thoại. Các yêu cầu dưới đây mô tả hành vi cần đạt. Trạng thái triển khai của từng phần nằm ở mục 8.

## 1. Bối cảnh và mục tiêu

Du khách cần tìm quán ăn ở Quận 4 theo vị trí, hiểu món ăn qua nội dung đa ngôn ngữ và tiếp tục tham quan khi kết nối không ổn định. Chủ quán cần một kênh cập nhật thực đơn và thông tin địa điểm. Quản trị viên cần kiểm tra chủ sở hữu, duyệt thay đổi và kiểm soát nội dung trước khi công khai.

Mục tiêu MVP là chứng minh một luồng xuyên suốt. Chủ quán gửi hồ sơ, Admin xác minh và gắn quán, nội dung đạt điều kiện công khai, sau đó du khách tìm được quán và phát được thuyết minh trên điện thoại.

| Người dùng | Việc cần hoàn thành |
| --- | --- |
| Chủ quán | Đăng ký, theo dõi xác minh, quản lý đúng quán của mình và biết kết quả duyệt đề xuất. |
| Quản trị viên | Đối chiếu hồ sơ, xử lý quán trùng, duyệt nội dung, chuẩn bị audio và quyết định khi nào công khai quán. |
| Du khách | Tìm quán trên điện thoại, xem thông tin hữu ích và nghe thuyết minh bằng ngôn ngữ phù hợp. |

## 2. Phạm vi sản phẩm và trách nhiệm

| Phần | Nơi phát triển | Trách nhiệm |
| --- | --- | --- |
| Website Chủ quán | Repo này, `frontend/` | Đăng ký, xác minh, quản lý quán và thực đơn, AI Advisor, đề xuất và thông báo. |
| Website Quản trị | Repo này, `frontend/` | Xét duyệt hồ sơ, POI Master, duyệt đề xuất, Nhà máy Audio, tài khoản, quyền và nhật ký. |
| Backend dùng chung | Repo này, `backend/` | Xác thực và phân quyền web, lưu hồ sơ và dữ liệu quán, kiểm duyệt, dịch và audio, API và tài nguyên dành cho mobile. |
| Ứng dụng Du khách | Repo mobile riêng | Bản đồ, tìm quán, ngôn ngữ, GPS, kích hoạt thuyết minh, trình phát và lưu gói ngoại tuyến trên điện thoại. |

Trang gốc website dẫn tới đăng nhập chung tại `/admin/login`. Chủ quán đăng ký tại `/register/owner` và làm việc ở `/owner`. Quản trị viên làm việc ở `/admin`. Website cần dùng được trên màn hình nhỏ. Giao diện bản đồ du khách, geofencing và PWA ngoại tuyến của du khách thuộc phạm vi mobile.

Đặt món, thanh toán, đặt bàn, đánh giá công khai và chứng nhận an toàn thực phẩm nằm ngoài phạm vi MVP.

## 3. Luồng đưa quán từ hồ sơ lên ứng dụng du khách

1. **Chủ quán gửi hồ sơ.** Nhập thông tin liên hệ, thông tin quán, CCCD và đường dẫn ảnh mặt tiền nếu có. Tài khoản có thể đăng nhập để xem hồ sơ và thông báo trong lúc chờ xác minh.
2. **Admin xác minh và đối chiếu POI Master.** Tìm theo tên và địa chỉ từ hồ sơ. Có thể rút gọn tiêu chí hoặc tìm từng trường để nhận ra quán được viết khác tên. Nếu tìm thấy đúng quán, chọn bản ghi để gắn. Nếu quán chưa có, xác nhận đã đối chiếu rồi bổ sung phường, tọa độ và mô tả tiếng Việt để tạo quán nháp. Quán nháp dùng tên và địa chỉ từ hồ sơ, xuất hiện trong POI Master ở trạng thái ẩn.
3. **Backend lưu quyết định.** Phê duyệt, liên kết quán và xác minh tài khoản được lưu trong cùng giao dịch. Nếu từ chối, Admin nhập lý do. Hệ thống lưu kết quả, ghi nhật ký và thông báo cho chủ quán. Với hồ sơ cũ đã duyệt nhưng chưa có liên kết, Admin có thể bổ sung quán trong tab **Đã duyệt**.
4. **Chủ quán hoàn thiện dữ liệu.** Chủ quán cập nhật thực đơn và trạng thái mở cửa trực tiếp. Thay đổi hồ sơ quán như tên, địa chỉ, mô tả, ảnh và vị trí được gửi thành đề xuất. Admin so sánh dữ liệu hiện tại với nội dung gửi lên rồi duyệt hoặc từ chối kèm lý do.
5. **Admin công khai quán.** Admin kiểm tra thông tin địa điểm, chuẩn bị tên và mô tả tiếng Anh, tạo audio tiếng Anh và kiểm tra điều kiện công khai. Khi đủ điều kiện, Admin bật công khai trong POI Master.
6. **Du khách tiếp cận quán.** Mobile tải danh sách địa điểm công khai từ backend, hiển thị quán trên bản đồ và cho phép xem nội dung hoặc nghe audio. Hoàn tất bước này cần API đọc POI trả dữ liệu thực và app mobile tích hợp thành công.

**Ba trạng thái độc lập.** Hồ sơ được duyệt xác nhận người quản lý. `is_open` mô tả quán đang mở hay đóng cửa. `is_active` quyết định quán đủ điều kiện được trả trong API công khai. Duyệt hồ sơ hoặc đổi trạng thái mở cửa không thay thế bước công khai.

## 4. Yêu cầu chức năng website

### 4.1. Cổng Chủ quán

| Mã | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| OWN-01 | Đăng ký và theo dõi xác minh | Người đăng ký nhận xác nhận đã gửi hồ sơ, xem được trạng thái chờ duyệt, đã duyệt hoặc từ chối và đọc được phản hồi Admin. |
| OWN-02 | Tổng quan và quản lý quán | Chủ quán đã xác minh chỉ thấy quán được gắn với tài khoản. Khi chưa có quán, màn hình giải thích tình trạng. Gọi API bằng ID quán của người khác bị từ chối. |
| OWN-03 | Mở cửa và thực đơn | Chủ quán đổi trạng thái mở cửa, thêm, sửa, xóa món có tên và giá VND. Ảnh và nhãn món là thông tin bổ sung. |
| OWN-04 | Đề xuất thay đổi | Chủ quán gửi các trường đã thay đổi, xem lịch sử và nhận thông báo khi Admin xử lý. Hồ sơ quán được cập nhật khi đề xuất được duyệt. |
| OWN-05 | AI Advisor | Tạo bản nháp mô tả từ dữ kiện chủ quán cung cấp. Chủ quán đọc lại, sửa hoặc chèn vào đề xuất. Giới hạn mặc định 10 lượt mỗi tài khoản mỗi ngày theo UTC, có thể cấu hình. Khi Gemini thiếu cấu hình hoặc lỗi, chủ quán vẫn nhập mô tả thủ công. |

### 4.2. Cổng Quản trị

| Mã | Yêu cầu | Tiêu chí chấp nhận |
| --- | --- | --- |
| ADM-01 | Xác minh hồ sơ và gắn POI | Khi duyệt, Admin chọn đúng một quán có sẵn hoặc tạo nháp. Backend chặn gắn quán thuộc chủ khác và chặn tạo mới khi trùng tên, địa chỉ theo quy tắc so khớp. Các trường hợp tên hoặc địa chỉ được ghi khác cần Admin đối chiếu. |
| ADM-02 | POI Master | Admin có quyền có thể tạo, xem, sửa, ẩn, công khai hoặc xóa POI theo quy trình. Quán mới ở trạng thái ẩn. Tọa độ, địa chỉ, ảnh và mô tả có thể được kiểm tra trước khi công khai. |
| ADM-03 | Duyệt đề xuất | Admin xem giá trị trước và sau. Duyệt cập nhật đúng phiên bản POI đang xem. Nếu dữ liệu đã đổi, hệ thống yêu cầu tải lại. Từ chối cần lý do để chủ quán có thể chỉnh và gửi lại. |
| ADM-04 | Điều kiện công khai | Backend chỉ cho bật công khai khi có tên, mô tả tiếng Anh và audio tiếng Anh đã hoàn tất. Nếu đổi tên hoặc mô tả của quán đang công khai, Admin tắt công khai trước, duyệt nội dung mới rồi hoàn thiện bản tiếng Anh và audio để bật lại. |
| ADM-05 | Nhà máy Audio | Admin tạo tác vụ dịch và sinh audio, theo dõi tiến độ và lỗi, nghe thử kết quả. Khi dịch tự động lỗi, có luồng nhập bản dịch thủ công để tiếp tục xử lý. |
| ADM-06 | Vận hành và phân quyền | Dashboard tổng hợp dữ liệu theo quyền. Admin quản lý tài khoản, vai trò và xem nhật ký theo quyền được cấp. Các thao tác nhạy cảm như xem CCCD, duyệt hồ sơ và sửa POI có dấu vết kiểm tra. |

## 5. Yêu cầu tích hợp ứng dụng Du khách

| Mã | Backend trong repo này | Ứng dụng mobile |
| --- | --- | --- |
| MOB-01 | Hoàn thiện `GET /api/v1/poi/load-all` và `GET /api/v1/poi/nearby` với dữ liệu MongoDB, chỉ trả POI công khai. Chuẩn hóa dữ liệu chi tiết quán, thực đơn, ảnh và trạng thái mở cửa. | Tìm quán, xem bản đồ, xem chi tiết và xử lý trạng thái không có dữ liệu hoặc mất mạng. |
| MOB-02 | Cung cấp nội dung theo ngôn ngữ và URL audio phù hợp. Khi thiếu bản dịch, ưu tiên ngôn ngữ đã chọn, rồi tiếng Anh, rồi tiếng Việt gốc. Hợp đồng dữ liệu cần thể hiện ngôn ngữ thực tế và tình trạng thiếu audio. | Cho phép chọn ngôn ngữ, nghe thủ công, tự kích hoạt theo vị trí nếu được cấp quyền. Khi thiếu audio, vẫn hiển thị thông tin quán. |
| MOB-03 | Cung cấp thông tin gói PMTiles và tài nguyên có thể tải, cùng cơ chế phiên bản để cập nhật dữ liệu. Thiết kế đồng bộ để quán bị ẩn hoặc xóa được loại khỏi dữ liệu mobile khi đồng bộ lại. | Tải và quản lý gói đã chọn, hiển thị nội dung đã lưu khi ngoại tuyến, đồng bộ lại khi có mạng. |
| MOB-04 | Hoàn thiện hợp đồng cho gói ngôn ngữ giao diện, tải trước nội dung hoặc audio theo vùng và sinh audio theo yêu cầu. | Dùng các hợp đồng này sau khi chốt định dạng và hành vi dự phòng với nhóm backend. |
| MOB-05 | Chỉ triển khai đo lường khi đã có quy tắc đồng ý, giới hạn dữ liệu, lưu giữ và kiểm thử. Dữ liệu vị trí chính xác cần được giảm thiểu. | Xin quyền vị trí khi cần cho tính năng. Người từ chối định vị vẫn có thể tìm quán và nghe thủ công. Việc đồng ý phân tích là lựa chọn riêng. |

MVP ưu tiên bản đồ, chi tiết quán và audio đã tạo. Đa ngôn ngữ mở rộng, gói ngoại tuyến, đồng bộ thay đổi và tự phát theo vùng được nghiệm thu theo từng mốc. Định dạng gói, phiên bản API, chiến lược cache và ngôn ngữ hỗ trợ khi ra mắt cần được thống nhất giữa hai repo trước khi thử thực địa.

## 6. Dữ liệu, bảo mật và vận hành

- **Dữ liệu chính.** `users` và `roles` quản lý danh tính và quyền. `poi_owner_registrations` lưu hồ sơ xác minh và liên kết quán. `poi` lưu địa điểm và chủ sở hữu. `menu_items`, `poi_submissions`, `poi_localizations` và `owner_notifications` lưu thực đơn, đề xuất, bản địa hóa và thông báo. Mỗi POI có ID ổn định. GeoJSON lưu tọa độ theo thứ tự kinh độ rồi vĩ độ.
- **Phiên và quyền.** Web dùng cookie HttpOnly, HTTPS và thiết lập cookie phù hợp khi triển khai. Backend kiểm tra quyền theo vai trò và quyền sở hữu trên mọi API quản lý, kể cả khi người dùng gọi API trực tiếp. API du khách chỉ trả trường được phép công khai.
- **CCCD và quyền riêng tư.** Mã hóa CCCD bằng Fernet khi lưu. Chỉ người có quyền được xem theo thao tác tường minh có audit. Không đưa CCCD vào danh sách hồ sơ, nhật ký, thông báo, nội dung AI hay API mobile. Thời hạn lưu mặc định là 180 ngày và có thể cấu hình.
- **Tính nhất quán.** Duyệt hồ sơ, liên kết POI và tạo nháp cần giao dịch MongoDB. Duyệt đề xuất kiểm tra phiên bản hiện tại. Các yêu cầu lặp hoặc song song không được tạo thêm nháp, đổi sai chủ hoặc ghi đè dữ liệu mới hơn.
- **An toàn tài nguyên và dịch vụ ngoài.** Kiểm tra đường dẫn tệp bản đồ và audio. Đặt giới hạn đầu vào và lượt dùng cho AI, audio và các API cần thiết. Nếu dịch, TTS hoặc AI lỗi, UI phải báo rõ và cho phép tiếp tục bằng luồng thủ công phù hợp.
- **Vận hành.** Frontend dùng React, Vite và Tailwind. Backend dùng FastAPI, MongoDB replica set và Redis. Dùng `/health`, `/health/ready` và `/docs` để kiểm tra dịch vụ. Các trang có danh sách cần phân trang và trạng thái tải, rỗng, lỗi rõ ràng. Theo dõi độ trễ API, tỷ lệ lỗi và thời gian hoàn tất audio ở môi trường thử nghiệm trước khi đặt cam kết hiệu năng.

## 7. Nghiệm thu và chỉ số

| Kịch bản | Kết quả cần thấy |
| --- | --- |
| Hồ sơ cho quán đã tồn tại | Admin tìm được quán bằng tên hoặc địa chỉ, gắn vào đúng tài khoản và không tạo thêm POI. |
| Hồ sơ cho quán mới | Admin xác nhận đã đối chiếu, bổ sung dữ liệu và tạo đúng một quán ẩn. Chủ quán xem được quán sau khi được xác minh và gắn. |
| Trùng dữ liệu hoặc khác chủ | Backend từ chối thao tác không hợp lệ, giữ nguyên quyền sở hữu và trạng thái hồ sơ. |
| Kiểm duyệt nội dung | Đề xuất chờ duyệt chưa tác động hồ sơ công khai. Sau khi duyệt, thay đổi và thông báo được lưu. Từ chối có lý do. |
| Công khai và ẩn quán | Quán thiếu nội dung hoặc audio EN không thể bật công khai. Sau khi đủ điều kiện, thiết bị thật thấy quán và phát được audio. Khi quán bị ẩn, mobile loại quán khi đồng bộ lại. |
| Bảo mật | Chủ quán không sửa được quán của người khác. API du khách và nhật ký không chứa CCCD. |
| Ngoại tuyến khi mốc tương ứng sẵn sàng | Điện thoại mở được bản đồ và phát audio đã tải khi mất mạng, rồi đồng bộ lại khi có kết nối. |

Trong đợt thử nghiệm, đo tỷ lệ hồ sơ duyệt có quán được gắn, số lần bị chặn vì trùng hoặc xung đột, thời gian từ gửi hồ sơ đến công khai, và tỷ lệ quán công khai tải và phát audio thành công trên mobile. Chốt ngưỡng mục tiêu sau khi có số liệu thử nghiệm đầu tiên.

## 8. Hiện trạng và thứ tự triển khai

| Mốc | Trạng thái theo mã nguồn hiện tại | Điều kiện hoàn thành |
| --- | --- | --- |
| 1. Vận hành hai cổng web | Đã có đăng nhập, đăng ký, tìm và gắn quán hoặc tạo nháp khi duyệt, quản lý thực đơn, đề xuất, thông báo, POI Master và điều kiện công khai. AI và audio cần cấu hình dịch vụ tương ứng. | Chạy thử luồng mới và luồng bổ sung quán cho hồ sơ đã duyệt trên môi trường kiểm thử với MongoDB thật. |
| 2. Mobile đọc quán công khai | Hai route đọc danh sách và quán gần đây đã có khung, hiện trả danh sách rỗng. Hợp đồng đọc chi tiết và thực đơn cần hoàn thiện. | API trả dữ liệu thật, loại quán ẩn và được kiểm tra trên app mobile. |
| 3. Audio và đa ngôn ngữ | Có luồng quản trị tác vụ audio. Luồng bản địa hóa theo yêu cầu, tải trước và gói chuỗi UI còn cần hoàn thiện. | Kiểm tra bản dịch, audio, ngôn ngữ dự phòng và xử lý lỗi trên thiết bị thật. |
| 4. Ngoại tuyến và vận hành | API bản đồ trả thông tin gói mẫu. Đồng bộ thay đổi, nghiệm thu gói tải và đo lường có đồng ý là các hạng mục tiếp theo. | Kiểm tra tải gói, mất mạng, đồng bộ lại và quy tắc quyền riêng tư trước khi phát hành. |

**Tài liệu vận hành** nằm trong [README dự án](README.md) và [hướng dẫn backend](backend/README.md). Dùng OpenAPI của môi trường đang chạy để đối chiếu endpoint và schema hiện hành.
