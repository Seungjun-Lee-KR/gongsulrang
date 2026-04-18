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
        event: {
          addListener: (target: unknown, type: string, handler: () => void) => void;
        };
      };
    };
  }
}

type KakaoMapInstance = {
  setCenter: (pos: unknown) => void;
  setBounds: (bounds: KakaoBounds) => void;
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

export type { KakaoMapInstance, KakaoMarker, KakaoOverlay, KakaoBounds };

const SDK_ID = "kakao-maps-sdk";

let loadPromise: Promise<void> | null = null;

export function loadKakaoMaps(appkey: string): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("window unavailable"));
  if (window.kakao?.maps) return Promise.resolve();
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    const existing = document.getElementById(SDK_ID) as HTMLScriptElement | null;
    const onReady = () => {
      if (!window.kakao?.maps) {
        reject(new Error("kakao.maps not available after SDK load"));
        return;
      }
      window.kakao.maps.load(() => resolve());
    };

    if (existing) {
      existing.addEventListener("load", onReady, { once: true });
      existing.addEventListener("error", () => reject(new Error("Kakao SDK load failed")), {
        once: true,
      });
      return;
    }

    const script = document.createElement("script");
    script.id = SDK_ID;
    script.async = true;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(appkey)}&autoload=false`;
    script.addEventListener("load", onReady, { once: true });
    script.addEventListener("error", () => {
      loadPromise = null;
      reject(new Error("Kakao SDK load failed"));
    }, { once: true });
    document.head.appendChild(script);
  });

  return loadPromise;
}
