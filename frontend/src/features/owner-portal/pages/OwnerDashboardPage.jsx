import React, { useEffect, useState } from "react";
import {
  FiArrowRight,
  FiCoffee,
  FiFileText,
  FiMapPin,
  FiUser,
} from "react-icons/fi";
import { Link, useSearchParams } from "react-router-dom";
import axiosClient from "../../../api/axiosClient.js";
import {
  apiErrorMessage,
  assetUrl,
} from "../../admin-dashboard/utils/assetUrl.js";
import OwnerAnalyticsSection from "../components/OwnerAnalyticsSection.jsx";

const cards = [
  {
    key: "poi_count",
    label: "Quán của bạn",
    href: "/owner/poi",
    action: "Quản lý quán",
  },
  {
    key: "menu_item_count",
    label: "Món trong thực đơn",
    href: "/owner/menu",
    action: "Cập nhật thực đơn",
  },
  {
    key: "pending_submission_count",
    label: "Đề xuất đang chờ",
    href: "/owner/submissions",
    action: "Theo dõi đề xuất",
  },
  {
    key: "unread_notification_count",
    label: "Thông báo chưa đọc",
    href: "/owner/notifications",
    action: "Xem thông báo",
  },
];

export default function OwnerDashboardPage({ shops }) {
  const [searchParams] = useSearchParams();
  const demoAnalytics = import.meta.env.DEV && searchParams.get("demoAnalytics") === "1";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    axiosClient
      .get("/owner/dashboard")
      .then(({ data: result }) => {
        if (alive) setData(result);
      })
      .catch((err) => {
        if (alive) setError(apiErrorMessage(err, "Không tải được tổng quan"));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Tổng quan hoạt động
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Quản lý thông tin quán, thực đơn và các cập nhật đang được xét
            duyệt.
          </p>
        </div>
        <Link
          to="/owner/poi"
          className="rounded-lg bg-orange-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-orange-800 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2"
        >
          Quản lý quán
        </Link>
      </header>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
          <button
            type="button"
            className="ml-3 font-semibold underline"
            onClick={() => {
              setLoading(true);
              setError("");
              axiosClient
                .get("/owner/dashboard")
                .then(({ data: result }) => setData(result))
                .catch((err) =>
                  setError(apiErrorMessage(err, "Không tải được tổng quan")),
                )
                .finally(() => setLoading(false));
            }}
          >
            Thử lại
          </button>
        </div>
      )}

      <section
        aria-label="Chỉ số hoạt động"
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
      >
        {cards.map((card) => (
          <Link
            key={card.key}
            to={card.href}
            className="group rounded-xl border border-amber-100 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-orange-200 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-orange-500"
          >
            <p className="text-sm font-medium text-slate-600">{card.label}</p>
            <p className="mt-3 text-3xl font-bold tabular-nums text-slate-900">
              {loading ? "—" : (data?.summary?.[card.key] ?? 0)}
            </p>
            <span className="mt-3 inline-flex text-sm font-semibold text-orange-700">
              {card.action}
              <FiArrowRight
                aria-hidden="true"
                className="ml-1 self-center transition-transform group-hover:translate-x-1"
              />
            </span>
          </Link>
        ))}
      </section>

      {(data || demoAnalytics) && (
        <OwnerAnalyticsSection shops={data?.pois ?? []} demo={demoAnalytics} />
      )}

      <section className="rounded-xl border border-amber-100 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Quán của bạn</h2>
            <p className="mt-1 text-sm text-slate-600">
              Thông tin địa điểm đang được gắn với tài khoản.
            </p>
          </div>
          <Link
            to="/owner/poi"
            className="text-sm font-semibold text-orange-700 hover:underline"
          >
            Mở quản lý quán
          </Link>
        </div>
        {loading && (
          <p role="status" className="mt-5 text-sm text-slate-500">
            Đang tải dữ liệu…
          </p>
        )}
        {!loading && !error && !data?.pois?.length && (
          <div className="mt-5 rounded-lg border border-dashed border-amber-200 bg-amber-50/50 p-5 text-sm text-slate-600">
            Chưa có quán nào được gắn với tài khoản. Hồ sơ đăng ký cần được quản
            trị viên xác minh và liên kết với địa điểm.
          </div>
        )}
        {!loading && !!data?.pois?.length && (
          <ul className="mt-5 grid gap-3 md:grid-cols-2">
            {data.pois.map((poi) => {
              const isOpen =
                shops.find((shop) => shop.id === poi.id)?.is_open ??
                poi.is_open;
              return (
                <li
                  key={poi.id}
                  className="rounded-lg border border-slate-200 p-4"
                >
                  <div className="flex gap-4">
                    {poi.images?.[0] ? (
                      <img
                        src={assetUrl(poi.images[0])}
                        alt=""
                        className="h-16 w-16 shrink-0 rounded-lg object-cover"
                      />
                    ) : (
                      <div
                        aria-hidden="true"
                        className="grid h-16 w-16 shrink-0 place-items-center rounded-lg bg-amber-100 text-2xl"
                      >
                        <FiMapPin size={22} />
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate font-semibold text-slate-900">
                        {poi.name}
                      </h3>
                      <p className="mt-1 line-clamp-2 text-sm text-slate-600">
                        {poi.address || "Chưa có địa chỉ"}
                      </p>
                      <span
                        className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${isOpen ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-700"}`}
                      >
                        {isOpen ? "Đang mở cửa" : "Đang đóng cửa"}
                      </span>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <Link
          to="/owner/menu"
          className="rounded-xl border border-amber-100 bg-white p-4 hover:border-orange-200"
        >
          <FiCoffee size={20} aria-hidden="true" />
          <h2 className="mt-2 font-semibold text-slate-900">Thực đơn</h2>
          <p className="mt-1 text-sm text-slate-600">
            Thêm món và cập nhật giá bán.
          </p>
        </Link>
        <Link
          to="/owner/submissions"
          className="rounded-xl border border-amber-100 bg-white p-4 hover:border-orange-200"
        >
          <FiFileText size={20} aria-hidden="true" />
          <h2 className="mt-2 font-semibold text-slate-900">
            Đề xuất cập nhật
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Xem tiến độ quản trị viên xét duyệt.
          </p>
        </Link>
        <Link
          to="/owner/status"
          className="rounded-xl border border-amber-100 bg-white p-4 hover:border-orange-200"
        >
          <FiUser size={20} aria-hidden="true" />
          <h2 className="mt-2 font-semibold text-slate-900">Hồ sơ chủ quán</h2>
          <p className="mt-1 text-sm text-slate-600">
            Kiểm tra trạng thái xác minh tài khoản.
          </p>
        </Link>
      </section>
    </div>
  );
}
