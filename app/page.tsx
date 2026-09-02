export default function Home() {
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: "48px 24px" }}>
      <section style={{ maxWidth: 760 }}>
        <p style={{ letterSpacing: "0.12em", textTransform: "uppercase", fontSize: 13, marginBottom: 18 }}>
          Research build
        </p>
        <h1 style={{ fontSize: "clamp(42px, 8vw, 82px)", lineHeight: 0.95, margin: 0 }}>
          Write Now Publishing House
        </h1>
        <p style={{ fontSize: 22, lineHeight: 1.5, marginTop: 28 }}>
          Recovering works, witnesses, and readings that fell out of circulation at different layers of transmission.
        </p>
        <p style={{ fontSize: 16, lineHeight: 1.6, opacity: 0.72 }}>
          This deployment is the research surface for the publishing system. Catalog, corpus, reconstruction, and library-delivery interfaces will be added only as their underlying custody models become operational.
        </p>
        <p style={{ marginTop: 32 }}>
          <a
            href="/glyph-atlas"
            style={{
              display: "inline-block",
              color: "inherit",
              textDecoration: "none",
              borderBottom: "1px solid currentColor",
              paddingBottom: 4,
              fontSize: 15,
            }}
          >
            Open Glyph Atlas v0 →
          </a>
        </p>
      </section>
    </main>
  );
}
