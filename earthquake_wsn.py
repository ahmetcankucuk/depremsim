"""
Deprem Erken Uyarı WSN Simülasyonu
====================================
P-dalgası algılayan sensörlerin veri füzyonu, zaman senkronizasyonu,
gecikme analizi ve false alarm oranı simülasyonu.
"""

import random
import math
import json
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum

# ─── Sabitler ───────────────────────────────────────────────
AREA_SIZE       = 500       # 500x500 metre alan
N_SENSORS       = 30        # Sensör sayısı
GATEWAY_POS     = (250, 250)# Gateway konumu (merkez)
P_WAVE_SPEED    = 6000      # m/s  (P-dalgası hızı)
S_WAVE_SPEED    = 3500      # m/s  (S-dalgası hızı)
COMM_RANGE      = 150       # m    (iletişim menzili)
TX_ENERGY       = 0.05      # J/paket (iletim)
RX_ENERGY       = 0.01      # J/paket (alma)
IDLE_ENERGY     = 0.001     # J/s   (bekleme)
INITIAL_ENERGY  = 5.0       # J     (başlangıç enerjisi)
THRESHOLD_MAG   = 2.5       # Minimum algılama büyüklüğü
FALSE_ALARM_PROB= 0.08      # %8 yanlış alarm olasılığı
QUORUM_K        = 3         # Alarm için gereken minimum onaylayan sensör

random.seed(42)

# ─── Veri Yapıları ───────────────────────────────────────────

class SensorState(Enum):
    SLEEP  = "SLEEP"
    ACTIVE = "ACTIVE"
    TX     = "TRANSMITTING"
    DEAD   = "DEAD"

@dataclass
class SeismicPacket:
    sensor_id:    int
    timestamp:    float       # Algılama zamanı (s)
    magnitude:    float       # Yerel büyüklük tahmini
    p_arrival:    float       # P-dalgası varış zamanı
    confidence:   float       # 0-1 güven skoru
    hop_count:    int = 0
    path:         List[int] = field(default_factory=list)

@dataclass
class Sensor:
    id:           int
    x:            float
    y:            float
    energy:       float = INITIAL_ENERGY
    state:        SensorState = SensorState.ACTIVE
    clock_offset: float = 0.0   # Saat kayması (ms)
    packets_sent: int = 0
    packets_recv: int = 0
    false_alarms: int = 0
    true_detections: int = 0
    neighbors:    List[int] = field(default_factory=list)

    def distance_to(self, other: 'Sensor') -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def distance_to_point(self, px: float, py: float) -> float:
        return math.hypot(self.x - px, self.y - py)

    def consume_tx(self):
        self.energy -= TX_ENERGY
        if self.energy <= 0:
            self.energy = 0
            self.state = SensorState.DEAD

    def consume_rx(self):
        self.energy -= RX_ENERGY
        if self.energy <= 0:
            self.energy = 0
            self.state = SensorState.DEAD

    def consume_idle(self, dt: float):
        self.energy -= IDLE_ENERGY * dt
        if self.energy <= 0:
            self.energy = 0
            self.state = SensorState.DEAD

    @property
    def is_alive(self) -> bool:
        return self.state != SensorState.DEAD

# ─── Ağ Kurulumu ─────────────────────────────────────────────

def deploy_sensors(n: int) -> List[Sensor]:
    sensors = []
    for i in range(n):
        x = random.uniform(20, AREA_SIZE - 20)
        y = random.uniform(20, AREA_SIZE - 20)
        offset = random.gauss(0, 2.5)   # ±2.5 ms saat kayması
        sensors.append(Sensor(id=i, x=x, y=y, clock_offset=offset))
    return sensors

def build_topology(sensors: List[Sensor]) -> Dict[int, List[int]]:
    """Her sensörün komşularını belirle (COMM_RANGE içindekiler)"""
    adj = {s.id: [] for s in sensors}
    for i, si in enumerate(sensors):
        for j, sj in enumerate(sensors):
            if i != j and si.distance_to(sj) <= COMM_RANGE:
                adj[si.id].append(sj.id)
        si.neighbors = adj[si.id]
    return adj

# ─── Deprem Olayı ────────────────────────────────────────────

@dataclass
class EarthquakeEvent:
    epicenter_x:  float
    epicenter_y:  float
    magnitude:    float
    depth_km:     float
    origin_time:  float = 0.0

    def p_wave_arrival(self, sensor: Sensor) -> float:
        dist = sensor.distance_to_point(self.epicenter_x, self.epicenter_y)
        hypo  = math.hypot(dist, self.depth_km * 1000)
        return self.origin_time + hypo / P_WAVE_SPEED

    def s_wave_arrival(self, sensor: Sensor) -> float:
        dist = sensor.distance_to_point(self.epicenter_x, self.epicenter_y)
        hypo  = math.hypot(dist, self.depth_km * 1000)
        return self.origin_time + hypo / S_WAVE_SPEED

    def local_magnitude(self, sensor: Sensor) -> float:
        dist = max(sensor.distance_to_point(self.epicenter_x, self.epicenter_y), 1)
        atten = -0.8 * math.log10(dist / 100)
        noise = random.gauss(0, 0.2)
        return max(0, self.magnitude + atten + noise)

