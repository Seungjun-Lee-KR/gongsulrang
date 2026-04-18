"use client";

import { useEffect, useRef, useState } from "react";
import {
  loadKakaoMaps,
  type KakaoMapInstance,
  type KakaoMarker,
  type KakaoOverlay,
} from "@/lib/kakao-maps";

export type MapMarker = {
  id: string | number;
  lat: number;
  lng: number;
  label?: string;
  href?: string;
};

type Props = {
  markers: MapMarker[];
  center?: { lat: number; lng: number };
  level?: number;
  userCoord?: { lat: number; lng: number } | null;
  className?: string;
};

const appkey = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY;

export default function KakaoMap({
  markers,
  center,
  level = 9,
  userCoord,
  className,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<KakaoMapInstance | null>(null);
  const markerObjectsRef = useRef<Array<KakaoMarker | KakaoOverlay>>([]);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!appkey) {
      setError("NEXT_PUBLIC_KAKAO_MAP_KEY가 설정되지 않았습니다.");
      return;
    }
    if (!containerRef.current) return;

    let cancelled = false;

    loadKakaoMaps(appkey)
      .then(() => {
        if (cancelled || !containerRef.current) return;
        const kakao = window.kakao!;
        const start = center ??
          (markers[0] ? { lat: markers[0].lat, lng: markers[0].lng } : { lat: 36.5, lng: 127.8 });
        const map = new kakao.maps.Map(containerRef.current, {
          center: new kakao.maps.LatLng(start.lat, start.lng),
          level,
        });
        mapRef.current = map;
        setReady(true);
        requestAnimationFrame(() => {
          map.relayout();
          map.setCenter(new kakao.maps.LatLng(start.lat, start.lng));
        });
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });

    const container = containerRef.current;
    const ro = new ResizeObserver(() => {
      mapRef.current?.relayout();
    });
    ro.observe(container);

    return () => {
      cancelled = true;
      ro.disconnect();
    };
  }, [center, level, markers]);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    const kakao = window.kakao!;
    const map = mapRef.current;

    for (const obj of markerObjectsRef.current) obj.setMap(null);
    markerObjectsRef.current = [];

    for (const m of markers) {
      const pos = new kakao.maps.LatLng(m.lat, m.lng);
      const marker = new kakao.maps.Marker({ position: pos, map, title: m.label });
      markerObjectsRef.current.push(marker);

      if (m.label) {
        const contentHtml = m.href
          ? `<a href="${m.href}" class="inline-block -translate-y-1 rounded-full bg-zinc-900 px-2 py-0.5 text-[11px] font-semibold text-white shadow-md hover:bg-orange-600">${escapeHtml(m.label)}</a>`
          : `<div class="inline-block -translate-y-1 rounded-full bg-zinc-900 px-2 py-0.5 text-[11px] font-semibold text-white shadow-md">${escapeHtml(m.label)}</div>`;
        const overlay = new kakao.maps.CustomOverlay({
          position: pos,
          content: contentHtml,
          yAnchor: 2.4,
        });
        overlay.setMap(map);
        markerObjectsRef.current.push(overlay);
      }
    }

    if (userCoord) {
      const pos = new kakao.maps.LatLng(userCoord.lat, userCoord.lng);
      const dot = new kakao.maps.CustomOverlay({
        position: pos,
        content:
          '<div class="h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-blue-500 shadow-md"></div>',
      });
      dot.setMap(map);
      markerObjectsRef.current.push(dot);
    }

    if (markers.length > 1) {
      const bounds = new kakao.maps.LatLngBounds();
      for (const m of markers) bounds.extend(new kakao.maps.LatLng(m.lat, m.lng));
      if (userCoord) bounds.extend(new kakao.maps.LatLng(userCoord.lat, userCoord.lng));
      map.setBounds(bounds);
    } else if (markers.length === 1) {
      map.setCenter(new kakao.maps.LatLng(markers[0].lat, markers[0].lng));
    }

    requestAnimationFrame(() => {
      map.relayout();
      if (markers.length === 1) {
        map.setCenter(new kakao.maps.LatLng(markers[0].lat, markers[0].lng));
      }
    });
  }, [ready, markers, userCoord]);

  if (error) {
    return (
      <div
        className={`flex items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-zinc-50 p-8 text-sm text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400 ${className ?? ""}`}
      >
        지도를 불러올 수 없습니다: {error}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`rounded-2xl border border-zinc-200 bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-900 ${className ?? ""}`}
    />
  );
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!,
  );
}
