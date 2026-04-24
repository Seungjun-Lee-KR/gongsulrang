"use client";

import { useEffect, useRef, useState } from "react";
import {
  loadKakaoMaps,
  type KakaoCircle,
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
  userCircleRadius?: number;
  className?: string;
};

const appkey = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY;

export default function KakaoMap({
  markers,
  center,
  level = 9,
  userCoord,
  userCircleRadius,
  className,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<KakaoMapInstance | null>(null);
  const markerObjectsRef = useRef<Array<KakaoMarker | KakaoOverlay | KakaoCircle>>([]);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!appkey) {
      setError("NEXT_PUBLIC_KAKAO_MAP_KEY가 설정되지 않았습니다.");
      return;
    }
    if (!containerRef.current) return;

    let cancelled = false;

    if (mapRef.current) {
      setReady(true);
    } else {
      loadKakaoMaps(appkey)
        .then(() => {
          if (cancelled || !containerRef.current || mapRef.current) return;
          const kakao = window.kakao!;
          const start = center ?? { lat: 37.5665, lng: 126.9780 };
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
    }

    const container = containerRef.current;
    const ro = new ResizeObserver(() => {
      mapRef.current?.relayout();
    });
    ro.observe(container);

    return () => {
      cancelled = true;
      ro.disconnect();
    };
  }, [center, level]);

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
      if (userCircleRadius && userCircleRadius > 0) {
        const circle = new kakao.maps.Circle({
          center: pos,
          radius: userCircleRadius,
          strokeWeight: 2,
          strokeColor: "#f97316",
          strokeOpacity: 0.7,
          strokeStyle: "solid",
          fillColor: "#f97316",
          fillOpacity: 0.08,
        });
        circle.setMap(map);
        markerObjectsRef.current.push(circle);
      }
      const dot = new kakao.maps.CustomOverlay({
        position: pos,
        content:
          '<div class="h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-blue-500 shadow-md"></div>',
      });
      dot.setMap(map);
      markerObjectsRef.current.push(dot);
    }

    requestAnimationFrame(() => {
      map.relayout();
      if (userCoord && userCircleRadius && userCircleRadius > 0) {
        map.setCenter(new kakao.maps.LatLng(userCoord.lat, userCoord.lng));
        map.setLevel(levelForRadius(userCircleRadius));
      } else if (markers.length > 1) {
        const bounds = new kakao.maps.LatLngBounds();
        for (const m of markers) bounds.extend(new kakao.maps.LatLng(m.lat, m.lng));
        if (userCoord) bounds.extend(new kakao.maps.LatLng(userCoord.lat, userCoord.lng));
        map.setBounds(bounds);
      } else if (markers.length === 1) {
        map.setCenter(new kakao.maps.LatLng(markers[0].lat, markers[0].lng));
      } else if (userCoord) {
        map.setCenter(new kakao.maps.LatLng(userCoord.lat, userCoord.lng));
      }
    });
  }, [ready, markers, userCoord, userCircleRadius]);

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

function levelForRadius(radiusM: number): number {
  if (radiusM <= 500) return 4;
  if (radiusM <= 700) return 4;
  if (radiusM <= 1000) return 5;
  if (radiusM <= 2000) return 6;
  return 7;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!,
  );
}
