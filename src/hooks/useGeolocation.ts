"use client";

import { useCallback, useState } from "react";
import type { Coord } from "@/lib/distance";

export type GeolocationState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; coord: Coord }
  | { status: "error"; message: string };

export function useGeolocation() {
  const [state, setState] = useState<GeolocationState>({ status: "idle" });

  const request = useCallback(() => {
    if (typeof window === "undefined" || !navigator.geolocation) {
      setState({
        status: "error",
        message: "이 브라우저는 위치 기능을 지원하지 않습니다.",
      });
      return;
    }

    setState({ status: "loading" });
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setState({
          status: "success",
          coord: { lat: pos.coords.latitude, lng: pos.coords.longitude },
        });
      },
      (err) => {
        const message =
          err.code === err.PERMISSION_DENIED
            ? "위치 권한이 거부되어 근처 맛집을 찾을 수 없습니다."
            : "현재 위치를 가져오지 못했습니다.";
        setState({ status: "error", message });
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 },
    );
  }, []);

  return { state, request };
}
