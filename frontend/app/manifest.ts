import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "RoadSoS — Emergency Response",
    short_name: "RoadSoS",
    description: "AI-powered emergency response companion",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#0F172A",
    theme_color: "#DC2626",
    categories: ["health", "utilities", "safety"],
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
    ],
    shortcuts: [
      { name: "SOS Emergency", short_name: "SOS", url: "/?sos=1", icons: [{ src: "/icon-192.png", sizes: "192x192" }] },
    ],
  };
}
