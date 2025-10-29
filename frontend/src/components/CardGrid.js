import { useNavigate } from "react-router-dom";

export default function CardGrid() {
  const nav = useNavigate();

  const items = [
    { title: "Start Upload", desc: "Upload FASTQ/FASTA/POD5", to: "/upload" },
    { title: "Run Analysis", desc: "QC, Filter, BLAST", to: "/analysis" }, // 
    { title: "View Results", desc: "Charts & Reports", to: "/results" },
    { title: "Docs", desc: "How to use iONspID", to: "/" },
  ];

  return (
    <div style={{
      maxWidth: 1400, margin: "24px auto",
      display: "grid", gap: 16,
      gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))"
    }}>
      {items.map((it, i) => (
        <div key={i}
          onClick={() => nav(it.to)}
          style={{
            cursor: "pointer",
            background: "#fff",
            borderRadius: 12,
            padding: 18,
            boxShadow: "0 6px 16px rgba(0,0,0,.12)",
            transition: "transform .15s ease"
          }}
          onMouseEnter={e => e.currentTarget.style.transform = "translateY(-4px)"}
          onMouseLeave={e => e.currentTarget.style.transform = "translateY(0)"}
        >
          <h3 style={{ margin: "0 0 6px", fontSize: "clamp(16px,1.4vw,20px)" }}>{it.title}</h3>
          <p style={{ margin: 0, color: "#444", fontSize: "clamp(13px,1.1vw,16px)" }}>{it.desc}</p>
        </div>
      ))}
    </div>
  );
}
