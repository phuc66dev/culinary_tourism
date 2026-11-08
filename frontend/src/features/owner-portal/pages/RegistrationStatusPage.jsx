import { FiAlertCircle, FiCheck, FiCircle, FiClock } from "react-icons/fi";
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axiosClient from "../../../api/axiosClient.js";
import { apiErrorMessage } from "../../admin-dashboard/utils/assetUrl.js";

const states = {
  not_submitted: {
    title: "Chưa gửi hồ sơ",
    tone: "bg-slate-100 text-slate-700",
    Icon: FiCircle,
    description: "Gửi hồ sơ đăng ký để bắt đầu xác minh tài khoản chủ quán.",
  },
  pending: {
    title: "Đang chờ xét duyệt",
    tone: "bg-amber-100 text-amber-900",
    Icon: FiClock,
    description: "Quản trị viên đang kiểm tra thông tin đăng ký của bạn.",
  },
  pending_verification: {
    title: "Đang chờ xét duyệt",
    tone: "bg-amber-100 text-amber-900",
    Icon: FiClock,
    description: "Quản trị viên đang kiểm tra thông tin đăng ký của bạn.",
  },
  approved: {
    title: "Đã được xác minh",
    tone: "bg-emerald-100 text-emerald-900",
    Icon: FiCheck,
    description: "Tài khoản chủ quán đã được xác minh.",
  },
  rejected: {
    title: "Cần bổ sung hồ sơ",
    tone: "bg-red-100 text-red-900",
    Icon: FiAlertCircle,
    description:
      "Hồ sơ chưa được chấp thuận. Xem ghi chú để biết nội dung cần xử lý.",
  },
};

function dateLabel(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString("vi-VN", { dateStyle: "medium", timeStyle: "short" });
}

export default function RegistrationStatusPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    axiosClient
      .get("/owner/registration-status")
      .then(({ data: result }) => {
        if (alive) setData(result);
      })
      .catch((err) => {
        if (alive)
          setError(apiErrorMessage(err, "Không tải được trạng thái hồ sơ"));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  if (loading)
    return (
      <div
        role="status"
        className="rounded-xl border bg-white p-6 text-sm text-slate-600"
      >
        Đang tải trạng thái hồ sơ…
      </div>
    );
  if (error)
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-200 bg-white p-6 text-sm text-red-800"
      >
        {error}
        <button
          onClick={() => window.location.reload()}
          className="ml-2 font-semibold underline"
        >
          Tải lại
        </button>
      </div>
    );

  const status = data?.status || "not_submitted";
  const current = states[status] || states.pending;
  const steps = [
    { label: "Gửi hồ sơ", done: status !== "not_submitted" },
    {
      label: "Quản trị viên xác minh",
      done:
        ["approved", "rejected"].includes(status) ||
        data?.is_poi_owner_verified,
    },
    {
      label: "Kích hoạt chức năng chủ quán",
      done: Boolean(data?.is_poi_owner_verified),
    },
  ];

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-orange-700">
          Tài khoản của bạn
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900 sm:text-3xl">
          Trạng thái hồ sơ
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Theo dõi tiến trình xác minh và phản hồi từ ban quản trị.
        </p>
      </header>
      <section className="rounded-2xl border border-amber-100 bg-white p-5 shadow-sm sm:p-7">
        <div className="flex items-start gap-4">
          <span
            className={
              "grid h-12 w-12 shrink-0 place-items-center rounded-full text-xl font-bold " +
              current.tone
            }
            aria-hidden="true"
          >
            <current.Icon aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <span
              className={
                "inline-flex rounded-full px-3 py-1 text-xs font-bold " +
                current.tone
              }
            >
              {current.title}
            </span>
            <h2 className="mt-3 text-lg font-bold text-slate-900">
              {data?.poi_name || "Hồ sơ chủ quán"}
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              {current.description}
            </p>
          </div>
        </div>
        <ol className="mt-7 grid gap-3 sm:grid-cols-3">
          {steps.map((step, index) => (
            <li
              key={step.label}
              className="flex items-start gap-3 rounded-lg bg-slate-50 p-3"
            >
              <span
                className={
                  "grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold " +
                  (step.done
                    ? "bg-emerald-700 text-white"
                    : "bg-white text-slate-500 ring-1 ring-slate-300")
                }
              >
                {step.done ? <FiCheck aria-hidden="true" /> : index + 1}
              </span>
              <span className="pt-1 text-sm font-medium text-slate-700">
                {step.label}
              </span>
            </li>
          ))}
        </ol>
        <dl className="mt-6 grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Ngày gửi hồ sơ
            </dt>
            <dd className="mt-1 text-sm text-slate-800">
              {dateLabel(data?.created_at)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Ngày xét duyệt
            </dt>
            <dd className="mt-1 text-sm text-slate-800">
              {dateLabel(data?.reviewed_at)}
            </dd>
          </div>
        </dl>
        {data?.admin_note && (
          <div className="mt-5 rounded-lg border-l-4 border-orange-500 bg-amber-50 p-4">
            <h3 className="text-sm font-bold text-slate-900">
              Phản hồi từ quản trị viên
            </h3>
            <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">
              {data.admin_note}
            </p>
          </div>
        )}
        {status === "not_submitted" && (
          <Link
            to="/register/owner"
            className="mt-5 inline-flex rounded-lg bg-orange-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-800"
          >
            Đăng ký hồ sơ chủ quán
          </Link>
        )}
        {status === "rejected" && (
          <p className="mt-5 text-sm text-slate-600">
            Nếu cần gửi hồ sơ mới, hãy liên hệ ban quản trị để được hướng dẫn.
          </p>
        )}
      </section>
    </div>
  );
}
