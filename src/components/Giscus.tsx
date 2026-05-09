"use client";

import { useEffect, useRef } from "react";

const GISCUS_CONFIG = {
  "data-repo": "Seungjun-Lee-KR/gongsulrang",
  "data-repo-id": "R_kgDOSW8gdw",
  "data-category": "General",
  "data-category-id": "DIC_kwDOSW8gd84C8pXn",
  "data-mapping": "pathname",
  "data-strict": "0",
  "data-reactions-enabled": "1",
  "data-emit-metadata": "0",
  "data-input-position": "top",
  "data-theme": "noborder_dark",
  "data-lang": "ko",
  "data-loading": "lazy",
} as const;

export default function Giscus() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = ref.current;
    if (!container || container.querySelector("iframe")) return;
    const script = document.createElement("script");
    script.src = "https://giscus.app/client.js";
    script.crossOrigin = "anonymous";
    script.async = true;
    for (const [k, v] of Object.entries(GISCUS_CONFIG)) {
      script.setAttribute(k, v);
    }
    container.appendChild(script);
  }, []);

  return <div ref={ref} className="giscus" />;
}
