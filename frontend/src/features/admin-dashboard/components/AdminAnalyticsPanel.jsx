import React from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis, Legend,
} from "recharts";
import AdminIcon from "./AdminIcon.jsx";

const number = new Intl.NumberFormat("vi-VN");
const formatNumber = (value) => number.format(value ?? 0);
const shortDate = (date) => `${date.slice(8, 10)}/${date.slice(5, 7)}`;
const langName = { vi: "Tiếng Việt", en: "Tiếng Anh", zh: "Tiếng Trung", ja: "Tiếng Nhật", ko: "Tiếng Hàn" };
const SERIES = {
  views: { name: "Xem chi tiết", color: "#245cb6" },
  search_selections: { name: "Chọn từ tìm kiếm", color: "#12a085" },
  audio_starts: { name: "Bắt đầu nghe", color: "#245cb6" },
  audio_completions: { name: "Nghe hoàn tất", color: "#12a085" },
};

function Panel({ title, description, children }) {
  return (
    <section className="admin-chart-panel">
      <div className="admin-chart-heading">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}

function TrendChart({ daily, series, label }) {
  return (
    <div className="admin-chart-plot" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart data={daily} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="#e9edf3" />
          <XAxis dataKey="date" tickFormatter={shortDate} minTickGap={26} tick={{ fontSize: 11, fill: "#69798b" }} />
          <YAxis allowDecimals={false} width={42} tickFormatter={formatNumber} tick={{ fontSize: 11, fill: "#69798b" }} />
          <Tooltip labelFormatter={shortDate} formatter={(value) => formatNumber(value)} />
          <Legend iconType="plainline" wrapperStyle={{ fontSize: 11 }} />
          {series.map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={SERIES[key].name}
              stroke={SERIES[key].color}
              strokeWidth={2.3}
              strokeDasharray={index === 1 ? "6 4" : undefined}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function Statistic({ label, value, detail }) {
  return (
    <div className="admin-statistic">
      <p>{label}</p>
      <strong>{formatNumber(value)}</strong>
      <small>{detail}</small>
    </div>
  );
}

function Breakdown({ title, items }) {
  return (
    <div className="admin-breakdown">
      <h3>{title}</h3>
      {items.map(({ label, value, color }) => (
        <div className="admin-breakdown-row" key={label}>
          <span className="admin-breakdown-label"><i className={`admin-breakdown-dot ${color}`} />{label}</span>
          <strong>{formatNumber(value)}</strong>
        </div>
      ))}
    </div>
  );
}

export default function AdminAnalyticsPanel({ data, days, onDaysChange }) {
  const { summary, interactions } = data;
  const { totals, daily, languages, top_pois: topPois } = interactions;
  const namedLanguages = languages.map((item) => ({
    ...item,
    name: langName[item.language] ?? item.language,
  }));
  const activity = totals.views + totals.search_selections + totals.audio_starts;

  return (
    <div className="admin-analytics">
      <div className="admin-analytics-toolbar">
        <div>
          <h2>Thống kê tương tác</h2>
          <p>Số liệu toàn hệ thống theo ngày (giờ Việt Nam).</p>
        </div>
        <label className="admin-range-label">
          Khoảng thời gian
          <select value={days} onChange={(event) => onDaysChange(Number(event.target.value))}>
            <option value={7}>7 ngày gần nhất</option>
            <option value={30}>30 ngày gần nhất</option>
            <option value={90}>90 ngày gần nhất</option>
          </select>
        </label>
      </div>

      <div className="admin-analytics-kpis">
        <Statistic label="Lượt xem quán" value={totals.views} detail="Mở trang chi tiết POI" />
        <Statistic label="Lượt chọn tìm kiếm" value={totals.search_selections} detail="Chọn quán từ tìm kiếm" />
        <Statistic label="Lượt bắt đầu nghe" value={totals.audio_starts} detail="Khởi chạy thuyết minh" />
        <Statistic label="Lượt nghe hoàn tất" value={totals.audio_completions} detail="Sự kiện phát hoàn tất" />
      </div>

      {!activity && (
        <p className="admin-analytics-notice" role="status">
          Chưa có lượt tương tác được ghi nhận trong {days} ngày gần nhất. Biểu đồ sẽ có dữ liệu khi khách đồng ý chia sẻ thống kê và sử dụng ứng dụng.
        </p>
      )}

      <div className="admin-analytics-charts">
        <Panel title="Khách khám phá quán" description="Lượt xem chi tiết và lượt chọn từ tìm kiếm.">
          <TrendChart daily={daily} series={["views", "search_selections"]} label={`Biểu đồ lượt xem và lượt chọn tìm kiếm trong ${days} ngày`} />
        </Panel>
        <Panel title="Khách nghe thuyết minh" description="Lượt bắt đầu nghe so với lượt nghe hoàn tất.">
          <TrendChart daily={daily} series={["audio_starts", "audio_completions"]} label={`Biểu đồ bắt đầu nghe và nghe hoàn tất trong ${days} ngày`} />
        </Panel>
      </div>

      <div className="admin-analytics-lower">
        <Panel title="Quán được quan tâm nhiều" description="Xếp hạng theo lượt mở trang chi tiết trong kỳ.">
          {topPois.length ? (
            <div className="admin-top-pois">
              {topPois.map((poi, index) => (
                <div className="admin-top-poi" key={poi.poi_id}>
                  <span className="admin-top-poi-index">{index + 1}</span>
                  <div className="admin-top-poi-info">
                    <strong>{poi.name}</strong>
                    <small>{poi.ward || "Chưa có phường"}</small>
                  </div>
                  <span className="admin-top-poi-value">{formatNumber(poi.views)} <small>lượt</small></span>
                </div>
              ))}
            </div>
          ) : <p className="admin-analytics-empty">Chưa có lượt xem POI trong kỳ này.</p>}
        </Panel>
        <Panel title="Ngôn ngữ thuyết minh" description="Số lượt bắt đầu nghe theo từng ngôn ngữ.">
          {namedLanguages.length ? (
            <div className="admin-chart-plot" role="img" aria-label="Biểu đồ lượt nghe theo ngôn ngữ">
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <BarChart data={namedLanguages} layout="vertical" margin={{ top: 8, right: 14, left: 0, bottom: 0 }}>
                  <CartesianGrid horizontal={false} stroke="#e9edf3" />
                  <XAxis type="number" allowDecimals={false} tickFormatter={formatNumber} tick={{ fontSize: 11, fill: "#69798b" }} />
                  <YAxis type="category" dataKey="name" width={82} tick={{ fontSize: 11, fill: "#69798b" }} />
                  <Tooltip formatter={formatNumber} />
                  <Bar dataKey="audio_starts" name="Lượt bắt đầu nghe" fill="#245cb6" radius={[0, 4, 4, 0]} maxBarSize={25} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="admin-analytics-empty">Chưa ghi nhận lượt nghe audio trong kỳ này.</p>}
        </Panel>
      </div>

      <section className="admin-dashboard-section">
        <div className="admin-section-header">
          <h2>Tình trạng vận hành</h2>
          <p>Số lượng hiện tại (không theo khoảng ngày) · {formatNumber(summary.users.total)} tài khoản, gồm {formatNumber(summary.users.owners)} chủ quán.</p>
        </div>
        <div className="admin-operations-grid">
          <Breakdown title="Điểm tham quan" items={[
            { label: "Đang công khai", value: summary.pois.active, color: "green" },
            { label: "Chưa công khai", value: summary.pois.inactive, color: "gray" },
          ]} />
          <Breakdown title="Đăng ký chủ quán" items={[
            { label: "Chờ duyệt", value: summary.registrations.pending, color: "amber" },
            { label: "Đã duyệt", value: summary.registrations.approved, color: "green" },
            { label: "Từ chối", value: summary.registrations.rejected, color: "red" },
          ]} />
          <Breakdown title="Đề xuất chỉnh sửa" items={[
            { label: "Chờ duyệt", value: summary.submissions.pending, color: "amber" },
            { label: "Đã duyệt", value: summary.submissions.approved, color: "green" },
            { label: "Từ chối", value: summary.submissions.rejected, color: "red" },
          ]} />
          <Breakdown title="Tác vụ audio" items={[
            { label: "Đang xử lý / tạm dừng", value: summary.audio.processing, color: "blue" },
            { label: "Hoàn tất", value: summary.audio.completed, color: "green" },
            { label: "Thất bại", value: summary.audio.failed, color: "red" },
            { label: "Đã hủy", value: summary.audio.cancelled, color: "gray" },
          ]} />
        </div>
      </section>
      <div className="admin-analytics-footnote">
        <AdminIcon name="alert" size={14} />
        Tương tác chỉ gồm sự kiện của khách đã đồng ý chia sẻ thống kê. Dữ liệu sự kiện được lưu tối đa {data.retention_days} ngày; các tổng số vận hành được tính từ dữ liệu hiện tại.
      </div>
    </div>
  );
}
