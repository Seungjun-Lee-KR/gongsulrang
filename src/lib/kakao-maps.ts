declare global {
  interface Window {
    kakao?: {
      maps: {
        load: (cb: () => void) => void;
        LatLng: new (lat: number, lng: number) => unknown;
        Map: new (container: HTMLElement, options: { center: unknown; level: number }) => KakaoMapInstance;
        Marker: new (options: { position: unknown; map?: KakaoMapInstance; title?: string }) => KakaoMarker;
        CustomOverlay: new (options: {
          position: unknown;
          content: string | HTMLElement;
          yAnchor?: number;
          xAnchor?: number;
        }) => KakaoOverlay;
        LatLngBounds: new () => KakaoBounds;
        Circle: new (options: {
          center: unknown;
          radius: number;
          strokeWeight?: number;
          strokeColor?: string;
          strokeOpacity?: number;
          strokeStyle?: string;
          fillColor?: string;
          fillOpacity?: number;
        }) => KakaoCircle;
        event: {
          addListener: (target: unknown, type: string, handler: () => void) => void;
        };
        services?: {
          Status: { OK: "OK"; ZERO_RESULT: "ZERO_RESULT"; ERROR: "ERROR" };
          Places: new () => KakaoPlaces;
          Geocoder: new () => KakaoGeocoder;
        };
      };
    };
  }
}

type KakaoPlaceResult = {
  id: string;
  place_name: string;
  address_name: string;
  road_address_name: string;
  x: string;
  y: string;
  category_name?: string;
};

type KakaoPlaces = {
  keywordSearch: (
    keyword: string,
    callback: (data: KakaoPlaceResult[], status: "OK" | "ZERO_RESULT" | "ERROR") => void,
    options?: { size?: number },
  ) => void;
};

type KakaoAddressResult = {
  address_name: string;
  x: string;
  y: string;
};

type KakaoGeocoder = {
  addressSearch: (
    query: string,
    callback: (data: KakaoAddressResult[], status: "OK" | "ZERO_RESULT" | "ERROR") => void,
  ) => void;
};

type KakaoMapInstance = {
  setCenter: (pos: unknown) => void;
  setBounds: (bounds: KakaoBounds) => void;
  setLevel: (level: number) => void;
  relayout: () => void;
};

type KakaoMarker = {
  setMap: (map: KakaoMapInstance | null) => void;
};

type KakaoOverlay = {
  setMap: (map: KakaoMapInstance | null) => void;
};

type KakaoBounds = {
  extend: (pos: unknown) => void;
};

type KakaoCircle = {
  setMap: (map: KakaoMapInstance | null) => void;
};

export type {
  KakaoMapInstance,
  KakaoMarker,
  KakaoOverlay,
  KakaoBounds,
  KakaoCircle,
  KakaoPlaceResult,
  KakaoPlaces,
  KakaoGeocoder,
};

const SDK_ID = "kakao-maps-sdk";

let loadPromise: Promise<void> | null = null;

export function loadKakaoMaps(appkey: string): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("window unavailable"));
  if (window.kakao?.maps) return Promise.resolve();
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      loadPromise = null;
      reject(new Error("Kakao 지도 SDK 로딩 시간 초과 (도메인 허용 설정을 확인해 주세요)"));
    }, 8000);

    const settle = (fn: () => void) => {
      clearTimeout(timer);
      fn();
    };

    const existing = document.getElementById(SDK_ID) as HTMLScriptElement | null;
    const onReady = () => {
      if (!window.kakao?.maps) {
        settle(() => reject(new Error("kakao.maps not available after SDK load")));
        return;
      }
      window.kakao.maps.load(() => settle(resolve));
    };
    const onError = () => {
      settle(() => {
        loadPromise = null;
        reject(new Error("Kakao SDK load failed"));
      });
    };

    if (existing) {
      existing.addEventListener("load", onReady, { once: true });
      existing.addEventListener("error", onError, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.id = SDK_ID;
    script.async = true;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(appkey)}&autoload=false&libraries=services`;
    script.addEventListener("load", onReady, { once: true });
    script.addEventListener("error", onError, { once: true });
    document.head.appendChild(script);
  });

  return loadPromise;
}

export type PlaceHit = {
  name: string;
  address: string;
  lat: number;
  lng: number;
};

export function searchPlaceByKeyword(keyword: string): Promise<PlaceHit | null> {
  return new Promise((resolve, reject) => {
    const services = window.kakao?.maps?.services;
    if (!services) {
      reject(new Error("Kakao services 라이브러리가 로드되지 않았습니다."));
      return;
    }
    const places = new services.Places();
    places.keywordSearch(
      keyword,
      (data, status) => {
        if (status === "OK" && data.length > 0) {
          const top = data[0];
          resolve({
            name: top.place_name,
            address: top.road_address_name || top.address_name,
            lat: Number(top.y),
            lng: Number(top.x),
          });
          return;
        }
        if (status === "ZERO_RESULT") {
          const geocoder = new services.Geocoder();
          geocoder.addressSearch(keyword, (addr, aStatus) => {
            if (aStatus === "OK" && addr.length > 0) {
              resolve({
                name: keyword,
                address: addr[0].address_name,
                lat: Number(addr[0].y),
                lng: Number(addr[0].x),
              });
              return;
            }
            resolve(null);
          });
          return;
        }
        resolve(null);
      },
      { size: 1 },
    );
  });
}
