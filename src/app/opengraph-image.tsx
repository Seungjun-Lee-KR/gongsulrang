import { ImageResponse } from "next/og";
import { restaurants } from "@/data/restaurants";

export const alt = "공슐랭 — 공무원이 인정한 서울 맛집";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  const total = restaurants.length.toLocaleString();

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#08080a",
          color: "#f5f5f7",
          padding: "80px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          fontFamily: "sans-serif",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            width: 700,
            height: 380,
            background:
              "radial-gradient(circle at 70% 30%, rgba(255,122,77,0.28), transparent 60%)",
          }}
        />

        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: 999,
              background:
                "linear-gradient(135deg, #ff7a4d, #ffd07a 60%, #c2ff5e)",
            }}
          />
          <div
            style={{
              fontSize: 22,
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              color: "#ff7a4d",
              fontWeight: 600,
            }}
          >
            The Officials' Guide
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div
            style={{
              fontSize: 44,
              color: "#8a8a95",
              fontWeight: 500,
              letterSpacing: "-0.01em",
            }}
          >
            서울시 공무원이 인정한
          </div>
          <div
            style={{
              fontSize: 116,
              fontWeight: 800,
              letterSpacing: "-0.03em",
              lineHeight: 1.0,
              backgroundImage:
                "linear-gradient(135deg, #ff7a4d, #ffd07a 55%, #c2ff5e)",
              backgroundClip: "text",
              color: "transparent",
            }}
          >
            {`서울 맛집 TOP ${total}`}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            borderTop: "1px solid #2a2a32",
            paddingTop: 28,
          }}
        >
          <div style={{ fontSize: 26, color: "#8a8a95" }}>
            서울시·25개 구청 업무추진비 80만 건 분석
          </div>
          <div style={{ fontSize: 26, color: "#8a8a95", fontWeight: 700 }}>
            gongsulrang.vercel.app
          </div>
        </div>
      </div>
    ),
    size,
  );
}
