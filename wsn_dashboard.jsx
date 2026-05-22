import { useState, useEffect, useRef } from "react";

const AREA = 500;
const GATEWAY = { x: 250, y: 250 };
const COMM_RANGE = 150;

function seededRandom(seed) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    return (s >>> 0) / 4294967296;
  };
}

function generateSensors() {
  const rng = seededRandom(42);
  return Array.from({ length: 30 }, (_, i) => ({
    id: i,
    x: 20 + rng() * 460,
    y: 20 + rng() * 460,
    energy: 5.0,
    state: "ACTIVE",
    detected: false,
    sent: false,
  }));
}

const SCENARIOS = [
  { id: 1, label: "M4.5 – Köşe", mag: 4.5, ex: 100, ey: 100, depth: 10, lat: 1669, packets: 26, fused: 4.29, alive: 30 },
  { id: 2, label: "M6.2 – Merkez", mag: 6.2, ex: 250, ey: 250, depth: 15, lat: 2502, packets: 29, fused: 6.06, alive: 30 },
];

function magColor(m) {
  if (m >= 6) return "#ff2d55";
  if (m >= 5) return "#ff9500";
  if (m >= 4) return "#ffcc00";
  return "#34c759";
}

export default function EducationalEarthquakeWSN() {
  const [activeScenario, setActiveScenario] = useState(null);
  const [animStep, setAnimStep] = useState(0); 
  const [sensors, setSensors] = useState(generateSensors());
  const [waveRadius, setWaveRadius] = useState(0);
  const [routeLines, setRouteLines] = useState([]);
  const [alarmFired, setAlarmFired] = useState(false);
  const animRef = useRef(null);
  const svgSize = 420;
  const scale = svgSize / AREA;

  function sc(v) { return v * scale; }

  function resetSim() {
    setAnimStep(0);
    setWaveRadius(0);
    setRouteLines([]);
    setAlarmFired(false);
    setSensors(generateSensors());
    setActiveScenario(null);
    clearInterval(animRef.current);
  }

  function runScenario(sc_data) {
    resetSim();
    setTimeout(() => {
      setActiveScenario(sc_data);
      startAnimation(sc_data);
    }, 100);
  }

  function startAnimation(sc_data) {
    let step = 0;
    const epicenter = { x: sc_data.ex, y: sc_data.ey };

    animRef.current = setInterval(() => {
      step++;

      if (step <= 40) {
        setAnimStep(1); // Dalga yayılımı
        setWaveRadius(r => r + 12);
        const newR = (step) * 12;
        setSensors(prev => prev.map(s => {
          const d = Math.hypot(s.x - epicenter.x, s.y - epicenter.y);
          if (d <= newR && s.state === "ACTIVE") return { ...s, detected: true };
          return s;
        }));
      } else if (step <= 55) {
        setAnimStep(3); // Multi-hop Yönlendirme
        setSensors(prev => prev.map(s => s.detected && !s.sent ? { ...s, sent: true } : s));
        setSensors(prev => {
          const lines = [];
          prev.forEach(s => {
            if (s.sent) {
              let cur = { x: s.x, y: s.y };
              for (let h = 0; h < 4; h++) {
                const gd = Math.hypot(cur.x - GATEWAY.x, cur.y - GATEWAY.y);
                if (gd <= COMM_RANGE) {
                  lines.push({ x1: cur.x, y1: cur.y, x2: GATEWAY.x, y2: GATEWAY.y, id: s.id + "_" + h });
                  break;
                }
                const neighbors = prev.filter(nb => Math.hypot(nb.x - cur.x, nb.y - cur.y) <= COMM_RANGE);
                const best = neighbors.reduce((b, nb) => {
                  const d = Math.hypot(nb.x - GATEWAY.x, nb.y - GATEWAY.y);
                  return d < Math.hypot(b.x - GATEWAY.x, b.y - GATEWAY.y) ? nb : b;
                }, { x: cur.x, y: cur.y, id: -1 });
                if (best.id === -1) break;
                lines.push({ x1: cur.x, y1: cur.y, x2: best.x, y2: best.y, id: s.id + "_" + h });
                cur = best;
              }
            }
          });
          setRouteLines(lines);
          return prev;
        });
      } else if (step <= 70) {
        setAnimStep(4); // Alarm
        setAlarmFired(true);
      } else {
        clearInterval(animRef.current);
      }
    }, 80);
  }

  useEffect(() => () => clearInterval(animRef.current), []);

  // Eğitici Metin İçerikleri
  const getEducationalContent = () => {
    switch(animStep) {
      case 0:
        return {
          title: "Sistem Beklemede",
          text: "Sensörler şu an uyku modunda (Sleep State). Sadece sismik bir aktivite algıladıklarında uyanarak enerji tasarrufu yaparlar. Bir senaryo seçerek simülasyonu başlatın."
        };
      case 1:
        return {
          title: "1. Adım: P-Dalgası Yayılımı",
          text: "Deprem gerçekleşti! Yıkıcı olan S-dalgalarından önce, daha hızlı olan P-dalgaları (6000 m/s) sensörlere ulaşır. Sensörler titreşimi algılayıp uyanır."
        };
      case 3:
        return {
          title: "2. Adım: Multi-Hop Yönlendirme (Dijkstra)",
          text: "Uyanan sensörler Gateway'e (Merkez) çok uzak olabilir. Verilerini komşu sensörler üzerinden atlatarak (Multi-Hop) merkeze iletirler. Kesikli çizgiler verinin izlediği en kısa rotayı gösterir."
        };
      case 4:
        return {
          title: "3. Adım: Veri Füzyonu ve Alarm",
          text: "Gateway verileri topladı. Yanlış alarmı önlemek için 'Quorum' mantığı çalışır: En az 3 farklı sensörden (K=3) veri gelirse sistem doğrulanır ve erken uyarı alarmı verilir!"
        };
      default: return {title: "", text: ""};
    }
  };

  const eduInfo = getEducationalContent();

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a1a", fontFamily: "monospace", color: "#e0e8ff", padding: "24px" }}>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, color: "#4488ff", margin: 0 }}>WSN DEPREM ERKEN UYARI SİSTEMİ</h1>
        <div style={{ color: "#6688aa", marginTop: 6 }}>Etkileşimli Ağ Algoritmaları Simülasyonu</div>
      </div>

      <div style={{ display: "flex", gap: 12, justifyContent: "center", marginBottom: 28 }}>
        {SCENARIOS.map(s => (
          <button key={s.id} onClick={() => runScenario(s)} style={{ padding: "10px 18px", background: "#112233", color: "#fff", border: "none", cursor: "pointer" }}>
            {s.label} Başlat
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 24, justifyContent: "center", flexWrap: "wrap" }}>
        
        {/* SVG Harita (Sol Taraf) */}
        <div style={{ background: "#08101e", border: "1px solid #1e3050", padding: 16, borderRadius: 8, position: "relative" }}>
          {alarmFired && (
            <div style={{ position: "absolute", top: 10, left: "50%", transform: "translateX(-50%)", background: "#ff2d55", color: "#fff", padding: "4px 12px", borderRadius: 4, zIndex: 10 }}>
              ⚠ ALARM ONAYLANDI
            </div>
          )}
          <svg width={svgSize} height={svgSize}>
            {/* Bağlantılar */}
            {sensors.map(s => sensors.filter(nb => nb.id > s.id && Math.hypot(s.x-nb.x, s.y-nb.y) <= COMM_RANGE).map(nb => (
                <line key={`${s.id}-${nb.id}`} x1={sc(s.x)} y1={sc(s.y)} x2={sc(nb.x)} y2={sc(nb.y)} stroke="#0d2540" />
            )))}
            
            {/* Dalga */}
            {waveRadius > 0 && <circle cx={sc(activeScenario.ex)} cy={sc(activeScenario.ey)} r={sc(waveRadius)} fill="none" stroke="#ffcc00" strokeWidth={2} opacity={0.7} />}
            
            {/* Rota */}
            {routeLines.map(l => <line key={l.id} x1={sc(l.x1)} y1={sc(l.y1)} x2={sc(l.x2)} y2={sc(l.y2)} stroke="#44aaff" strokeWidth={2} strokeDasharray="4" />)}
            
            {/* Sensörler */}
            {sensors.map(s => <circle key={s.id} cx={sc(s.x)} cy={sc(s.y)} r={5} fill={s.detected ? "#ffcc00" : "#1a3060"} />)}
            
            {/* Gateway */}
            <circle cx={sc(GATEWAY.x)} cy={sc(GATEWAY.y)} r={8} fill="#ff2d55" />
          </svg>
        </div>

        {/* Eğitici Panel (Sağ Taraf) */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16, width: 350 }}>
          <div style={{ background: "#08101e", border: "1px solid #4488ff", padding: 20, borderRadius: 8 }}>
            <h3 style={{ color: "#4488ff", marginTop: 0 }}>📖 Simülasyon Rehberi</h3>
            <h4 style={{ color: "#fff" }}>{eduInfo.title}</h4>
                        <p style={{ color: "#8899bb", lineHeight: "1.5" }}>{eduInfo.text}</p>
            {animStep >= 3 && (
                <>
                <br/>
                                </>
            )}
          </div>
          
          {/* İstatistikler */}
          <div style={{ background: "#08101e", border: "1px solid #1e3050", padding: 20, borderRadius: 8 }}>
            <h3 style={{ color: "#4466aa", marginTop: 0 }}>📊 Canlı Veriler</h3>
            <p>Aktif Sensör: {sensors.filter(s => s.detected).length} / 30</p>
            <p>İletilen Paket: {routeLines.length}</p>
          </div>
        </div>

      </div>
    </div>
  );
}