import React, { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import axiosClient from "../../../api/axiosClient.js";
import { apiErrorMessage } from "../../admin-dashboard/utils/assetUrl.js";
import { createDemoAnalytics } from "./demoAnalytics.js";

const numberFormat = new Intl.NumberFormat("vi-VN");
const count = (value) => numberFormat.format(value);
const dayLabel = (date) => `${date.slice(8, 10)}/${date.slice(5, 7)}`;
const languageNames = {
  vi: "Tiếng Việt",
  en: "Tiếng Anh",
  zh: "Tiếng Trung",
  ja: "Tiếng Nhật",
  ko: "Tiếng Hàn",
};
const metrics = {
  views: { name: "Lượt xem chi tiết", color: "#9a3412" },
  search_selections: { name: "Lượt chọn từ tìm kiếm", color: "#1d4ed8" },
  audio_starts: { name: "Lượt bắt đầu nghe", color: "#9a3412" },
  audio_completions: { name: "Lượt nghe hết", color: "#047857" },
  listen_seconds: { name: "Tổng thời lượng nghe", color: "#0f766e" },
};

function duration(seconds) {
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const parts = [
    hours > 0 && `${count(hours)} giờ`,
    minutes > 0 && `${minutes} phút`,
    total % 60 > 0 && `${total % 60} giây`,
  ].filter(Boolean);
  return parts.join(" ") || "0 giây";
}

function ChartPanel({ title, description, children }) {
  return (
    <div className="min-w-0 rounded-xl border border-amber-100 bg-white p-4 sm:p-5">
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-sm text-slate-600">{description}</p>
      <div className="mt-4 h-64 min-w-0">{children}</div>
    </div>
  );
}

function TrendChart({ daily, series }) {
  return (
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <LineChart data={daily} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#e2e8f0" />
        <XAxis dataKey="date" tickFormatter={dayLabel} minTickGap={24} tick={{ fontSize: 12 }} />
        <YAxis allowDecimals={false} width={52} tickFormatter={count} tick={{ fontSize: 12 }} />
        <Tooltip labelFormatter={dayLabel} formatter={count} />
        <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
        {series.map((key, index) => (
          <Line
            key={key}
            dataKey={key}
            name={metrics[key].name}
            stroke={metrics[key].color}
            strokeWidth={2}
            strokeDasharray={index === 1 ? "5 4" : undefined}
            dot={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function AnalyticsCharts({ daily, languages }) {
  const languageData = languages.map((entry) => ({
    ...entry,
    name: languageNames[entry.language] ?? entry.language,
  }));
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <ChartPanel title="Khách tìm đến quán" description="Lượt mở chi tiết và lượt chọn quán từ kết quả tìm kiếm theo ngày.">
        <TrendChart daily={daily} series={["views", "search_selections"]} />
      </ChartPanel>
      <ChartPanel title="Lượt nghe theo ngày" description="So sánh lượt bắt đầu nghe với lượt phát đến cuối.">
        <TrendChart daily={daily} series={["audio_starts", "audio_completions"]} />
      </ChartPanel>
      <ChartPanel title="Thời lượng nghe theo ngày" description="Cộng thời gian phát thực tế của các lượt đã kết thúc trong ngày.">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <BarChart data={daily} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" tickFormatter={dayLabel} minTickGap={24} tick={{ fontSize: 12 }} />
            <YAxis width={64} tickFormatter={duration} tick={{ fontSize: 11 }} />
            <Tooltip labelFormatter={dayLabel} formatter={duration} />
            <Bar
              dataKey="listen_seconds"
              name={metrics.listen_seconds.name}
              fill={metrics.listen_seconds.color}
              radius={[4, 4, 0, 0]}
              maxBarSize={24}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>
      <ChartPanel title="Ngôn ngữ được chọn" description="Số lượt bắt đầu nghe theo ngôn ngữ bản thuyết minh.">
        {languageData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart data={languageData} layout="vertical" margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid horizontal={false} stroke="#e2e8f0" />
              <XAxis type="number" allowDecimals={false} tickFormatter={count} tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="name" width={84} tick={{ fontSize: 12 }} />
              <Tooltip formatter={count} />
              <Bar
                dataKey="audio_starts"
                name={metrics.audio_starts.name}
                fill="#1d4ed8"
                radius={[0, 4, 4, 0]}
                maxBarSize={24}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="grid h-full place-items-center rounded-lg bg-slate-50 px-4 text-center text-sm text-slate-600">
            Chưa ghi nhận lượt bắt đầu nghe trong kỳ này.
          </p>
        )}
      </ChartPanel>
    </div>
  );
}

function DailyTable({ daily }) {
  return (
    <details className="rounded-lg border border-slate-200 bg-white p-4">
      <summary className="cursor-pointer text-sm font-semibold text-orange-800">
        Xem số liệu từng ngày
      </summary>
      <div className="mt-3 max-h-80 overflow-auto">
        <table className="w-full text-left text-sm text-slate-700">
          <thead className="sticky top-0 bg-slate-50">
            <tr>
              <th scope="col" className="px-3 py-2">Ngày</th>
              {Object.entries(metrics).map(([key, metric]) => (
                <th key={key} scope="col" className="px-3 py-2 text-right">{metric.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...daily].reverse().map((day) => (
              <tr key={day.date} className="border-t border-slate-100">
                <th scope="row" className="whitespace-nowrap px-3 py-2 font-medium">{dayLabel(day.date)}</th>
                {Object.keys(metrics).map((key) => (
                  <td key={key} className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                    {key === "listen_seconds" ? duration(day[key]) : count(day[key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export default function OwnerAnalyticsSection({ shops, demo }) {
  const [selectedPoi, setSelectedPoi] = useState("");
  const [days, setDays] = useState(30);
  const [request, setRequest] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const poiId = shops.find(({ id }) => id === selectedPoi)?.id ?? shops[0]?.id;
  const requestKey = `${poiId}:${days}:${attempt}`;
  const currentRequest = !demo && request?.key === requestKey ? request : null;
  const stats = demo ? createDemoAnalytics(days) : currentRequest?.data;
  const hasActivity = stats && Object.values(stats.totals).some((value) => value > 0);

  useEffect(() => {
    if (demo || !poiId) return;
    const controller = new AbortController();
    axiosClient
      .get("/owner/analytics", { params: { poi_id: poiId, days }, signal: controller.signal })
      .then(({ data }) => {
        if (!controller.signal.aborted) setRequest({ key: requestKey, data });
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setRequest({ key: requestKey, error: apiErrorMessage(error, "Không tải được thống kê.") });
        }
      });
    return () => controller.abort();
  }, [demo, poiId, days, requestKey]);

  return (
    <section aria-labelledby="owner-analytics-title" className="space-y-4 rounded-xl border border-amber-100 bg-amber-50/40 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="owner-analytics-title" className="text-lg font-bold text-slate-900">Thống kê tương tác</h2>
          <p className="mt-1 text-sm text-slate-600">Theo dõi cách khách khám phá quán và nghe thuyết minh.</p>
        </div>
        {(demo || poiId) && (
          <div className="flex min-w-0 flex-wrap gap-3">
            {!demo && shops.length > 1 && (
              <label className="flex min-w-0 flex-col gap-1 text-xs font-medium text-slate-700">
                Quán
                <select value={poiId} onChange={(event) => setSelectedPoi(event.target.value)} className="w-48 max-w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:ring-2 focus:ring-orange-500">
                  {shops.map((shop) => <option key={shop.id} value={shop.id}>{shop.name}</option>)}
                </select>
              </label>
            )}
            <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
              Khoảng thời gian
              <select value={days} onChange={(event) => setDays(Number(event.target.value))} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:ring-2 focus:ring-orange-500">
                {[7, 30, 90].map((value) => <option key={value} value={value}>{value} ngày gần nhất</option>)}
              </select>
            </label>
          </div>
        )}
      </div>
      {!demo && !poiId && <p className="text-sm text-slate-600">Thống kê sẽ xuất hiện khi tài khoản được liên kết với quán.</p>}
      {!demo && poiId && !currentRequest && <p role="status" className="text-sm text-slate-600">Đang tải thống kê…</p>}
      {currentRequest?.error && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {currentRequest.error}{" "}
          <button type="button" className="font-semibold underline" onClick={() => setAttempt((value) => value + 1)}>Thử lại</button>
        </p>
      )}
      {stats && (
        <>
          <p className="text-xs text-slate-600">
            {demo ? (
              <strong>Dữ liệu mẫu để xem thử · Theo giờ Việt Nam (UTC+7)</strong>
            ) : (
              "Theo giờ Việt Nam (UTC+7) · Chỉ tính hoạt động của khách đã đồng ý chia sẻ thống kê."
            )}
          </p>
          <dl className="grid grid-cols-2 gap-3 lg:grid-cols-3 2xl:grid-cols-5">
            {Object.entries(metrics).map(([key, metric]) => (
              <div key={key} className="rounded-lg border border-amber-100 bg-white p-3 sm:p-4">
                <dt className="text-sm text-slate-600">{metric.name}</dt>
                <dd className="mt-1 text-xl font-bold tabular-nums text-slate-900">
                  {key === "listen_seconds" ? duration(stats.totals[key]) : count(stats.totals[key])}
                </dd>
              </div>
            ))}
          </dl>
          {hasActivity ? (
            <>
              <AnalyticsCharts daily={stats.daily} languages={stats.languages} />
              <DailyTable daily={stats.daily} />
            </>
          ) : (
            <p className="rounded-lg border border-dashed border-amber-200 bg-white p-5 text-sm text-slate-600">
              Chưa ghi nhận tương tác cho quán trong khoảng thời gian này.
            </p>
          )}
        </>
      )}
    </section>
  );
}
