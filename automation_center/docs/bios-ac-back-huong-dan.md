# Nhờ bật lại máy tự động sau khi mất điện (1 phút)

Gửi người đang ở cùng phòng với máy tính đặt ở góc — máy chạy phần mềm tạo ảnh
của công ty. Việc này **không cài gì, không xoá gì**, chỉ gạt một công tắc có
sẵn trong máy.

**Lý do:** hiện tại cứ mất điện là máy nằm im cho tới khi có người bấm nút
nguồn. Nửa năm vừa rồi chuyện này xảy ra 5 lần, lần lâu nhất máy chết 2 ngày
mà không ai biết. Bật xong thì có điện trở lại là máy tự lên.

## Làm thế nào

1. Bật máy (bấm nút nguồn) rồi **bấm liên tục phím `Delete`** ngay từ giây đầu,
   cho tới khi hiện màn hình xanh/cam của BIOS. Bấm hụt thì tắt máy bấm lại.
2. Nếu màn hình đang ở dạng đơn giản, bấm **`F2`** để sang *Advanced Mode*.
3. Vào tab **`Settings`** → mục **`Platform Power`** (một số máy ghi là
   `Power Management`).
4. Tìm dòng **`AC BACK`** → đổi thành **`Always On`**.
   (Có bản BIOS ghi là `Restore on AC Power Loss` → chọn `Power On`.)
5. Ngay dưới đó thường có dòng **`ErP`** → đổi thành **`Disabled`**.
6. Bấm **`F10`** → chọn **`Yes`** để lưu. Máy tự khởi động lại.

Xong. Không cần đăng nhập vào Windows, cứ để máy tự chạy.

## Nếu không thấy đúng chữ như trên

Chụp ảnh màn hình BIOS đang hiện rồi gửi lại — chỉ cần ảnh, không cần làm gì
thêm. Tên mục khác nhau tuỳ đời máy nhưng luôn có một dòng về "AC" hoặc
"Power Loss".

## Kiểm tra giúp luôn (nếu tiện)

Rút phích điện của máy khoảng 10 giây rồi cắm lại. Máy tự sáng đèn và tự lên
là đạt. Nếu vẫn im thì báo lại, đừng bấm nút nguồn vội — im chính là kết quả
cần biết.
