import React, { useEffect, useRef, useState } from "react";
import { FiArrowLeft, FiCheck, FiImage, FiSearch, FiUpload, FiX } from "react-icons/fi";
import { Link } from "react-router-dom";
import axiosClient from "../../../api/axiosClient.js";
import { apiErrorMessage } from "../../admin-dashboard/utils/assetUrl.js";
import ShopLocationMap from "../../maps/ShopLocationMap.jsx";
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
  {
    key: "cccd_number",
    label: "Số CCCD",
    placeholder: "Nhập 9 hoặc 12 chữ số",
    max: 12,
    autoComplete: "off",
    inputMode: "numeric",
    hint: "9 hoặc 12 chữ số.",
  },
];
const shopNameField = {
  key: "poi_name",
  label: "Tên quán",
  placeholder: "Ví dụ: Bánh mì Chảo Quận 4",
  max: 180,
  autoComplete: "organization",
};
const steps = [
  "Tài khoản và liên hệ",
  "Thông tin quán",
  "Vị trí quán",
  "Kiểm tra hồ sơ",
];
const finalStep = steps.length - 1;
const photoTypes = ["image/jpeg", "image/png", "image/webp"];

function ReviewSection({ title, fields, onEdit, disabled, children }) {
  return (
    <section className="space-y-3 rounded-lg border border-slate-200 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        <button type="button" onClick={onEdit} disabled={disabled}
          className="owner-register-back" aria-label={`Sửa ${title.toLowerCase()}`}>
          Chỉnh sửa
        </button>
      </div>
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        {fields.map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="mt-1 break-words font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      {children}
    </section>
  );
}

export default function PublicOwnerRegisterPage() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(initial);
  const [error, setError] = useState("");
  const [fieldError, setFieldError] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(null);
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState("");
  const [photoError, setPhotoError] = useState("");
  const [location, setLocation] = useState(null);
  const [lookup, setLookup] = useState(null);
  const [locationMessage, setLocationMessage] = useState("");
  const [mapCenter, setMapCenter] = useState(null);
  const addressRequest = useRef(null);
  const fileInput = useRef(null);
  const stepHeading = useRef(null);
  const focusStep = useRef(false);

  useEffect(() => () => addressRequest.current?.abort(), []);
  useEffect(() => {
    if (focusStep.current) stepHeading.current?.focus();
  }, [step]);

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

  async function findAddress(mode, path, params, onResult, onFailure) {
    addressRequest.current?.abort();
    const request = new AbortController();
    addressRequest.current = request;
    setLocationMessage("");
    setLookup(mode);
    try {
      const { data } = await axiosClient.get(path, { params, signal: request.signal });
      if (!request.signal.aborted) onResult(data);
    } catch (err) {
      if (!request.signal.aborted) onFailure(err);
    } finally {
      if (!request.signal.aborted) setLookup(null);
    }
  }

  function pinLocation(coordinates) {
    setLocation({ coordinates, ward: null });
    setMapCenter(null);
    update("poi_address", "");
    setFieldError((current) => ({ ...current, poi_location: "" }));
    const [lng, lat] = coordinates;
    return findAddress("pin", "/maps/reverse-geocode", { lat, lng }, (data) => {
      update("poi_address", data.address);
      setLocation({ coordinates, ward: data.ward });
      setLocationMessage("Đã ghim vị trí. Hãy kiểm tra lại địa chỉ.");
    }, () => setLocationMessage("Đã ghim vị trí. Hãy nhập địa chỉ của điểm đã ghim."));
  }

  function searchAddress() {
    const q = form.poi_address.trim();
    if (q.length < 3) {
      setFieldError((current) => ({ ...current, poi_address: "Nhập ít nhất 3 ký tự để tìm địa chỉ." }));
      return;
    }
    return findAddress("search", "/maps/search-address", { q }, (data) => {
      setLocation({ coordinates: data.coordinates, ward: data.ward });
      setMapCenter(data.coordinates);
      setFieldError((current) => ({ ...current, poi_location: "", poi_address: "" }));
      setLocationMessage(`Đã ghim kết quả: ${data.address}. Kiểm tra vị trí trên bản đồ.`);
    }, (err) => setLocationMessage(
      err.response?.status === 404
        ? "Không tìm thấy địa chỉ. Thử thêm tên đường, phường hoặc ghim trực tiếp."
        : "Chưa tìm được địa chỉ. Hãy thử lại hoặc ghim trực tiếp.",
    ));
  }

  function goToStep(next) {
    addressRequest.current?.abort();
    setLookup(null);
    setFieldError({});
    setError("");
    focusStep.current = true;
    setStep(next);
  }

  function validateStep() {
    const issues = {};
    if (step === 0) {
      if (!form.full_name.trim()) issues.full_name = "Hãy nhập họ và tên.";
      if (form.phone.trim().length < 8) issues.phone = "Số điện thoại cần ít nhất 8 ký tự.";
      if (!/^(?:\d{9}|\d{12})$/.test(form.cccd_number.trim()))
        issues.cccd_number = "CCCD cần gồm 9 hoặc 12 chữ số.";
      const password = form.password.trim();
      if (password.length < 12 || new TextEncoder().encode(password).length > 72)
        issues.password = "Mật khẩu cần ít nhất 12 ký tự và tối đa 72 byte.";
      if (form.password !== form.password_confirmation)
        issues.password_confirmation = "Mật khẩu nhập lại chưa khớp.";
    }
    if (step === 1 && !form.poi_name.trim()) issues.poi_name = "Hãy nhập tên quán.";
    if (step === 2) {
      if (!location) issues.poi_location = "Hãy tìm địa chỉ hoặc ghim vị trí trên bản đồ.";
      if (!form.poi_address.trim()) issues.poi_address = "Hãy nhập địa chỉ quán.";
    }
    setFieldError(issues);
    return !Object.keys(issues).length && (step !== 1 || !photoError);
  }

  async function submit(event) {
    event.preventDefault();
    if (submitting || lookup || !validateStep()) return;
    if (step < finalStep) {
      goToStep(step + 1);
      return;
    }

    setError("");
    setSubmitting(true);
    const { password_confirmation, ...payload } = form;
    payload.cccd_number = payload.cccd_number.trim();
    payload.poi_location = { type: "Point", coordinates: location.coordinates };
    payload.poi_ward = location.ward;
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
        <nav className="owner-register-progress" aria-label="Tiến trình đăng ký">
          <ol>
            {steps.map((label, index) => (
              <li key={label} aria-current={step === index ? "step" : undefined}
                data-completed={index < step}>
                <span className="owner-register-step-number" aria-hidden={index < step || undefined}>
                  {index < step ? <FiCheck /> : index + 1}
                </span>
                <span>
                  {index < step && <span className="sr-only">Bước {index + 1}, đã hoàn thành. </span>}
                  {label}
                </span>
              </li>
            ))}
          </ol>
        </nav>
        <form onSubmit={submit} aria-labelledby="registration-step-heading">
          <div className="owner-register-body">
            <h2 id="registration-step-heading" ref={stepHeading} tabIndex={-1}
              className="text-lg font-bold">
              {steps[step]}
            </h2>
            {error && (
              <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">
                {error}
              </p>
            )}
            {step === 0 && (
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {accountFields.map(renderField)}
              </div>
            )}
            {step === 1 && (
              <div className="owner-register-grid mt-4">
                <div>{renderField(shopNameField)}</div>
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
            )}
            {step === 2 && (
              <div className="mt-4 space-y-3">
                <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                  <label className="owner-register-field">
                    Địa chỉ quán
                    <input
                      required
                      maxLength={400}
                      value={form.poi_address}
                      disabled={Boolean(lookup)}
                      autoComplete="street-address"
                      placeholder="Ví dụ: Vĩnh Khánh, Khánh Hội"
                      onChange={(event) => update("poi_address", event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.nativeEvent.isComposing) {
                          event.preventDefault();
                          if (!lookup) searchAddress();
                        }
                      }}
                      aria-invalid={Boolean(fieldError.poi_address)}
                      aria-describedby="poi-address-hint"
                    />
                  </label>
                  <button type="button" disabled={Boolean(lookup)}
                    className="owner-secondary inline-flex min-h-9 items-center justify-center gap-2 disabled:opacity-60"
                    onClick={searchAddress}>
                    <FiSearch aria-hidden="true" />
                    {lookup === "search" ? "Đang tìm…" : "Tìm trên bản đồ"}
                  </button>
                </div>
                {fieldError.poi_address && (
                  <p role="alert" className="text-sm text-red-700">{fieldError.poi_address}</p>
                )}
                <p id="poi-address-hint" className="text-sm text-slate-600">
                  Tìm theo địa chỉ nếu muốn, hoặc bấm vào bản đồ để ghim vị trí quán.
                </p>
                <ShopLocationMap
                  coordinates={location?.coordinates}
                  centerOn={mapCenter}
                  onPick={pinLocation}
                />
                {fieldError.poi_location && (
                  <p role="alert" className="text-sm text-red-700">{fieldError.poi_location}</p>
                )}
                <p role="status" className="text-sm text-slate-600">
                  {lookup === "pin" ? "Đang lấy địa chỉ từ vị trí đã ghim…" : locationMessage}
                </p>
              </div>
            )}
            {step === finalStep && (
              <div className="mt-3 space-y-3">
                <p className="text-sm text-slate-600">
                  Kiểm tra thông tin trước khi xác nhận gửi hồ sơ cho quản trị viên.
                </p>
                <ReviewSection title={steps[0]} disabled={submitting} onEdit={() => goToStep(0)}
                  fields={[
                    ["Họ và tên", form.full_name],
                    ["Số điện thoại", form.phone],
                    ["Email", form.email],
                    ["Số CCCD", "•••• " + form.cccd_number.trim().slice(-4)],
                  ]} />
                <ReviewSection title={steps[1]} disabled={submitting} onEdit={() => goToStep(1)}
                  fields={[["Tên quán", form.poi_name], ["Ảnh mặt tiền", photo?.name || "Chưa tải ảnh"]]}>
                  {preview && <img src={preview} alt="Ảnh mặt tiền quán đã chọn"
                    className="max-h-32 max-w-full rounded-lg object-contain" />}
                </ReviewSection>
                <ReviewSection title={steps[2]} disabled={submitting} onEdit={() => goToStep(2)}
                  fields={[["Địa chỉ quán", form.poi_address]]}>
                  <ShopLocationMap coordinates={location?.coordinates} disabled={submitting} />
                </ReviewSection>
              </div>
            )}
          </div>
          <footer className="owner-register-footer">
            {step > 0 && (
              <button type="button" disabled={submitting} className="owner-secondary"
                onClick={() => goToStep(step - 1)}>
                Quay lại
              </button>
            )}
            <button type="submit"
              disabled={submitting || Boolean(lookup) || (step === 1 && Boolean(photoError))}
              className="admin-button-primary disabled:opacity-60">
              {step < finalStep ? "Tiếp tục" : submitting ? "Đang gửi hồ sơ…" : "Xác nhận và gửi hồ sơ"}
            </button>
          </footer>
        </form>
      </section>
    </main>
  );
}
