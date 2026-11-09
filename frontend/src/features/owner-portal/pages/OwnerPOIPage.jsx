import React, { useEffect, useId, useRef, useState } from "react";
import axiosClient from "../../../api/axiosClient.js";
import {
  apiErrorMessage,
  assetUrl,
} from "../../admin-dashboard/utils/assetUrl.js";
import toast from "react-hot-toast";
import { FiLoader, FiMapPin, FiPlus } from "react-icons/fi";
import { LuSparkles } from "react-icons/lu";
import OwnerMenuTable from "../components/OwnerMenuTable.jsx";
import MenuImagePicker from '../components/MenuImagePicker.jsx';
import OwnerDialog from "../components/OwnerDialog.jsx";
import ProposalMediaFields from "../components/ProposalMediaFields.jsx";

const input =
  "mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100";
const blankMenu = { name: "", price_vnd: "", images: [], tags: "" };
const blankProposal = {
  name: "",
  address: "",
  ward: "",
  category: "",
  original_description: "",
  coordinates: null,
};

function parseTags(value) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function coordinatesFromPoi(poi) {
  const coordinates = poi.location?.coordinates;
  if (!Array.isArray(coordinates) || coordinates.length < 2) return null;
  const [rawLongitude, rawLatitude] = coordinates;
  if (rawLongitude == null || rawLatitude == null
    || String(rawLongitude).trim() === "" || String(rawLatitude).trim() === "") return null;
  const longitude = Number(rawLongitude);
  const latitude = Number(rawLatitude);
  return Math.abs(longitude) <= 180 && Math.abs(latitude) <= 90
    ? [longitude, latitude]
    : null;
}

function proposalFromPoi(poi) {
  return {
    name: poi.name || "",
    address: poi.address || "",
    ward: poi.ward || "",
    category: poi.category || "",
    original_description: poi.original_description || "",
    coordinates: coordinatesFromPoi(poi),
  };
}