# ─── Zaman Senkronizasyonu (TPSN-benzeri) ───────────────────

def tpsn_sync(sensors: List[Sensor], adj: Dict) -> Dict[int, float]:
    """
    Basitleştirilmiş TPSN: Gateway (merkez düğüm) zamanı referans alır,
    BFS ile senkronizasyon yayılır. Düzeltme sonrası artık hata döner.
    """
    ref_time = 0.0
    sync_errors = {}
    visited = set()
    queue = [-1]     # -1 = gateway
    level_offsets = {-1: 0.0}

    # Gateway'den BFS
    bfs_q = [(-1, 0.0)]
    visited.add(-1)

    sensor_map = {s.id: s for s in sensors}

    while bfs_q:
        node_id, parent_offset = bfs_q.pop(0)
        if node_id == -1:
            neighbors = [s.id for s in sensors
                         if math.hypot(s.x - GATEWAY_POS[0], s.y - GATEWAY_POS[1]) <= COMM_RANGE]
        else:
            neighbors = adj.get(node_id, [])

        for nid in neighbors:
            if nid not in visited:
                visited.add(nid)
                s = sensor_map[nid]
                prop_delay = (math.hypot(s.x - GATEWAY_POS[0], s.y - GATEWAY_POS[1])
                              / 3e8 * 1000)  # ms
                raw_offset = s.clock_offset
                corrected  = raw_offset - parent_offset - prop_delay
                sync_errors[nid] = corrected
                s.clock_offset = corrected  # uygula
                bfs_q.append((nid, corrected))

    # Senkronize edilemeyen düğümler
    for s in sensors:
        if s.id not in sync_errors:
            sync_errors[s.id] = s.clock_offset

    return sync_errors

# ─── Yönlendirme: En Kısa Yol (Dijkstra) ───────────────────

def dijkstra(src: int, sensors: List[Sensor], adj: Dict) -> Dict[int, List[int]]:
    sensor_map = {s.id: s for s in sensors}
    dist   = {s.id: float('inf') for s in sensors}
    prev   = {s.id: None for s in sensors}
    dist[src] = 0
    unvisited  = set(s.id for s in sensors if s.is_alive)

    while unvisited:
        u = min(unvisited, key=lambda x: dist[x])
        if dist[u] == float('inf'):
            break
        unvisited.remove(u)
        for v in adj.get(u, []):
            if v in unvisited and sensor_map[v].is_alive:
                alt = dist[u] + 1
                if alt < dist[v]:
                    dist[v] = alt
                    prev[v] = u

    # Tüm düğümlere yol oluştur
    paths = {}
    for target in [s.id for s in sensors]:
        path = []
        cur  = target
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        if path[0] == src:
            paths[target] = path
    return paths

# ─── Algılama & Alarm ────────────────────────────────────────

