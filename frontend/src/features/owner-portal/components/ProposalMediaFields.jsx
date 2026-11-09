import React, { useEffect, useId, useRef, useState } from "react";
import { FiImage, FiSearch, FiUpload } from "react-icons/fi";
import axiosClient from "../../../api/axiosClient.js";
import { assetUrl } from "../../admin-dashboard/utils/assetUrl.js";

const ShopLocationMap = React.lazy(() => import("../../maps/ShopLocationMap.jsx"));
const photoTypes = ["image/jpeg", "image/png", "image/webp"];

export default function ProposalMediaFields({
  coverUrl, photo, onPhotoChange, address, coordinates, onLocationChange, onLookupChange, disabled,
}) {
  const [preview, setPreview] = useState("");
  const [failedPhoto, setFailedPhoto] = useState(null);
  const [photoError, setPhotoError] = useState("");
  const [resolvedAddress, setResolvedAddress] = useState(coordinates ? address : "");
  const [locationMessage, setLocationMessage] = useState("");
  const [lookup, setLookup] = useState(null);
  const [centerOn, setCenterOn] = useState(null);
  const fileInput = useRef(null);
  const lookupRequest = useRef(null);
  const searchId = useId();
  const image = preview || assetUrl(coverUrl);

  useEffect(() => () => lookupRequest.current?.abort(), []);
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
    const supported = photoTypes.includes(file.type) || (!file.type && /\.(jpe?g|png|webp)$/i.test(file.name));
    if (!supported || !file.size || file.size > 5 * 1024 * 1024) {
      setPhotoError("Chọn ảnh JPEG, PNG hoặc WebP tối đa 5 MB.");
      return;
    }
    setPhotoError("");
    onPhotoChange(file);
  }

  async function lookupAddress(mode, path, params, onResult) {
    lookupRequest.current?.abort();
    const request = new AbortController();
    lookupRequest.current = request;
    setLookup(mode);
    onLookupChange(true);
    setLocationMessage("");
    try {
      const { data } = await axiosClient.get(path, { params, signal: request.signal });
      if (!request.signal.aborted) {
        setResolvedAddress(data.address);
        onResult(data);
      }
    } catch (err) {
      if (request.signal.aborted) return;
      setLocationMessage(mode === "pin"
        ? "Đã đổi ghim. Hãy nhập địa chỉ nếu bản đồ chưa nhận ra vị trí."
        : err.response?.status === 404
          ? "Không tìm thấy địa chỉ. Thử nhập thêm tên đường hoặc phường."
          : "Chưa tìm được địa chỉ. Hãy thử lại hoặc chọn vị trí trực tiếp.");
    } finally {
      if (!request.signal.aborted) {
        setLookup(null);
        onLookupChange(false);
      }
    }
  }

  function searchAddress() {
    if (disabled || lookup) return;
    const query = address.trim();
    if (query.length < 3) {
      setLocationMessage("Nhập ít nhất 3 ký tự để tìm địa chỉ.");
      return;
    }
    return lookupAddress("search", "/maps/search-address", { q: query }, (data) => {
      setCenterOn(data.coordinates);
      onLocationChange({ coordinates: data.coordinates, ...(data.ward && { ward: data.ward }) });
    });
  }

  function pickLocation(nextCoordinates) {
    setCenterOn(null);
    setResolvedAddress("");
    onLocationChange({ coordinates: nextCoordinates });
    const [lng, lat] = nextCoordinates;
    return lookupAddress("pin", "/maps/reverse-geocode", { lat, lng }, (data) => {
      onLocationChange({ address: data.address, ...(data.ward && { ward: data.ward }) });
    });
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <section className="min-w-0 space-y-2" aria-label="Ảnh quán">
        <h3 className="text-sm font-semibold">Ảnh quán</h3>
        <div className="grid h-60 place-items-center overflow-hidden rounded-lg border border-slate-300 bg-slate-50">
          {image && failedPhoto !== image ? (
            <a href={image} target="_blank" rel="noopener noreferrer" className="h-full w-full"
              aria-label="Mở ảnh mặt tiền quán">
              <img src={image} alt="Ảnh mặt tiền quán" className="h-full w-full object-contain"
                onError={() => {
                  setFailedPhoto(image);
                  if (preview) {
                    onPhotoChange(null);
                    setPhotoError("Không đọc được ảnh đã chọn. Hãy chọn ảnh khác.");
                  }
                }} />
            </a>
          ) : (
            <p className="flex items-center gap-2 px-3 text-sm text-slate-600">
              <FiImage aria-hidden="true" /> {image ? "Không tải được ảnh" : "Chưa có ảnh quán"}
            </p>
          )}
        </div>
        <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp"
          hidden disabled={disabled} onChange={choosePhoto} />
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={disabled} onClick={() => fileInput.current?.click()}
            className="owner-secondary inline-flex items-center gap-2">
            <FiUpload aria-hidden="true" /> {image ? "Đổi ảnh" : "Chọn ảnh"}
          </button>
          {photo && (
            <button type="button" disabled={disabled} className="owner-secondary" onClick={() => {
              onPhotoChange(null);
              setPhotoError("");
            }}>Hoàn tác</button>
          )}
        </div>
        {photoError && <p role="alert" className="text-sm text-red-700">{photoError}</p>}
      </section>
      <section className="min-w-0 space-y-2" aria-label="Vị trí quán">
        <h3 className="text-sm font-semibold">Vị trí quán</h3>
        <React.Suspense fallback={<p role="status" className="h-60 text-sm text-slate-600">Đang tải bản đồ…</p>}>
          <ShopLocationMap coordinates={coordinates} centerOn={centerOn}
            onPick={pickLocation} draggablePin pickOnPan disabled={disabled} />
        </React.Suspense>
        <label htmlFor={searchId} className="sr-only">Địa chỉ quán</label>
        <div className="relative">
          <input id={searchId} className="w-full rounded-lg border border-slate-300 bg-white py-2.5 pl-3 pr-11 text-sm"
            value={address} maxLength={400} placeholder="Nhập địa chỉ quán" disabled={disabled || Boolean(lookup)}
            onChange={(event) => onLocationChange({ address: event.target.value })}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.nativeEvent.isComposing) {
                event.preventDefault();
                searchAddress();
              }
            }} />
          <button type="button" aria-label="Tìm địa chỉ trên bản đồ" title="Tìm địa chỉ trên bản đồ"
            onClick={searchAddress} disabled={disabled || Boolean(lookup)}
            className="absolute inset-y-0 right-0 grid w-10 place-items-center rounded-r-lg text-blue-800 hover:bg-blue-50 disabled:opacity-50">
            <FiSearch aria-hidden="true" />
          </button>
        </div>
        <div role="status" className="break-words text-sm text-slate-600">
          {lookup ? "Đang tra địa chỉ…" : locationMessage || (resolvedAddress
            ? <><span className="font-semibold">Địa chỉ ghim</span> · {resolvedAddress}</>
            : "Tìm theo địa chỉ, kéo ghim hoặc kéo bản đồ để chọn vị trí.")}
        </div>
      </section>
    </div>
  );
}
