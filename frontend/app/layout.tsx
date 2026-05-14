import type { Metadata, Viewport } from "next";
import "./globals.css";
import LayoutWrapper from "./layout-wrapper";

export const metadata: Metadata = {
  title: "RoadSoS — Emergency Response",
  description: "AI-powered emergency response companion. One tap saves lives.",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "RoadSoS" },
  other: { "mobile-web-app-capable": "yes" },
  openGraph: {
    title: "RoadSoS — AI Emergency Response",
    description: "Save lives in the Golden Hour with AI-powered triage and dispatch",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
  themeColor: "#DC2626",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="robots" content="noindex, nofollow" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                  navigator.serviceWorker.register('/sw.js')
                    .then(r => console.debug('RoadSoS SW registered:', r.scope))
                    .catch(e => console.warn('SW registration failed:', e));
                });
              }
            `,
          }}
        />
      </head>
      <body>
        <LayoutWrapper>{children}</LayoutWrapper>
      </body>
    </html>
  );
}