def detect_and_report(
    sensors:  List[Sensor],
    quake:    EarthquakeEvent,
    adj:      Dict,
    sim_time: float
) -> Dict:
    """
    Her sensör P-dalgasını algılar → paket oluşturur → gateway'e iletir.
    Quorum mekanizması: K farklı sensör onaylarsa gerçek alarm verilir.
    """
    sensor_map   = {s.id: s for s in sensors}
    detections   = []
    false_alarms = []
    all_packets  = []
    latencies    = []
    gateway_recv = []

    paths_from = {}   # kaynak → yol haritası (cache)

    for s in sensors:
        if not s.is_alive:
            continue

        p_arr  = quake.p_wave_arrival(s)
        loc_m  = quake.local_magnitude(s)

        # Sensörün algılayıp algılamadığı
        if loc_m < THRESHOLD_MAG:
            # Yanlış alarm mı?
            if random.random() < FALSE_ALARM_PROB:
                s.false_alarms += 1
                false_alarms.append(s.id)
                pkt = SeismicPacket(
                    sensor_id=s.id,
                    timestamp=p_arr + s.clock_offset / 1000,
                    magnitude=random.uniform(THRESHOLD_MAG, THRESHOLD_MAG + 0.5),
                    p_arrival=p_arr,
                    confidence=random.uniform(0.3, 0.6)
                )
                all_packets.append(pkt)
            continue

        # Gerçek algılama
        s.true_detections += 1
        detections.append(s.id)

        pkt = SeismicPacket(
            sensor_id=s.id,
            timestamp=p_arr + s.clock_offset / 1000,
            magnitude=loc_m,
            p_arrival=p_arr,
            confidence=min(1.0, loc_m / quake.magnitude),
            path=[s.id]
        )

        # Multi-hop iletim (Dijkstra rota)
        if s.id not in paths_from:
            paths_from[s.id] = dijkstra(s.id, sensors, adj)

        # Gateway'e en yakın sensör üzerinden iletilebilir mi?
        # Basit greedy hop: komşular arasında gateway'e en yakın olanı seç
        current  = s.id
        visited_route = set([s.id])
        hops     = 0
        reached  = False
        prop_ms  = 0.0

        while hops < 10:
            cx = sensor_map[current].x
            cy = sensor_map[current].y
            gd = math.hypot(cx - GATEWAY_POS[0], cy - GATEWAY_POS[1])

            if gd <= COMM_RANGE:
                # Gateway'e direkt ulaş
                sensor_map[current].consume_tx()
                prop_ms += gd / 3e8 * 1000 + 1  # 1ms işlem gecikmesi
                pkt.hop_count = hops + 1
                reached = True
                break

            best_next = None
            best_dist = gd
            for nb_id in adj.get(current, []):
                nb = sensor_map[nb_id]
                if nb.is_alive and nb_id not in visited_route:
                    nd = math.hypot(nb.x - GATEWAY_POS[0], nb.y - GATEWAY_POS[1])
                    if nd < best_dist:
                        best_dist = nd
                        best_next  = nb_id

            if best_next is None:
                break

            # TX/RX enerji harcama
            sensor_map[current].consume_tx()
            sensor_map[best_next].consume_rx()
            hop_dist = math.hypot(
                sensor_map[current].x - sensor_map[best_next].x,
                sensor_map[current].y - sensor_map[best_next].y
            )
            prop_ms += hop_dist / 3e8 * 1000 + 1
            pkt.path.append(best_next)
            visited_route.add(best_next)
            current = best_next
            hops   += 1
            s.packets_sent += 1

        if reached:
            total_latency = (p_arr - quake.origin_time) * 1000 + prop_ms  # ms
            latencies.append(total_latency)
            gateway_recv.append(pkt)
            all_packets.append(pkt)

    # Quorum kontrolü: K'dan fazla sensör alarm verdiyse gerçek alarm
    real_alarm = len(gateway_recv) >= QUORUM_K
    false_alarm_count = len(false_alarms)

    # Veri füzyonu: ağırlıklı ortalama magnitude
    if gateway_recv:
        total_conf = sum(p.confidence for p in gateway_recv)
        fused_mag  = sum(p.magnitude * p.confidence for p in gateway_recv) / total_conf
        earliest_p = min(p.p_arrival for p in gateway_recv)
        s_arr_est  = earliest_p + math.hypot(
            (quake.epicenter_x - GATEWAY_POS[0]),
            (quake.epicenter_y - GATEWAY_POS[1])
        ) * (1/S_WAVE_SPEED - 1/P_WAVE_SPEED)
        warning_window = max(0, (s_arr_est - (earliest_p + max(latencies)/1000 if latencies else 0)))
    else:
        fused_mag = 0
        warning_window = 0

    return {
        "real_alarm":       real_alarm,
        "detections":       len(detections),
        "false_alarms":     false_alarm_count,
        "packets_reached":  len(gateway_recv),
        "avg_latency_ms":   sum(latencies) / len(latencies) if latencies else 0,
        "min_latency_ms":   min(latencies) if latencies else 0,
        "max_latency_ms":   max(latencies) if latencies else 0,
        "fused_magnitude":  fused_mag,
        "warning_window_s": warning_window,
        "alive_sensors":    sum(1 for s in sensors if s.is_alive),
        "dead_sensors":     sum(1 for s in sensors if not s.is_alive),
        "avg_energy":       sum(s.energy for s in sensors) / len(sensors),
        "total_true_det":   sum(s.true_detections for s in sensors),
        "total_false_alm":  sum(s.false_alarms for s in sensors),
    }

# ─── Ana Simülasyon ─────────────────────────────────────────

