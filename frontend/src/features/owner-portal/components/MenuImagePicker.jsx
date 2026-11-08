import React, { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { FiImage, FiPlus, FiX } from 'react-icons/fi';
import { assetUrl } from '../../admin-dashboard/utils/assetUrl.js';

const maxImages = 6;
const maxBytes = 5 * 1024 * 1024;
const imageTypes = ['image/jpeg', 'image/png', 'image/webp'];

function ImagePreview({ image, alt }) {
  const [localUrl, setLocalUrl] = useState(null);
  const [failedSrc, setFailedSrc] = useState(null);
  useEffect(() => {
    if (!image.file) return undefined;
    const url = URL.createObjectURL(image.file);
    setLocalUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [image.file]);
  const src = image.url ? assetUrl(image.url) : localUrl;
  if (!src || failedSrc === src) return <FiImage aria-label="Không xem được ảnh" role="img" size={22} />;
  return <img src={src} alt={alt} onError={() => setFailedSrc(src)} />;
}

export default function MenuImagePicker({ images, onChange, disabled }) {
  const input = useRef(null);

  function addFiles(event) {
    const files = [...event.target.files];
    event.target.value = '';
    if (!files.length) return;
    const next = [...images];
    let rejected = false;
    for (const file of files) {
      const validType = imageTypes.includes(file.type) || (!file.type && /\.(jpe?g|png|webp)$/i.test(file.name));
      if (!validType || !file.size || file.size > maxBytes) {
        rejected = true;
        continue;
      }
      const id = [file.name, file.size, file.lastModified].join(':');
      if (!next.some((image) => image.id === id)) next.push({ id, file });
    }
    if (rejected) toast.error('Chọn ảnh JPEG, PNG hoặc WebP có dung lượng tối đa 5 MB.');
    if (next.length > maxImages) toast.error('Mỗi món có tối đa 6 ảnh.');
    onChange(next.slice(0, maxImages));
  }

  function remove(index) {
    onChange(images.filter((_, current) => current !== index));
  }

  function setCover(index) {
    onChange([images[index], ...images.filter((_, current) => current !== index)]);
  }

  function uploadButton(className, showLabel) {
    return (
      <button type="button" className={className} disabled={disabled || images.length >= maxImages}
        onClick={() => input.current?.click()} aria-label="Tải ảnh từ máy tính" title="Tải ảnh từ máy tính">
        <FiPlus aria-hidden="true" size={22} />
        {showLabel && <span>Tải ảnh từ máy tính</span>}
      </button>
    );
  }

  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-semibold">Ảnh món ăn <span className="font-normal text-slate-500">({images.length}/{maxImages})</span></legend>
      <p className="text-xs text-slate-600">JPEG, PNG hoặc WebP, tối đa 5 MB mỗi ảnh. Chọn ảnh nhỏ để đặt làm ảnh bìa.</p>
      <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden
        disabled={disabled || images.length >= maxImages} onChange={addFiles} />
      {images.length ? (
        <div className="owner-gallery">
          <div className="owner-gallery-cover owner-gallery-tile">
            <ImagePreview key={images[0].id} image={images[0]} alt="Ảnh bìa món ăn" />
            <span className="owner-gallery-label">Ảnh bìa</span>
            <button type="button" className="owner-gallery-remove" onClick={() => remove(0)} disabled={disabled}
              aria-label="Gỡ ảnh bìa" title="Gỡ ảnh bìa"><FiX aria-hidden="true" /></button>
          </div>
          <div className="owner-gallery-thumbnails">
            {images.slice(1).map((image, index) => (
              <div key={image.id} className="owner-gallery-tile">
                <button type="button" className="owner-gallery-preview" onClick={() => setCover(index + 1)}
                  aria-label={'Đặt ảnh ' + (index + 2) + ' làm ảnh bìa'} title="Đặt làm ảnh bìa" disabled={disabled}>
                  <ImagePreview image={image} alt={'Ảnh món ăn ' + (index + 2)} />
                </button>
                <button type="button" className="owner-gallery-remove" onClick={() => remove(index + 1)}
                  disabled={disabled} aria-label={'Gỡ ảnh ' + (index + 2)} title="Gỡ ảnh"><FiX aria-hidden="true" /></button>
              </div>
            ))}
            {images.length < maxImages && uploadButton('owner-gallery-add', false)}
          </div>
        </div>
      ) : uploadButton('owner-gallery-add owner-gallery-empty', true)}
    </fieldset>
  );
}
