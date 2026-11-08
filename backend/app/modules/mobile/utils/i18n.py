from typing import Dict, Optional

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "otp_subject": "[Quan 4 Culinary] Email verification",
        "otp_body": "Your verification code is: {otp}\nThis code is valid for {minutes} minutes.",
        "otp_sent": "OTP sent to email",
        "invalid_otp": "Invalid OTP",
        "otp_expired": "OTP expired",
        "no_pending": "No pending verification for this email",
        "too_many_attempts": "Too many attempts",
        "email_exists": "Email already exists",
        "username_exists": "Username already exists",
        "invalid_credentials": "Invalid email or password",
        "smtp_not_configured": "SMTP not configured",
        "invalid_token": "Invalid token",
        "token_expired": "Token expired",
        "user_not_found": "User not found",
        "profile_not_found": "Profile not found",
        "update_profile_success": "Profile updated successfully",
        "change_password_success": "Password changed successfully",
        "reset_subject": "[Quan 4 Culinary] Password reset",
        "reset_body": "Your password reset code is: {otp}\nThis code is valid for {minutes} minutes.",
        "reset_sent": "Password reset code sent to email",
        "poi_not_found": "POI not found",
        "content_not_found": "Audio content not found",
    },
    "vi": {
        "otp_subject": "[Ẩm Thực Quận 4] Mã xác thực tài khoản",
        "otp_body": "Mã xác thực của bạn là: {otp}\nMã này có hiệu lực trong {minutes} phút.",
        "otp_sent": "Mã OTP đã được gửi về email của bạn",
        "invalid_otp": "Mã OTP không chính xác",
        "otp_expired": "Mã OTP đã hết hạn",
        "no_pending": "Không có yêu cầu xác thực nào đang chờ cho email này",
        "too_many_attempts": "Đã thử sai quá nhiều lần. Vui lòng gửi lại mã mới",
        "email_exists": "Email này đã được sử dụng",
        "username_exists": "Tên đăng nhập đã tồn tại",
        "invalid_credentials": "Email hoặc mật khẩu không chính xác",
        "smtp_not_configured": "Hệ thống gửi mail chưa được cấu hình",
        "invalid_token": "Token không hợp lệ",
        "token_expired": "Phiên đăng nhập đã hết hạn",
        "user_not_found": "Không tìm thấy người dùng",
        "profile_not_found": "Không tìm thấy thông tin hồ sơ",
        "update_profile_success": "Cập nhật thông tin thành công",
        "change_password_success": "Đổi mật khẩu thành công",
        "reset_subject": "[Ẩm Thực Quận 4] Đặt lại mật khẩu",
        "reset_body": "Mã xác nhận đặt lại mật khẩu của bạn là: {otp}\nMã này có hiệu lực trong {minutes} phút.",
        "reset_sent": "Mã đặt lại mật khẩu đã được gửi đến email",
        "poi_not_found": "Không tìm thấy quán ăn / địa điểm",
        "content_not_found": "Không có nội dung thuyết minh",
    },
}


def _normalize_locale(loc: Optional[str]) -> str:
    if not loc:
        return "vi"
    code = loc.split(",")[0].strip().lower()
    if "-" in code:
        code = code.split("-")[0]
    return code if code in _TRANSLATIONS else "vi"


def t(key: str, locale: Optional[str] = None, **kwargs) -> str:
    loc = _normalize_locale(locale)
    msg = _TRANSLATIONS.get(loc, _TRANSLATIONS["vi"]).get(key)
    if msg is None:
        msg = _TRANSLATIONS["vi"].get(key, key)
    if kwargs:
        try:
            return msg.format(**kwargs)
        except Exception:
            return msg
    return msg