def run_simulation():
    print("=" * 60)
    print("  DEPREM ERKEN UYARI WSN SİMÜLASYONU")
    print("=" * 60)

    # 1. Sensörleri yerleştir
    sensors = deploy_sensors(N_SENSORS)
    adj     = build_topology(sensors)

    print(f"\n[KURULUM] {N_SENSORS} sensör yerleştirildi.")
    print(f"  Ortalama komşu sayısı: {sum(len(v) for v in adj.values())/N_SENSORS:.1f}")
    isolated = sum(1 for v in adj.values() if len(v) == 0)
    print(f"  İzole sensör sayısı  : {isolated}")

    # 2. Zaman senkronizasyonu
    print("\n[TPSN SENKRONIZASYON] Saat ofsetleri düzeltiliyor...")
    before_sync = [abs(s.clock_offset) for s in sensors]
    sync_errors = tpsn_sync(sensors, adj)
    after_sync  = [abs(v) for v in sync_errors.values()]
    print(f"  Senkronizasyon öncesi ort. hata : {sum(before_sync)/len(before_sync):.2f} ms")
    print(f"  Senkronizasyon sonrası ort. hata: {sum(after_sync)/len(after_sync):.4f} ms")

    # 3. Birden fazla deprem senaryosu
    scenarios = [
        EarthquakeEvent(100, 100, 4.5, 10, 0.0),   # Köşede küçük deprem
        EarthquakeEvent(250, 250, 6.2, 15, 0.0),   # Merkezde büyük deprem
        EarthquakeEvent(450, 50,  3.8, 8,  0.0),   # Sınırda orta deprem
        EarthquakeEvent(130, 380, 5.0, 20, 0.0),   # Derin ve uzak
    ]

    all_results = []
    print("\n" + "─" * 60)

    for i, quake in enumerate(scenarios):
        # Her senaryo için sensörleri sıfırla
        fresh_sensors = deploy_sensors(N_SENSORS)
        tpsn_sync(fresh_sensors, adj)

        print(f"\n[SENARYO {i+1}] M{quake.magnitude:.1f} @ "
              f"({quake.epicenter_x:.0f},{quake.epicenter_y:.0f}) "
              f"Derinlik: {quake.depth_km} km")

        result = detect_and_report(fresh_sensors, quake, adj, sim_time=0.0)
        all_results.append(result)

        alarm_str = "✓ GERÇEK ALARM" if result["real_alarm"] else "✗ ALARM YOK"
        print(f"  Alarm Durumu      : {alarm_str}")
        print(f"  Algılayan sensör  : {result['detections']}/{N_SENSORS}")
        print(f"  Gateway'e ulaşan  : {result['packets_reached']} paket")
        print(f"  Ortalama gecikme  : {result['avg_latency_ms']:.1f} ms")
        print(f"  Min / Max gecikme : {result['min_latency_ms']:.1f} / {result['max_latency_ms']:.1f} ms")
        print(f"  Yanlış alarm      : {result['false_alarms']}")
        print(f"  Füze büyüklük     : {result['fused_magnitude']:.2f} (gerçek: {quake.magnitude})")
        print(f"  Uyarı penceresi   : {result['warning_window_s']:.1f} s")
        print(f"  Ort. enerji kalan : {result['avg_energy']:.3f} J")
        print(f"  Hayatta sensör    : {result['alive_sensors']}/{N_SENSORS}")

    # 4. Özet istatistikler
    print("\n" + "=" * 60)
    print("  GENEL ÖZET")
    print("=" * 60)
    total_det     = sum(r["detections"] for r in all_results)
    total_packets = sum(r["packets_reached"] for r in all_results)
    avg_lat       = sum(r["avg_latency_ms"] for r in all_results) / len(all_results)
    total_false   = sum(r["false_alarms"] for r in all_results)
    alarms_ok     = sum(1 for r in all_results if r["real_alarm"])

    print(f"  Toplam senaryo      : {len(scenarios)}")
    print(f"  Başarılı alarm      : {alarms_ok}/{len(scenarios)}")
    print(f"  Toplam algılama     : {total_det}")
    print(f"  Toplam yanlış alarm : {total_false}")
    print(f"  Ortalama gecikme    : {avg_lat:.1f} ms")
    print(f"  Toplam iletilen pkt : {total_packets}")
    print(f"  False alarm oranı   : {total_false/(total_det+total_false)*100:.1f}%"
          if (total_det + total_false) > 0 else "  False alarm oranı: N/A")

    # 5. JSON çıktısı
    output = {
        "config": {
            "n_sensors": N_SENSORS,
            "area_size": AREA_SIZE,
            "comm_range": COMM_RANGE,
            "quorum_k": QUORUM_K,
            "threshold_magnitude": THRESHOLD_MAG,
        },
        "sync": {
            "before_avg_error_ms": sum(before_sync)/len(before_sync),
            "after_avg_error_ms":  sum(after_sync)/len(after_sync),
        },
        "scenarios": [
            {
                "id": i+1,
                "magnitude": scenarios[i].magnitude,
                "epicenter": [scenarios[i].epicenter_x, scenarios[i].epicenter_y],
                "depth_km": scenarios[i].depth_km,
                **all_results[i]
            }
            for i in range(len(scenarios))
        ]
    }

    with open("/mnt/user-data/outputs/wsn_earthquake_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n[ÇIKTI] Sonuçlar wsn_earthquake_results.json dosyasına kaydedildi.")
    return output

if __name__ == "__main__":
    results = run_simulation()