export default function OwnerPOIPage({
  mode = "info",
  selected,
  loading,
  shopError,
  onRetry,
}) {
  const [menuItems, setMenuItems] = useState([]);
  const [menuLoading, setMenuLoading] = useState(false);
  const [error, setError] = useState("");
  const isMenu = mode === "menu";
  const [dialog, setDialog] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [busy, setBusy] = useState(false);
  const [editingMenuId, setEditingMenuId] = useState("");
  const [menuForm, setMenuForm] = useState(blankMenu);
  const [menuError, setMenuError] = useState("");
  const menuFormId = useId();
  const [proposal, setProposal] = useState(blankProposal);
  const [proposalPhoto, setProposalPhoto] = useState(null);
  const [locationBusy, setLocationBusy] = useState(false);
  const [proposalBusy, setProposalBusy] = useState(false);
  const [generatingDescription, setGeneratingDescription] = useState(false);
  const [descriptionError, setDescriptionError] = useState("");
  const [ownerHighlight, setOwnerHighlight] = useState("");
  const [contextQuestion, setContextQuestion] = useState("");
  const lastGeneration = useRef(null);
  const highlightField = useRef(null);
  const descriptionId = useId();
  const highlightId = useId();

  useEffect(() => {
    if (!selected?.id) {
      setMenuItems([]);
      return undefined;
    }
    if (!isMenu) return undefined;
    setError("");
    let alive = true;
    setMenuItems([]);
    setMenuLoading(true);
    axiosClient
      .get("/owner/menu-items", { params: { poi_id: selected.id } })
      .then(({ data }) => {
        if (alive) setMenuItems(data.items || []);
      })
      .catch((err) => {
        if (alive) setError(apiErrorMessage(err, "Không tải được thực đơn"));
      })
      .finally(() => {
        if (alive) setMenuLoading(false);
      });
    setProposal(proposalFromPoi(selected));

    return () => {
      alive = false;
    };
  }, [selected?.id, isMenu]);

  function startEdit(item) {
    setMenuError("");
    const imageUrls = item.image_urls ?? (item.image_url ? [item.image_url] : []);
    setEditingMenuId(item.id);
    setMenuForm({
      name: item.name || "",
      price_vnd: String(item.price_vnd || ""),
      images: imageUrls.map((url, index) => ({ id: index + ":" + url, url })),
      tags: (item.tags || []).join(", "),
    });
    setDialog("menu");
  }
  function resetMenuForm() {
    setMenuError("");
    setEditingMenuId("");
    setMenuForm(blankMenu);
  }

  async function saveMenu(event) {
    event.preventDefault();
    if (!selected || busy || menuLoading) return;
    const price = Number(menuForm.price_vnd);
    if (!menuForm.name.trim() || !Number.isInteger(price) || price <= 0) {
      toast.error("Vui lòng nhập tên món và giá bán là số nguyên lớn hơn 0.");
      return;
    }
    setBusy(true);
    setMenuError("");
    let uploading = false;
    try {
      const imageUrls = [];
      for (const image of menuForm.images) {
        if (!image.file) {
          imageUrls.push(image.url);
          continue;
        }
        const body = new FormData();
        body.append("image", image.file);
        uploading = true;
        const { data } = await axiosClient.post("/owner/menu-items/images", body, {
          params: { poi_id: selected.id, menu_item_id: editingMenuId || undefined },
        });
        uploading = false;
        imageUrls.push(data.image_url);
        setMenuForm((current) => ({
          ...current,
          images: current.images.map((entry) =>
            entry.id === image.id ? { id: entry.id, url: data.image_url } : entry,
          ),
        }));
      }
      const payload = {
        name: menuForm.name.trim(),
        price_vnd: price,
        image_urls: imageUrls,
        tags: parseTags(menuForm.tags),
      };
      const { data: savedItem } = editingMenuId
        ? await axiosClient.patch("/owner/menu-items/" + editingMenuId, payload)
        : await axiosClient.post("/owner/menu-items", {
            ...payload,
            poi_id: selected.id,
          });
      setMenuItems((items) =>
        editingMenuId
          ? items.map((item) => (item.id === editingMenuId ? savedItem : item))
          : [savedItem, ...items],
      );
      setDialog(null);
      toast.success(
        editingMenuId ? "Đã cập nhật món ăn." : "Đã thêm món vào thực đơn.",
      );
      resetMenuForm();
    } catch (err) {
      if (err.response?.status === 405) {
        setMenuError(uploading
          ? "Máy chủ chưa hỗ trợ tải ảnh món ăn. Hãy chạy lại backend từ phiên bản mới rồi thử lại."
          : "Máy chủ từ chối thao tác lưu món. Hãy kiểm tra địa chỉ API và phiên bản backend rồi thử lại.");
      } else {
        setMenuError(apiErrorMessage(err, uploading ? "Không tải được ảnh món ăn" : "Không lưu được món ăn"));
      }
    } finally {
      setBusy(false);
    }
  }

  async function deleteMenu(items) {
    if (busy || !items?.length) return;
    setBusy(true);
    const deleted = new Set();
    const failed = [];
    try {
      for (const item of items) {
        try {
          await axiosClient.delete("/owner/menu-items/" + item.id);
          deleted.add(item.id);
        } catch (err) {
          if (err.response?.status === 404) deleted.add(item.id);
          else failed.push({ item, err });
        }
      }
      setMenuItems((previous) => previous.filter((item) => !deleted.has(item.id)));
      if (deleted.has(editingMenuId)) resetMenuForm();
      setDeleting(null);
      if (deleted.size) toast.success("Đã xóa " + deleted.size + " món khỏi thực đơn.");
      if (failed.length) {
        const message = apiErrorMessage(failed[0].err, "Không xóa được món ăn");
        toast.error("Không xóa được " + failed.length + " món: " + message);
      }
    } finally {
      setBusy(false);
    }
  }

  async function generateDescription() {
    if (!selected || generatingDescription || proposalBusy) return;
    setGeneratingDescription(true);
    setDescriptionError("");
    setContextQuestion("");
    const draft = proposal.original_description.trim();
    const notes = draft === lastGeneration.current?.description
      ? lastGeneration.current.notes
      : draft;
    try {
      const { data } = await axiosClient.post("/ai/enhance-description", {
        poi_id: selected.id,
        poi_name: selected.name,
        owner_highlight: ownerHighlight.trim(),
        raw_notes: notes,
      }, { timeout: 75000 });
      lastGeneration.current = { description: data.enhanced_description.trim(), notes };
      setProposal((current) => ({
        ...current,
        original_description: data.enhanced_description,
      }));
      toast.success("Đã chèn gợi ý. Hãy đọc lại mô tả trước khi gửi.");
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.code === "ai_context_required") {
        setContextQuestion(detail.message);
        highlightField.current?.focus();
      } else {
        setDescriptionError(apiErrorMessage(err, "Không tạo được mô tả. Vui lòng thử lại."));
      }
    } finally {
      setGeneratingDescription(false);
    }
  }

  async function submitProposal(event) {
    event.preventDefault();
    if (!selected || proposalBusy || generatingDescription || locationBusy) return;
    const proposed_changes = {};
    ["name", "address", "ward", "category", "original_description"].forEach(
      (key) => {
        const next = String(proposal[key] || "").trim();
        if (next !== String(selected[key] || "").trim())
          proposed_changes[key] = next;
      },
    );
    const coordinates = proposal.coordinates;
    const original = coordinatesFromPoi(selected) ?? [];
    if (coordinates && (coordinates[0] !== original[0] || coordinates[1] !== original[1])) {
      proposed_changes.location = {
        type: "Point",
        coordinates,
      };
    }
    if (!proposalPhoto && !Object.keys(proposed_changes).length) {
      toast.error("Chưa có thay đổi nào trong thông tin quán.");
      return;
    }
    setProposalBusy(true);
    setError("");
    try {
      const payload = { poi_id: selected.id, proposed_changes };
      if (proposalPhoto) {
        const body = new FormData();
        body.append("payload", JSON.stringify(payload));
        body.append("image", proposalPhoto);
        await axiosClient.post("/owner/submissions/with-photo", body);
      } else {
        await axiosClient.post("/owner/submissions", payload);
      }
      setProposal(proposalFromPoi(selected));
      setDialog(null);
      toast.success(
        "Đã gửi đề xuất. Quản trị viên sẽ xét duyệt trước khi thông tin được cập nhật.",
      );
    } catch (err) {
      toast.error(apiErrorMessage(err, "Không gửi được đề xuất"));
    } finally {
      setProposalBusy(false);
    }
  }

  if (loading)
    return (
      <div
        role="status"
        className="rounded-xl border bg-white p-6 text-sm text-slate-600"
      >
        Đang tải thông tin quán…
      </div>
    );

  return (
    <div className="space-y-6">
      <header className="admin-dashboard-heading">
        <div>
          <p className="admin-eyebrow">Quản lý quán</p>
          <h1>{isMenu ? "Thực đơn" : "Thông tin quán"}</h1>
          <p>
            {isMenu
              ? "Thêm món, cập nhật giá và hình ảnh."
              : "Xem thông tin hiện tại và gửi đề xuất chỉnh sửa."}
          </p>
        </div>
      </header>
      {shopError && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 p-3 text-sm text-red-800"
        >
          {shopError}{" "}
          <button type="button" onClick={onRetry} className="underline">
            Thử lại
          </button>
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 p-3 text-sm text-red-800"
        >
          {error}
        </p>
      )}
      {!selected && !shopError && (
        <div className="rounded-xl border bg-white p-6 text-center">
          <FiMapPin className="mx-auto" size={24} aria-hidden="true" />
          <h2 className="mt-3">Chưa có quán được liên kết</h2>
          <p className="mt-2 text-sm text-slate-600">
            Quản trị viên cần liên kết hồ sơ của bạn với địa điểm.
          </p>
          <button
            type="button"
            onClick={onRetry}
            className="admin-refresh-button mx-auto mt-4"
          >
            Tải lại
          </button>
        </div>
      )}
      {selected && !shopError && (
        <section className="rounded-xl border bg-white p-5">
          {isMenu ? (
            <div>
              <h2 className="mb-4 text-lg">{selected.name}</h2>
              <button
                type="button"
                disabled={busy || menuLoading}
                className="admin-button-primary inline-flex items-center gap-2 disabled:opacity-50"
                onClick={() => {
                  resetMenuForm();
                  setDialog("menu");
                }}
              >
                <FiPlus aria-hidden="true" /> Thêm món
              </button>
              <OwnerMenuTable items={menuItems} shopName={selected.name} busy={busy} loading={menuLoading}
                error={error} onEdit={startEdit} onDelete={setDeleting} />
            </div>
          ) : (
            <div className="space-y-4">
              {selected.images?.[0] && (
                <img
                  src={assetUrl(selected.images[0])}
                  alt=""
                  className="h-40 w-full max-w-sm rounded-lg object-cover"
                />
              )}
              <div>
                <h2 className="text-lg">{selected.name}</h2>
                <p className="text-sm text-slate-600">{selected.address}</p>
              </div>
              {selected.category && (
                <p className="text-sm">{selected.category}</p>
              )}
              {selected.original_description && (
                <p className="whitespace-pre-wrap text-sm">
                  {selected.original_description}
                </p>
              )}
              <button
                type="button"
                className="admin-button-primary"
                onClick={() => {
                  setProposal(proposalFromPoi(selected));
                  setProposalPhoto(null);
                  setDescriptionError("");
                  setOwnerHighlight("");
                  setContextQuestion("");
                  lastGeneration.current = null;
                  setDialog("proposal");
                }}
              >
                Đề xuất chỉnh sửa
              </button>
            </div>
          )}
        </section>
      )}
      <OwnerDialog
        open={dialog === "menu"}
        onClose={() => setDialog(null)}
        busy={busy}
        title={editingMenuId ? "Chỉnh sửa món" : "Thêm món mới"}
        description={selected?.name || "Thông tin món ăn"}
        footer={
          <>
            {menuError && <p role="alert" className="basis-full rounded-lg bg-red-50 p-2 text-sm text-red-800">{menuError}</p>}
            <button type="button" disabled={busy} onClick={() => setDialog(null)} className="owner-secondary">Hủy</button>
            <button type="submit" form={menuFormId} disabled={busy} className="admin-button-primary disabled:opacity-50">
              {busy ? "Đang lưu…" : editingMenuId ? "Lưu thay đổi" : "Thêm vào thực đơn"}
            </button>
          </>
        }
      >
        <form id={menuFormId} onSubmit={saveMenu} className="space-y-4">
          <fieldset disabled={busy} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-[2fr_1fr]">
              <label className="block text-sm font-medium">Tên món
                <input required maxLength={120} className={input} value={menuForm.name}
                  onChange={(event) => setMenuForm({ ...menuForm, name: event.target.value })} placeholder="Ví dụ: Bánh mì chảo" />
              </label>
              <label className="block text-sm font-medium">Giá (VNĐ)
                <input required type="number" min="1" max="1000000000" step="1" className={input} value={menuForm.price_vnd}
                  onChange={(event) => setMenuForm({ ...menuForm, price_vnd: event.target.value })} placeholder="45000" />
              </label>
            </div>
            <label className="block text-sm font-medium">Nhãn, phân cách bằng dấu phẩy
              <input className={input} value={menuForm.tags}
                onChange={(event) => setMenuForm({ ...menuForm, tags: event.target.value })} placeholder="món cay, đặc sản" />
            </label>
            <MenuImagePicker images={menuForm.images} disabled={busy}
              onChange={(images) => setMenuForm((current) => ({ ...current, images }))} />
          </fieldset>
        </form>
      </OwnerDialog>
      <OwnerDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        busy={busy}
        title={deleting?.length > 1 ? "Xóa nhiều món khỏi thực đơn" : "Xóa món khỏi thực đơn"}
        description={
          deleting?.length === 1
            ? "Bạn có muốn xóa món “" + deleting[0].name + "” khỏi thực đơn?"
            : "Bạn có muốn xóa " + (deleting?.length ?? 0) + " món đã chọn khỏi thực đơn?"
        }
      >
        <div className="flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => setDeleting(null)}
            className="rounded-lg border px-4 py-2 text-sm"
          >
            Hủy
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => deleteMenu(deleting)}
            className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white"
          >
            {busy ? "Đang xóa…" : deleting?.length > 1 ? "Xóa " + deleting.length + " món" : "Xóa món"}
          </button>
        </div>
      </OwnerDialog>
      <OwnerDialog
        open={dialog === "proposal"}
        onClose={() => setDialog(null)}
        busy={proposalBusy || generatingDescription || locationBusy}
        className="owner-proposal-dialog"
        title="Đề xuất chỉnh sửa thông tin quán"
        description="Quản trị viên sẽ xét duyệt trước khi cập nhật."
      >
        <form onSubmit={submitProposal} className="mt-4 space-y-3">
          <label className="block text-sm font-medium text-slate-700">
            Tên quán
            <input
              className={input}
              maxLength={180}
              value={proposal.name}
              onChange={(event) =>
                setProposal({ ...proposal, name: event.target.value })
              }
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm font-medium text-slate-700">
              Phường
              <input
                className={input}
                maxLength={80}
                value={proposal.ward}
                onChange={(event) =>
                  setProposal({ ...proposal, ward: event.target.value })
                }
              />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Loại hình
              <input
                className={input}
                maxLength={80}
                value={proposal.category}
                onChange={(event) =>
                  setProposal({ ...proposal, category: event.target.value })
                }
              />
            </label>
          </div>
          <div>
            <label htmlFor={descriptionId} className="block text-sm font-medium text-slate-700">
              Mô tả
            </label>
            <div className="relative">
              <textarea
                id={descriptionId}
                rows="5"
                maxLength={8000}
                className={input + " relative block resize-y pb-12"}
                value={proposal.original_description}
                readOnly={generatingDescription}
                onChange={(event) =>
                  setProposal({
                    ...proposal,
                    original_description: event.target.value,
                  })
                }
                placeholder="Mô tả món ăn, hương vị, trải nghiệm…"
              />
              <button
                type="button"
                aria-label="Gợi ý mô tả bằng AI"
                title="Gợi ý mô tả bằng AI"
                aria-busy={generatingDescription}
                disabled={proposalBusy || generatingDescription}
                onClick={generateDescription}
                className="absolute right-4 bottom-3 inline-flex size-9 items-center justify-center rounded-lg border border-blue-200 bg-blue-50 text-blue-800 hover:bg-blue-100 disabled:opacity-65"
              >
                {generatingDescription
                  ? <FiLoader aria-hidden="true" className="motion-safe:animate-spin" />
                  : <LuSparkles aria-hidden="true" />}
              </button>
            </div>
            <span className="sr-only" role="status">{generatingDescription ? "AI đang tạo mô tả." : ""}</span>
            {descriptionError && <p className="mt-1.5 text-sm text-red-700" role="alert">{descriptionError}</p>}
          </div>
          <div>
            <label htmlFor={highlightId} className="block text-sm font-medium text-slate-700">
              Điểm đặc trưng của quán <span className="font-normal text-slate-500">(tùy chọn)</span>
            </label>
            <textarea
              id={highlightId}
              ref={highlightField}
              rows="2"
              maxLength={500}
              className={input + " block resize-y"}
              value={ownerHighlight}
              readOnly={generatingDescription}
              onChange={(event) => {
                setOwnerHighlight(event.target.value);
                if (event.target.value.trim()) setContextQuestion("");
              }}
              placeholder="Ví dụ: muốn giới thiệu bánh mì chảo ăn kèm nước mía."
              aria-describedby={highlightId + "-hint"}
            />
            <p id={highlightId + "-hint"} role={contextQuestion ? "alert" : undefined}
              className={`mt-1 text-xs ${contextQuestion ? "text-amber-800" : "text-slate-600"}`}>
              {contextQuestion || "AI dùng thông tin quán, thực đơn và ghi chú bạn bổ sung để viết gợi ý."}
            </p>
          </div>
          {dialog === "proposal" && (
            <ProposalMediaFields
              coverUrl={selected.images?.[0]}
              photo={proposalPhoto}
              onPhotoChange={setProposalPhoto}
              address={proposal.address}
              coordinates={proposal.coordinates}
              onLocationChange={(changes) => setProposal((current) => ({ ...current, ...changes }))}
              onLookupChange={setLocationBusy}
              disabled={proposalBusy}
            />
          )}
          <button
            disabled={proposalBusy || generatingDescription || locationBusy}
            className="w-full rounded-lg border border-orange-300 bg-orange-50 px-4 py-2.5 text-sm font-semibold text-orange-900 hover:bg-orange-100 disabled:opacity-50"
          >
            {proposalBusy ? "Đang gửi đề xuất…" : "Gửi quản trị viên xét duyệt"}
          </button>
        </form>
      </OwnerDialog>
    </div>
  );
}
