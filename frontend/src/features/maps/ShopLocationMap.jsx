import React, { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const DEFAULT_CENTER = [106.7028, 10.7582];
const tileUrl = import.meta.env.VITE_REGISTRATION_MAP_TILE_URL ||
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const streetMap = {
  version: 8,
  sources: {
    streets: {
      type: "raster",
      tiles: [tileUrl],
      tileSize: 256,
      maxzoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>',
    },
  },
  layers: [{ id: "streets", type: "raster", source: "streets" }],
};

export default function ShopLocationMap({
  coordinates, centerOn, onPick, disabled = false, draggablePin = false, pickOnPan = false,
}) {
  const container = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const initialCenter = useRef(coordinates ?? DEFAULT_CENTER);
  const pickRef = useRef(null);
  pickRef.current = disabled ? null : onPick;
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  function pick(point) {
    pickRef.current?.([Number(point.wrap().lng.toFixed(7)), Number(point.lat.toFixed(7))]);
  }

  useEffect(() => {
    let map;
    try {
      map = new maplibregl.Map({
        container: container.current,
        center: initialCenter.current,
        zoom: 16,
        style: streetMap,
        scrollZoom: false,
        maxZoom: 20,
        attributionControl: false,
      });
      mapRef.current = map;
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }));
      map.addControl(new maplibregl.AttributionControl({ compact: false }));
      map.on("load", () => {
        setReady(true);
        map.on("click", (event) => pick(event.lngLat));
        if (pickOnPan) map.on("dragend", () => pick(map.getCenter()));
      });
      map.on("error", () => setError("Bản đồ đường phố tải chưa đầy đủ. Bạn có thể thử tải lại."));
    } catch {
      setError("Không mở được bản đồ. Hãy thử tải lại hoặc dùng trình duyệt hỗ trợ WebGL.");
    }
    return () => {
      markerRef.current?.remove();
      markerRef.current = null;
      mapRef.current = null;
      map?.remove();
    };
  }, [attempt, pickOnPan]);

  useEffect(() => {
    if (!coordinates || !mapRef.current) return;
    if (!markerRef.current) {
      const marker = new maplibregl.Marker({ color: "#b42318" })
        .setLngLat(coordinates)
        .addTo(mapRef.current);
      marker.on("dragend", () => pick(marker.getLngLat()));
      markerRef.current = marker;
    } else {
      markerRef.current.setLngLat(coordinates);
    }
  }, [coordinates, attempt]);

  useEffect(() => {
    markerRef.current?.setDraggable(draggablePin && !disabled);
  }, [coordinates, attempt, draggablePin, disabled]);

  useEffect(() => {
    if (centerOn) mapRef.current?.jumpTo({ center: centerOn, zoom: 17 });
  }, [centerOn, attempt]);

  return (
    <div className="space-y-2">
      <div ref={container} className="h-60 w-full overflow-hidden rounded-lg border border-slate-300 bg-slate-100"
        role="region" aria-label={onPick ? "Bản đồ chọn vị trí quán" : "Vị trí quán trên bản đồ"} />
      {onPick && !pickOnPan && (
        <button type="button" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-50"
          disabled={disabled || !ready} onClick={() => pick(mapRef.current.getCenter())}>
          Ghim ở giữa bản đồ
        </button>
      )}
      {error && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-amber-800" role="status">
          <span>{error}</span>
          <button type="button" className="font-semibold underline" disabled={disabled} onClick={() => {
            initialCenter.current = coordinates ?? initialCenter.current;
            setReady(false);
            setError("");
            setAttempt((current) => current + 1);
          }}>Tải lại bản đồ</button>
        </div>
      )}
    </div>
  );
}
