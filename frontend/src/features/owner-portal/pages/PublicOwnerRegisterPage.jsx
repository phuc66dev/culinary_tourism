import React, { useEffect, useRef, useState } from "react";
import { FiArrowLeft, FiCheck, FiImage, FiUpload, FiX } from "react-icons/fi";
import { Link } from "react-router-dom";
import axiosClient from "../../../api/axiosClient.js";
import { apiErrorMessage } from "../../admin-dashboard/utils/assetUrl.js";
import "../../admin-dashboard/admin.css";
import "../owner.css";

const initial = {
  full_name: "",
  phone: "",
  email: "",
  password: "",
  password_confirmation: "",
  poi_name: "",
  poi_address: "",
  cccd_number: "",
};
const accountFields = [
  {
    key: "full_name",
    label: "Họ và tên",
    placeholder: "Ví dụ: Nguyễn Văn An",
    max: 150,
    autoComplete: "name",
  },
  {
    key: "phone",
    label: "Số điện thoại",
    placeholder: "Ví dụ: 0901234567",
    type: "tel",
    max: 30,
    autoComplete: "tel",
  },
  {
    key: "email",
    label: "Email",
    placeholder: "Ví dụ: tenquan@example.com",
    type: "email",
    max: 254,
    autoComplete: "email",
    wide: true,
  },
  {
    key: "password",
    label: "Mật khẩu",
    placeholder: "Nhập ít nhất 12 ký tự",
    type: "password",
    min: 12,
    max: 72,
    autoComplete: "new-password",
    hint: "Ít nhất 12 ký tự.",
  },
  {
    key: "password_confirmation",
    label: "Nhập lại mật khẩu",
    placeholder: "Nhập lại mật khẩu vừa tạo",
    type: "password",
    max: 72,
    autoComplete: "new-password",
  },
];
const shopFields = [
  {
    key: "poi_name",
    label: "Tên quán",
    placeholder: "Ví dụ: Bánh mì Chảo Quận 4",
    max: 180,
    autoComplete: "organization",
  },
  {
    key: "cccd_number",
    label: "Số CCCD",
    placeholder: "Nhập 9 hoặc 12 chữ số",
    max: 12,
    autoComplete: "off",
    inputMode: "numeric",
    hint: "9 hoặc 12 chữ số.",
  },
  {
    key: "poi_address",
    label: "Địa chỉ quán",
    placeholder: "Ví dụ: 123 Vĩnh Khánh, Quận 4",
    max: 400,
    autoComplete: "street-address",
    wide: true,
  },
];
const photoTypes = ["image/jpeg", "image/png", "image/webp"];

