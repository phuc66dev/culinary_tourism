import React, { useEffect, useState } from 'react';
import { FiArrowDown, FiArrowUp, FiSearch } from 'react-icons/fi';
import { LuChevronsUpDown } from 'react-icons/lu';
import axiosClient from '../../../api/axiosClient.js';
import { apiErrorMessage } from '../utils/assetUrl.js';

const filters = [
  ['pending', 'Chờ duyệt'],
  ['approved', 'Đã duyệt'],
  ['rejected', 'Đã từ chối'],
  ['', 'Tất cả'],
];
const labels = {
  ...Object.fromEntries(filters),
  processing: 'Đang xử lý',
  review_error: 'Cần khôi phục',
};
const colors = {
  pending: 'bg-amber-100 text-amber-900',
  approved: 'bg-green-100 text-green-900',
  rejected: 'bg-red-100 text-red-900',
};

export function ReviewStatus({ status }) {
  return (
    <span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${colors[status] ?? 'bg-slate-100 text-slate-700'}`}>
      {labels[status] || status || '—'}
    </span>
  );
}

export default function ReviewQueue({ endpoint, title, searchPlaceholder, columns, renderDetail }) {
  const [status, setStatus] = useState('pending');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [limit, setLimit] = useState(15);
  const [sort, setSort] = useState({ key: 'created_at', order: 'desc' });
  const [result, setResult] = useState(null);
  const [version, setVersion] = useState(0);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState('');
  const requestKey = JSON.stringify([status, query, page, limit, sort, version]);
  const current = result?.key === requestKey ? result : null;
  const data = current?.data;
  const pageCount = Math.max(1, Math.ceil((data?.total ?? 0) / limit));
  const loading = !current;
  const reload = () => setVersion((value) => value + 1);

  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    const controller = new AbortController();
    axiosClient.get(endpoint, {
      params: { status: status || undefined, q: query || undefined, limit, skip: page * limit,
        sort_by: sort.key, order: sort.order },
      signal: controller.signal,
    }).then(({ data: response }) => {
      if (controller.signal.aborted) return;
      const lastPage = Math.max(0, Math.ceil(response.total / limit) - 1);
      if (page > lastPage) setPage(lastPage);
      else setResult({ key: requestKey, data: response });
    }).catch((error) => {
      if (!controller.signal.aborted) {
        setResult({ key: requestKey, error: apiErrorMessage(error, 'Không tải được danh sách.') });
      }
    });
    return () => controller.abort();
  }, [endpoint, requestKey, status, query, limit, page, sort]);

  function sortBy(key) {
    setSort((previous) => ({
      key,
      order: previous.key === key && previous.order === 'asc' ? 'desc' : 'asc',
    }));
    setPage(0);
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white" aria-label={title}>
        <header className="space-y-4 p-4 sm:p-5">
          <h2 className="text-xl font-bold text-slate-900">{title}</h2>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2" aria-label="Lọc theo trạng thái" role="group">
              {filters.map(([value, label]) => (
                <button key={value} type="button" aria-pressed={status === value}
                  onClick={() => { setStatus(value); setPage(0); }}
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold ${status === value ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}>
                  {label}{value && result?.data?.counts?.[value] !== undefined ? ` (${result.data.counts[value]})` : ''}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="relative">
                <FiSearch aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input type="search" aria-label="Tìm kiếm" maxLength={100} placeholder={searchPlaceholder}
                  value={search} onChange={(event) => setSearch(event.target.value)}
                  className="w-64 max-w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm" />
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                Mỗi trang
                <select value={limit} onChange={(event) => { setLimit(Number(event.target.value)); setPage(0); }}
                  className="rounded-lg border border-slate-300 bg-white px-2 py-2">
                  {[15, 25, 50, 100].map((size) => <option key={size} value={size}>{size}</option>)}
                </select>
              </label>
            </div>
          </div>
          {message && <p role="status" className="rounded-lg bg-green-50 px-3 py-2 text-sm text-green-800">{message}</p>}
          {current?.error && (
            <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">
              {current.error}{' '}
              <button type="button" className="font-semibold underline" onClick={reload}>Thử lại</button>
            </div>
          )}
        </header>
        <div className="overflow-x-auto" aria-busy={loading}>
          <table className="w-full text-left text-sm">
            <thead className="border-y border-slate-200 bg-slate-50 text-slate-700">
              <tr>
                {columns.map(({ key, label, sortable = true }) => {
                  const active = sort.key === key;
                  const Icon = !active ? LuChevronsUpDown : sort.order === 'asc' ? FiArrowUp : FiArrowDown;
                  return (
                    <th key={key} scope="col" className="whitespace-nowrap px-4 py-3"
                      aria-sort={active ? (sort.order === 'asc' ? 'ascending' : 'descending') : undefined}>
                      {sortable ? (
                        <button type="button" className="inline-flex items-center gap-1.5 hover:text-teal-800" onClick={() => sortBy(key)}>
                          {label}<Icon aria-hidden="true" />
                        </button>
                      ) : label}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((item) => (
                <tr key={item.id} onClick={() => setSelected(item)} className="cursor-pointer hover:bg-slate-50">
                  {columns.map(({ key, render }, index) => (
                    <td key={key} className="px-4 py-3 align-top">
                      {index === 0 ? (
                        <button type="button" aria-haspopup="dialog" className="text-left font-semibold text-teal-800 hover:underline">
                          {render(item)}
                        </button>
                      ) : render(item)}
                    </td>
                  ))}
                </tr>
              ))}
              {!data?.items.length && (
                <tr><td colSpan={columns.length} className="p-6 text-center text-slate-500">
                  {loading ? <span role="status">Đang tải danh sách…</span> : current?.error || 'Không có kết quả phù hợp.'}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
        {data && (
          <nav aria-label="Phân trang" className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-sm">
            <span className="text-slate-600">
              {data.total ? `${page * limit + 1}–${page * limit + data.items.length} / ${data.total}` : '0 kết quả'}
              {' · '}Trang {page + 1}/{pageCount}
            </span>
            <div className="flex gap-2">
              <button type="button" disabled={page === 0} onClick={() => setPage((value) => value - 1)}
                className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40">Trước</button>
              <button type="button" disabled={page + 1 >= pageCount} onClick={() => setPage((value) => value + 1)}
                className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40">Sau</button>
            </div>
          </nav>
        )}
      </section>
      {selected && renderDetail(selected, {
        close: () => setSelected(null),
        reload,
        reviewed: (notice) => { setMessage(notice); setSelected(null); reload(); },
      })}
    </div>
  );
}
