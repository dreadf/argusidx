"use client";

/**
 * Root-layout error boundary. error.tsx wraps page.js and nested layout.js
 * files, but never the layout.js in its own segment, so a failure in
 * app/layout.tsx or AppShell itself (e.g. its getSearchIndex() read) would
 * otherwise skip error.tsx entirely and fall through to Next's bare,
 * unstyled default. Next's own requirement: this file replaces the root
 * layout when active, so it renders its own <html>/<body> and gets none of
 * globals.css or the app's fonts, only inline styles.
 */
export default function GlobalError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <html lang="id">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          padding: 24,
          textAlign: "center",
          background: "#0a0a0a",
          color: "#e8e8e8",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }}
      >
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>ArgusIDX sedang bermasalah</h1>
        <p style={{ fontSize: 13.5, color: "#a3a3a3", maxWidth: 320, margin: 0, lineHeight: 1.5 }}>
          Halaman gagal dimuat sepenuhnya. Coba lagi sebentar lagi.
          {error.digest && <span style={{ display: "block", marginTop: 4, fontFamily: "monospace", fontSize: 11, color: "#737373" }}>Kode: {error.digest}</span>}
        </p>
        <button
          type="button"
          onClick={() => retry()}
          style={{
            marginTop: 8,
            minHeight: 44,
            padding: "0 20px",
            borderRadius: 8,
            border: "none",
            background: "#3b82f6",
            color: "#fff",
            fontSize: 13.5,
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          Coba lagi
        </button>
      </body>
    </html>
  );
}
