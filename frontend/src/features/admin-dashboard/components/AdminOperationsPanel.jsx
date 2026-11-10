import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { hasPermission } from "../hooks/useAdminSession.js";
import AdminInteractionDetails from "./AdminInteractionDetails.jsx";
import { makeInteractionBuckets } from "./interactionReport.js";

const nf = new Intl.NumberFormat("vi-VN");
const number = (value) => nf.format(value ?? 0);
const languageName = { vi: "Tiếng Việt", en: "Tiếng Anh", zh: "Tiếng Trung", ja: "Tiếng Nhật", ko: "Tiếng Hàn" };

function Section({ title, description, children, className = "", onTitleClick, action }) {
  return (
    <section className={`ops-panel ${className}`}>
      <div className="ops-panel-head">
        <div className="ops-panel-title-row">
          <h2>{onTitleClick ? <button type="button" className="ops-title-trigger" onClick={onTitleClick} aria-haspopup="dialog">{title}</button> : title}</h2>
          {action}
        </div>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}

function KpiCard({ title, value, hint, href, tone, user }) {
  const card = (
    <>
      <div className="ops-kpi-label">{title}</div>
      <div className="ops-kpi-value">{number(value)}</div>
      <div className="ops-kpi-note">{hint}</div>
    </>
  );
  const className = `ops-kpi ${tone ? `ops-kpi-${tone}` : ""}`;
  if (href && hasPermission(user, href.permission)) {
    return <Link className={className} to={href.path}>{card}</Link>;
  }
  return <div className={className}>{card}</div>;
}

function StatusRow({ label, count, total, tone }) {
  const pct = total ? Math.min(100, Math.round(count / total * 100)) : 0;
  return (
    <div className="ops-status-row">
      <div className="ops-status-top"><span>{label}</span><strong>{number(count)} <small>({pct}%)</small></strong></div>
      <div className="ops-track"><div className={`ops-track-fill ${tone}`} style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

function WorkRow({ title, count, extra, href, permission, user, tone = "" }) {
  return (
    <div className="ops-work-row">
      <div className="ops-work-count"><strong className={tone}>{number(count)}</strong><span>mục</span></div>
      <div className="ops-work-desc"><strong>{title}</strong><small>{extra}</small></div>
      {hasPermission(user, permission)
        ? <Link className="ops-work-link" to={href}>Xử lý ›</Link>
        : <span className="ops-work-link ops-muted">Chỉ xem</span>}
    </div>
  );
}

export default function AdminOperationsPanel({ data, days, onDaysChange, user }) {
  const [detailRange, setDetailRange] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const openAllDetails = () => { setDetailRange(null); setDetailOpen(true); };
  const openBucketDetails = (row) => {
    if (!row?.from || !row?.to) return;
    setDetailRange({ from: row.from, to: row.to });
    setDetailOpen(true);
  };
  const summary = data.summary;
  const { poi_readiness: readiness, pending_over_48h: overdue, publication_rate_percent: publicationRate } = data.operations;
  const { totals, daily, languages, top_pois: topPois } = data.interactions;
  const buckets = makeInteractionBuckets(daily, days);
  const maxViews = topPois.reduce((max, poi) => Math.max(max, poi.views || 0), 0);
  const totalLanguages = languages.reduce((sum, item) => sum + item.audio_starts, 0);
  const hasEvents = totals.views + totals.audio_starts + totals.search_selections > 0;

  return (
    <div className="ops-dashboard">
      <div className="ops-section-label">CHỈ SỐ VẬN HÀNH · TRẠNG THÁI HIỆN TẠI</div>
      <div className="ops-kpis">
        <KpiCard title="Tổng POI" value={readiness.total} hint="Tổng địa điểm đã tạo" href={{ path: "/admin/pois", permission: "poi:update" }} user={user} />
        <KpiCard title="POI công khai" value={readiness.published} hint="Du khách có thể khám phá" tone="good" href={{ path: "/admin/pois", permission: "poi:update" }} user={user} />
        <KpiCard title="Hồ sơ chờ duyệt" value={summary.registrations.pending} hint="Đăng ký chủ quán" tone="warn" href={{ path: "/admin/registrations", permission: "user:read" }} user={user} />
        <KpiCard title="Đề xuất chờ duyệt" value={summary.submissions.pending} hint="Cập nhật thông tin quán" tone="warn" href={{ path: "/admin/submissions", permission: "poi:approve" }} user={user} />
        <KpiCard title="Audio đang xử lý" value={summary.audio.processing} hint="Chờ / chạy / tạm dừng" href={{ path: "/admin/audio-tasks", permission: "poi:update" }} user={user} />
        <KpiCard title="Tác vụ audio lỗi" value={summary.audio.failed} hint="Trạng thái failed hiện tại" tone="danger" href={{ path: "/admin/audio-tasks", permission: "poi:update" }} user={user} />
      </div>

      <div className="ops-main-grid">
        <Section title="Tiến độ công khai địa điểm" description="Đếm theo trạng thái POI và điều kiện bản dịch/audio tiếng Anh.">
          <div className="ops-scoreline">
            <div><span>Tỷ lệ đang công khai</span><strong>{publicationRate == null ? "—" : `${publicationRate}%`}</strong></div>
            <span>{number(readiness.published)} / {number(readiness.total)} POI</span>
          </div>
          <StatusRow label="Đang công khai" count={readiness.published} total={readiness.total} tone="ops-green" />
          <StatusRow label="Đủ điều kiện nhưng chưa công khai" count={readiness.ready_unpublished} total={readiness.total} tone="ops-blue" />
          <StatusRow label="Chưa đủ điều kiện công khai" count={readiness.blocked_unpublished} total={readiness.total} tone="ops-amber" />
          {readiness.published_not_ready > 0 && (
            <div className="ops-alert" role="status">
              {number(readiness.published_not_ready)} POI đang công khai nhưng thiếu điều kiện EN/audio. Cần kiểm tra dữ liệu và cập nhật nội dung.
            </div>
          )}
          <div className="ops-readiness-footnote">Điều kiện công khai: tên EN, mô tả EN, audio EN đã hoàn tất và có URL.</div>
        </Section>
        <Section title="Chất lượng nội dung" description="Các vấn đề cần hoàn thiện trên toàn bộ POI; một POI có thể thiếu nhiều mục.">
          <div className="ops-quality-list">
            <div><span>Thiếu tên hoặc mô tả tiếng Anh</span><strong>{number(readiness.missing_english_content)}</strong></div>
            <div><span>Chưa có audio tiếng Anh hợp lệ</span><strong>{number(readiness.missing_english_audio)}</strong></div>
            <div><span>POI đã gắn chủ sở hữu</span><strong>{number(readiness.linked_to_owner)}</strong></div>
            <div><span>POI đầy đủ điều kiện EN + audio</span><strong>{number(readiness.ready)}</strong></div>
          </div>
          <p className="ops-hint">Chỉ số lấy từ trạng thái hiện tại của POI và `poi_localizations`, không phụ thuộc khoảng ngày.</p>
        </Section>
      </div>

      <Section title="Hàng đợi xử lý của Admin" description="Ưu tiên các việc cần xử lý. Mốc 48 giờ chỉ là cảnh báo tồn đọng, không phải SLA chính thức.">
        <div className="ops-work-list">
          <WorkRow title="Xác minh đăng ký chủ quán" count={summary.registrations.pending} extra={`${number(overdue.registrations)} hồ sơ chờ trên 48 giờ`} href="/admin/registrations" permission="user:read" user={user} tone="ops-amber-text" />
          <WorkRow title="Duyệt đề xuất thay đổi POI" count={summary.submissions.pending} extra={`${number(overdue.submissions)} đề xuất chờ trên 48 giờ`} href="/admin/submissions" permission="poi:approve" user={user} tone="ops-amber-text" />
          <WorkRow title="Kiểm tra tác vụ audio thất bại" count={summary.audio.failed} extra="Kiểm tra log và khởi chạy lại khi phù hợp" href="/admin/audio-tasks" permission="poi:update" user={user} tone="ops-red-text" />
          <WorkRow title="Hoàn thiện POI chưa công khai" count={readiness.blocked_unpublished} extra="Thiếu bản dịch hoặc audio EN theo activation gate" href="/admin/pois" permission="poi:update" user={user} />
        </div>
      </Section>

      <section className="ops-traffic-heading">
        <div><h2>Hiệu quả nội dung & trải nghiệm du khách</h2><p>Chỉ tính những sự kiện người dùng đã đồng ý ghi nhận; không phải số khách duy nhất.</p></div>
        <label className="ops-period">Khoảng ngày
          <select value={days} onChange={(e) => onDaysChange(Number(e.target.value))}>
            <option value={7}>7 ngày</option><option value={30}>30 ngày</option><option value={90}>90 ngày</option>
          </select>
        </label>
      </section>
      <div className="ops-traffic-kpis">
        <div><span>Xem chi tiết quán</span><strong>{number(totals.views)}</strong></div>
        <div><span>Chọn từ tìm kiếm</span><strong>{number(totals.search_selections)}</strong></div>
        <div><span>Bắt đầu nghe audio</span><strong>{number(totals.audio_starts)}</strong></div>
        <div><span>Nghe hoàn tất</span><strong>{number(totals.audio_completions)}</strong></div>
      </div>
      {!hasEvents && <div className="ops-empty">Chưa có lượt tương tác có sự đồng ý trong {days} ngày này. Dữ liệu 0 không đồng nghĩa hệ thống không có người dùng.</div>}
      <div className="ops-main-grid">
        <Section title="Tương tác theo kỳ" onTitleClick={openAllDetails}
          action={<button type="button" className="ops-drill-button" onClick={openAllDetails} aria-haspopup="dialog">Xem chi tiết <span aria-hidden="true">↗</span></button>}
          description={days === 7 ? "Tổng số lượt mỗi ngày · Nhấn vào cột để xem chi tiết" : "Gộp ngày để dễ quan sát · Nhấn vào cột để xem từng ngày"}>
          <div className="ops-chart" role="img" aria-label="Biểu đồ cột lượt xem và bắt đầu nghe theo thời gian">
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <BarChart data={buckets} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="#e8edf3" />
                <XAxis dataKey="period" tick={{ fontSize: 10, fill: "#64748b" }} interval={0} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} width={38} />
                <Tooltip formatter={(val, name) => [number(val), name]} />
                <Bar dataKey="views" name="Xem chi tiết" onClick={(entry, index) => openBucketDetails(entry?.payload || buckets[index])} style={{ cursor: "pointer" }} fill="#3467b0" radius={[3, 3, 0, 0]} maxBarSize={24} isAnimationActive={false} />
                <Bar dataKey="audio_starts" name="Bắt đầu nghe" onClick={(entry, index) => openBucketDetails(entry?.payload || buckets[index])} style={{ cursor: "pointer" }} fill="#11a397" radius={[3, 3, 0, 0]} maxBarSize={24} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="ops-legend"><span><i className="ops-legend-blue" /> Xem chi tiết</span><span><i className="ops-legend-teal" /> Bắt đầu nghe</span></div>
        </Section>
        <Section title="Top 5 quán được xem" description="Xếp theo lượt mở trang chi tiết, không cộng lượt nghe/audio.">
          {topPois.length ? <div className="ops-top-list">
            {topPois.map((poi, index) => (
              <div key={poi.poi_id} className="ops-top-row">
                <div className="ops-top-title"><span>{index + 1}. {poi.name}</span><strong>{number(poi.views)}</strong></div>
                <div className="ops-track"><div className="ops-track-fill ops-blue" style={{ width: `${maxViews ? poi.views / maxViews * 100 : 0}%` }} /></div>
                <small>{poi.ward || "Chưa xác định phường"}{!poi.exists ? " · Đã xóa" : ""}</small>
              </div>
            ))}
          </div> : <div className="ops-panel-empty">Chưa có lượt xem trong khoảng thời gian này.</div>}
        </Section>
      </div>
      <div className="ops-main-grid">
        <Section title="Audio theo ngôn ngữ" description="Số lượt bắt đầu phát thuyết minh; không phải số file audio đã tạo.">
          {languages.length ? <div className="ops-language-list">
            {languages.map(({ language, audio_starts }) => (
              <StatusRow key={language} label={languageName[language] || language} count={audio_starts} total={totalLanguages} tone="ops-teal" />
            ))}
          </div> : <div className="ops-panel-empty">Chưa ghi nhận lượt nghe audio.</div>}
        </Section>
        <Section title="Hiệu suất kiểm duyệt" description={`Số hồ sơ và đề xuất được xử lý trong ${days} ngày qua.`}>
          {(() => {
            const review = data.operations.review_performance;
            if (!review) return <div className="ops-panel-empty">Chưa có dữ liệu hiệu suất kiểm duyệt.</div>;
            const rows = [
              { label: "Đăng ký chủ quán", value: review.registrations },
              { label: "Đề xuất chỉnh sửa", value: review.submissions },
            ];
            return (
              <div className="ops-review-performance">
                <div className="ops-review-summary">
                  <div><span>Đã xử lý</span><strong>{number(review.processed)}</strong><small>hồ sơ và đề xuất</small></div>
                  <div><span>Thời gian xử lý TB</span><strong>{review.average_review_hours == null ? "—" : `${number(review.average_review_hours)} giờ`}</strong><small>từ khi tạo đến lúc duyệt</small></div>
                </div>
                <div className="ops-review-table" role="table" aria-label="Kết quả kiểm duyệt theo loại hồ sơ">
                  <div className="ops-review-tr ops-review-th" role="row">
                    <span role="columnheader">Loại</span><span role="columnheader">Đã duyệt</span><span role="columnheader">Từ chối</span>
                  </div>
                  {rows.map(({ label, value }) => (
                    <div className="ops-review-tr" role="row" key={label}>
                      <span role="cell">{label}</span>
                      <strong role="cell" className="ops-review-approved">{number(value.approved)}</strong>
                      <strong role="cell" className="ops-review-rejected">{number(value.rejected)}</strong>
                    </div>
                  ))}
                </div>
                <p className="ops-hint">Tính theo ngày xử lý, không tính hồ sơ còn chờ. Trung bình bỏ qua bản ghi thiếu mốc thời gian.</p>
              </div>
            );
          })()}
        </Section>
      </div>
      {detailOpen && (
        <AdminInteractionDetails
          daily={daily}
          days={days}
          range={detailRange}
          onClose={() => setDetailOpen(false)}
        />
      )}
    </div>
  );
}
