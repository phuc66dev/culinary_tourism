import React, { useEffect, useId, useState } from "react";
import axiosClient from "../../../api/axiosClient.js";
import {
  apiErrorMessage,
  assetUrl,
} from "../../admin-dashboard/utils/assetUrl.js";
import toast from "react-hot-toast";
import { FiMapPin, FiPlus, FiZap } from "react-icons/fi";
import OwnerMenuTable from "../components/OwnerMenuTable.jsx";
import MenuImagePicker from '../components/MenuImagePicker.jsx';
import OwnerDialog from "../components/OwnerDialog.jsx";
import AIAdvisorModal from "../components/AIAdvisorModal.jsx";

const input =
  "mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100";
const blankMenu = { name: "", price_vnd: "", images: [], tags: "" };
const blankProposal = {
  name: "",
  address: "",
  ward: "",
  category: "",
  original_description: "",
  images: "",
  longitude: "",
  latitude: "",
};

function parseTags(value) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}
function proposalFromPoi(poi) {
  return {
    name: poi.name || "",
    address: poi.address || "",
    ward: poi.ward || "",
    category: poi.category || "",
    original_description: poi.original_description || "",
    images: (poi.images || []).join("\n"),
    longitude:
      poi.location?.coordinates?.[0] == null
        ? ""
        : String(poi.location.coordinates[0]),
    latitude:
      poi.location?.coordinates?.[1] == null
        ? ""
        : String(poi.location.coordinates[1]),
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
  const [proposalBusy, setProposalBusy] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);

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

  async function submitProposal(event) {
    event.preventDefault();
    if (!selected || proposalBusy) return;
    const proposed_changes = {};
    ["name", "address", "ward", "category", "original_description"].forEach(
      (key) => {
        const next = String(proposal[key] || "").trim();
        if (next !== String(selected[key] || "").trim())
          proposed_changes[key] = next;
      },
    );
    const images = proposal.images
      .split(/[\n,]/)
      .map((url) => url.trim())
      .filter(Boolean);
    if (JSON.stringify(images) !== JSON.stringify(selected.images || []))
      proposed_changes.images = images;
    const originalCoordinates = selected.location?.coordinates || [];
    const coordinatesChanged =
      proposal.longitude !== String(originalCoordinates[0] ?? "") ||
      proposal.latitude !== String(originalCoordinates[1] ?? "");
    if (coordinatesChanged) {
      const longitude = Number(proposal.longitude);
      const latitude = Number(proposal.latitude);
      if (
        !proposal.longitude.trim() ||
        !proposal.latitude.trim() ||
        !Number.isFinite(longitude) ||
        longitude < -180 ||
        longitude > 180 ||
        !Number.isFinite(latitude) ||
        latitude < -90 ||
        latitude > 90
      ) {
        toast.error(
          "Vui lòng nhập kinh độ từ -180 đến 180 và vĩ độ từ -90 đến 90.",
        );
        return;
      }
      proposed_changes.location = {
        type: "Point",
        coordinates: [longitude, latitude],
      };
    }
    if (!Object.keys(proposed_changes).length) {
      toast.error("Chưa có thay đổi nào trong thông tin quán.");
      return;
    }
    setProposalBusy(true);
    setError("");
    try {
      await axiosClient.post("/owner/submissions", {
        poi_id: selected.id,
        proposed_changes,
      });
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
        onClose={() => {
          setDialog(null);
          setAiOpen(false);
        }}
        busy={proposalBusy}
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
          <label className="block text-sm font-medium text-slate-700">
            Địa chỉ
            <input
              className={input}
              maxLength={400}
              value={proposal.address}
              onChange={(event) =>
                setProposal({ ...proposal, address: event.target.value })
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
          <label className="block text-sm font-medium text-slate-700">
            Mô tả
            <textarea
              rows="5"
              maxLength={8000}
              className={input + " resize-y"}
              value={proposal.original_description}
              onChange={(event) =>
                setProposal({
                  ...proposal,
                  original_description: event.target.value,
                })
              }
              placeholder="Mô tả món ăn, hương vị, trải nghiệm…"
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Ảnh quán{" "}
            <span className="font-normal text-slate-500">
              (mỗi đường dẫn một dòng, tối đa 20 ảnh)
            </span>
            <textarea
              rows="3"
              className={input + " resize-y"}
              value={proposal.images}
              onChange={(event) =>
                setProposal({ ...proposal, images: event.target.value })
              }
              placeholder="https://example.com/anh-quan.jpg"
            />
          </label>
          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-1 text-sm font-semibold text-slate-700">
              Vị trí bản đồ (GeoJSON: kinh độ, vĩ độ)
            </legend>
            <label className="block text-sm font-medium text-slate-700">
              Kinh độ
              <input
                type="number"
                step="any"
                min="-180"
                max="180"
                className={input}
                value={proposal.longitude}
                onChange={(event) =>
                  setProposal({ ...proposal, longitude: event.target.value })
                }
              />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Vĩ độ
              <input
                type="number"
                step="any"
                min="-90"
                max="90"
                className={input}
                value={proposal.latitude}
                onChange={(event) =>
                  setProposal({ ...proposal, latitude: event.target.value })
                }
              />
            </label>
          </fieldset>
          <button
            disabled={proposalBusy}
            className="w-full rounded-lg border border-orange-300 bg-orange-50 px-4 py-2.5 text-sm font-semibold text-orange-900 hover:bg-orange-100 disabled:opacity-50"
          >
            {proposalBusy ? "Đang gửi đề xuất…" : "Gửi quản trị viên xét duyệt"}
          </button>
        </form>
        <button
          type="button"
          onClick={() => setAiOpen(true)}
          className="mt-3 inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold"
        >
          <FiZap aria-hidden="true" /> Gợi ý mô tả bằng AI
        </button>
        {aiOpen && selected && (
          <AIAdvisorModal
            poi={selected}
            onClose={() => setAiOpen(false)}
            onInsert={(description) => {
              setProposal((current) => ({
                ...current,
                original_description: description,
              }));
              setAiOpen(false);
              toast.success("Đã chèn mô tả AI vào đề xuất.");
            }}
          />
        )}
      </OwnerDialog>
    </div>
  );
}