export default function PublicOwnerRegisterPage() {
  const [form, setForm] = useState(initial);
  const [error, setError] = useState("");
  const [fieldError, setFieldError] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(null);
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState("");
  const [photoError, setPhotoError] = useState("");
  const fileInput = useRef(null);

  useEffect(() => {
    if (!photo) {
      setPreview("");
      return undefined;
    }
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  function choosePhoto(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    const allowedType =
      photoTypes.includes(file.type) ||
      (!file.type && /\.(jpe?g|png|webp)$/i.test(file.name));
    if (!allowedType || !file.size || file.size > 5 * 1024 * 1024) {
      setPhoto(null);
      setPhotoError("Chọn ảnh JPEG, PNG hoặc WebP có dung lượng tối đa 5 MB.");
      return;
    }
    setPhoto(file);
    setPhotoError("");
  }

  function update(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
    setFieldError((current) => ({ ...current, [key]: "" }));
  }

  async function submit(event) {
    event.preventDefault();
    if (submitting || photoError) return;
    const next = {};
    if (!/^(?:\d{9}|\d{12})$/.test(form.cccd_number.trim()))
      next.cccd_number = "CCCD cần gồm 9 hoặc 12 chữ số.";
    if (form.password !== form.password_confirmation)
      next.password_confirmation = "Mật khẩu nhập lại chưa khớp.";
    setFieldError(next);
    if (Object.keys(next).length) return;

    setError("");
    setSubmitting(true);
    const { password_confirmation, ...payload } = form;
    payload.cccd_number = payload.cccd_number.trim();
    try {
      let response;
      if (photo) {
        const body = new FormData();
        body.append("payload", JSON.stringify(payload));
        body.append("image", photo);
        response = await axiosClient.post(
          "/admin/auth/register-owner/upload",
          body,
        );
      } else {
        response = await axiosClient.post(
          "/admin/auth/register-owner",
          payload,
        );
      }
      setCreated(response.data);
      setPhoto(null);
    } catch (err) {
      setError(apiErrorMessage(err, "Không gửi được hồ sơ đăng ký"));
    } finally {
      setSubmitting(false);
    }
  }

  function renderField({
    key,
    label,
    type = "text",
    min,
    max,
    autoComplete,
    inputMode,
    placeholder,
    hint,
    wide,
  }) {
    const message = fieldError[key] || hint;
    return (
      <label
        key={key}
        className={
          wide ? "owner-register-field sm:col-span-2" : "owner-register-field"
        }
      >
        {label}
        <input
          required
          type={type}
          minLength={min}
          maxLength={max}
          autoComplete={autoComplete}
          inputMode={inputMode}
          placeholder={placeholder}
          value={form[key]}
          onChange={(event) => update(key, event.target.value)}
          aria-invalid={!!fieldError[key]}
          aria-describedby={message ? key + "-help" : undefined}
        />
        {message && (
          <span
            id={key + "-help"}
            className={fieldError[key] ? "text-red-700" : "text-slate-500"}
          >
            {message}
          </span>
        )}
      </label>
    );
  }

  if (created)
    return (
      <main className="admin-login-shell owner-register">
        <section className="owner-register-card w-full max-w-xl p-6 sm:p-9">
          <span
            className="grid size-11 place-items-center rounded-full bg-emerald-100 text-xl text-emerald-800"
            aria-hidden="true"
          >
            <FiCheck />
          </span>
          <h1 className="mt-4 text-2xl font-bold">Đã tiếp nhận hồ sơ</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Hồ sơ của quán <strong>{form.poi_name}</strong> đang chờ xác minh.
            Đăng nhập bằng <strong>{created.email}</strong> để theo dõi.
          </p>
          <Link
            to="/admin/login"
            className="admin-button-primary mt-5 inline-flex"
          >
            Đăng nhập để theo dõi
          </Link>
        </section>
      </main>
    );

  return (
    <main className="admin-login-shell owner-register">
      <section className="owner-register-card w-full max-w-5xl">
        <header className="owner-register-header">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="admin-brand admin-brand--standalone">
              <span className="admin-brand-mark">Q4</span>
              <span>
                <strong>QUẬN 4</strong>
                <small>Cổng chủ quán</small>
              </span>
            </div>
            <Link to="/admin/login" className="owner-register-back">
              <FiArrowLeft aria-hidden="true" /> Về trang đăng nhập
            </Link>
          </div>
          <h1 className="mt-5 text-2xl font-bold">Đăng ký hồ sơ quán</h1>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Cung cấp thông tin liên hệ và địa điểm để quản trị viên xác minh hồ
            sơ.
          </p>
        </header>
        <form onSubmit={submit}>
          {error && (
            <p
              role="alert"
              className="mx-5 mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800"
            >
              {error}
            </p>
          )}
          <div className="owner-register-grid">
            <div className="space-y-5">
              <fieldset disabled={submitting}>
                <legend className="owner-register-legend">
                  Tài khoản và liên hệ
                </legend>
                <div className="grid gap-3 sm:grid-cols-2">
                  {accountFields.map(renderField)}
                </div>
              </fieldset>
              <fieldset disabled={submitting}>
                <legend className="owner-register-legend">
                  Thông tin quán
                </legend>
                <div className="grid gap-3 sm:grid-cols-2">
                  {shopFields.map(renderField)}
                </div>
              </fieldset>
            </div>
            <aside className="owner-register-photo">
              <h2 className="font-semibold">Ảnh mặt tiền quán</h2>
              <p className="mt-1 text-sm text-slate-600">
                Ảnh rõ mặt tiền hoặc bảng hiệu giúp quản trị viên xác minh địa
                điểm. Ảnh không bắt buộc.
              </p>
              <input
                ref={fileInput}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                hidden
                disabled={submitting}
                onChange={choosePhoto}
              />
              <div className="owner-register-preview">
                {preview ? (
                  <img
                    src={preview}
                    alt="Xem trước ảnh mặt tiền quán"
                    onError={() => {
                      setPhoto(null);
                      setPhotoError(
                        "Không đọc được ảnh đã chọn. Hãy chọn ảnh khác.",
                      );
                    }}
                  />
                ) : (
                  <FiImage aria-hidden="true" size={32} />
                )}
              </div>
              {photo && (
                <p className="mt-2 break-all text-xs text-slate-600">
                  {photo.name}
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="owner-secondary inline-flex items-center gap-2 bg-white"
                  disabled={submitting}
                  onClick={() => fileInput.current?.click()}
                >
                  <FiUpload aria-hidden="true" />{" "}
                  {photo ? "Đổi ảnh" : "Chọn ảnh từ máy tính"}
                </button>
                {(photo || photoError) && (
                  <button
                    type="button"
                    className="owner-secondary inline-flex items-center gap-2"
                    disabled={submitting}
                    onClick={() => {
                      setPhoto(null);
                      setPhotoError("");
                    }}
                  >
                    <FiX aria-hidden="true" /> Bỏ ảnh
                  </button>
                )}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                JPEG, PNG hoặc WebP. Tối đa 5 MB.
              </p>
              {photoError && (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {photoError}
                </p>
              )}
            </aside>
          </div>
          <footer className="owner-register-footer">
            <button
              type="submit"
              disabled={submitting || !!photoError}
              className="admin-button-primary disabled:opacity-60"
            >
              {submitting ? "Đang gửi hồ sơ…" : "Gửi hồ sơ đăng ký"}
            </button>
          </footer>
        </form>
      </section>
    </main>
  );
}
