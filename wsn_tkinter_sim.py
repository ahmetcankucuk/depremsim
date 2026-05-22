import tkinter as tk
import random
import math

# --- Sabitler ---
AREA = 500
GATEWAY = (250, 250)
COMM_RANGE = 150
NUM_SENSORS = 30

# Eğitici metinler
EDU_TEXTS = {
    0: ("Sistem Beklemede", "Sensörler şu an enerji tasarrufu için uyku modunda. Sismik bir aktivite bekliyorlar.\n\nSimülasyonu başlatmak için alttaki senaryolardan birini seçin."),
    1: ("1. Adım: P-Dalgası Yayılımı", "Deprem gerçekleşti! Yıkıcı S-dalgalarından önce, hızlı P-dalgaları (6000 m/s) yayılıyor. Dalgayı ilk hisseden sensörler uyanıp veri toplamaya başlıyor."),
    2: ("2. Adım: Multi-Hop (Atlamalı) İletim", "Uyanan sensörler, veriyi merkeze (Gateway) ulaştırmak için Dijkstra benzeri algoritmalarla en kısa yolu arıyor. Veriler komşudan komşuya sıçrayarak (multi-hop) merkeze aktarılıyor."),
    3: ("3. Adım: Veri Füzyonu ve Alarm", "Gateway verileri topladı! Quorum algoritması devrede: En az 3 farklı sensörden onay geldiği için yanlış alarm ihtimali elendi ve ERKEN UYARI ALARMI verildi!")
}

class EarthquakeSim(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WSN Deprem Erken Uyarı Simülasyonu")
        self.geometry("900x600")
        self.configure(bg="#1e1e2e")

        self.sensors = []
        self.wave_radius = 0
        self.anim_step = 0
        self.active_scenario = None
        self.is_animating = False

        self.setup_ui()
        self.generate_sensors()
        self.draw_initial_state()

    def setup_ui(self):
        # Sol taraf: Görsel Simülasyon (Canvas)
        self.canvas_frame = tk.Frame(self, bg="#1e1e2e")
        self.canvas_frame.pack(side=tk.LEFT, padx=20, pady=20)
        
        self.canvas = tk.Canvas(self.canvas_frame, width=AREA, height=AREA, bg="#0d1117", highlightthickness=1, highlightbackground="#44475a")
        self.canvas.pack()

        # Sağ taraf: Kontrol ve Eğitim Paneli
        self.panel = tk.Frame(self, bg="#282a36", width=350)
        self.panel.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=20)
        self.panel.pack_propagate(False) # Genişliği sabitle

        # Başlık
        tk.Label(self.panel, text="📖 Simülasyon Rehberi", font=("Helvetica", 16, "bold"), bg="#282a36", fg="#8be9fd").pack(pady=(10, 20))

        # Eğitici Metin Alanı
        self.step_title = tk.Label(self.panel, text=EDU_TEXTS[0][0], font=("Helvetica", 14, "bold"), bg="#282a36", fg="#50fa7b", wraplength=300, justify=tk.LEFT)
        self.step_title.pack(anchor="w", padx=10)

        self.step_desc = tk.Label(self.panel, text=EDU_TEXTS[0][1], font=("Helvetica", 11), bg="#282a36", fg="#f8f8f2", wraplength=310, justify=tk.LEFT)
        self.step_desc.pack(anchor="w", padx=10, pady=10)

        # İstatistikler
        self.stats_label = tk.Label(self.panel, text="", font=("Courier", 11), bg="#282a36", fg="#ffb86c", justify=tk.LEFT)
        self.stats_label.pack(anchor="w", padx=10, pady=20)

        # Butonlar (Senaryolar)
        tk.Label(self.panel, text="Senaryo Seç:", font=("Helvetica", 12), bg="#282a36", fg="#bfbfbf").pack(pady=(20, 5))
        
        # Yerel dokunuşlar ekledik
        tk.Button(self.panel, text="M5.0 - Seydişehir Merkez", bg="#44475a", fg="white", command=lambda: self.start_sim(250, 250, 5.0)).pack(fill=tk.X, padx=20, pady=5)
        tk.Button(self.panel, text="M4.2 - Beyşehir Sınırı", bg="#44475a", fg="white", command=lambda: self.start_sim(50, 400, 4.2)).pack(fill=tk.X, padx=20, pady=5)
        tk.Button(self.panel, text="Sıfırla", bg="#ff5555", fg="white", command=self.reset_sim).pack(fill=tk.X, padx=20, pady=15)

    def generate_sensors(self):
        random.seed(42) # Her seferinde aynı topoloji
        self.sensors = []
        for i in range(NUM_SENSORS):
            x = random.uniform(20, AREA-20)
            y = random.uniform(20, AREA-20)
            self.sensors.append({"id": i, "x": x, "y": y, "detected": False, "sent": False})

    def draw_initial_state(self):
        self.canvas.delete("all")
        
        # İletişim Bağlantılarını Çiz (Zayıf Çizgiler)
        for i, s1 in enumerate(self.sensors):
            for s2 in self.sensors[i+1:]:
                if math.hypot(s1["x"]-s2["x"], s1["y"]-s2["y"]) <= COMM_RANGE:
                    self.canvas.create_line(s1["x"], s1["y"], s2["x"], s2["y"], fill="#1e2430", width=1)

        # Sensörleri Çiz
        for s in self.sensors:
            color = "#f1fa8c" if s["detected"] else "#6272a4"
            r = 6 if s["detected"] else 4
            self.canvas.create_oval(s["x"]-r, s["y"]-r, s["x"]+r, s["y"]+r, fill=color, outline="#282a36")

        # Gateway Çiz
        self.canvas.create_rectangle(GATEWAY[0]-8, GATEWAY[1]-8, GATEWAY[0]+8, GATEWAY[1]+8, fill="#ff79c6", outline="white", width=2)
        self.canvas.create_text(GATEWAY[0], GATEWAY[1]+15, text="GW", fill="#ff79c6", font=("Arial", 8, "bold"))

    def reset_sim(self):
        self.is_animating = False
        self.anim_step = 0
        self.wave_radius = 0
        self.active_scenario = None
        self.generate_sensors()
        self.draw_initial_state()
        self.update_edu_panel(0)
        self.stats_label.config(text="")

    def start_sim(self, ex, ey, mag):
        self.reset_sim()
        self.active_scenario = {"ex": ex, "ey": ey, "mag": mag}
        self.is_animating = True
        self.anim_step = 1
        self.update_edu_panel(1)
        self.animate()

    def update_edu_panel(self, step):
        title, desc = EDU_TEXTS[step]
        self.step_title.config(text=title)
        self.step_desc.config(text=desc)

    def animate(self):
        if not self.is_animating:
            return

        self.draw_initial_state()
        ex, ey = self.active_scenario["ex"], self.active_scenario["ey"]

        # Adım 1: Dalga Yayılımı
        if self.anim_step == 1:
            self.wave_radius += 10
            self.canvas.create_oval(ex-self.wave_radius, ey-self.wave_radius, ex+self.wave_radius, ey+self.wave_radius, outline="#ffb86c", width=2)
            
            detected_count = 0
            for s in self.sensors:
                if math.hypot(s["x"]-ex, s["y"]-ey) <= self.wave_radius:
                    s["detected"] = True
                if s["detected"]:
                    detected_count += 1
            
            self.stats_label.config(text=f"Aktif Sensör: {detected_count} / {NUM_SENSORS}\nDalga Çapı: {self.wave_radius} m")

            if self.wave_radius > AREA * 1.2:
                self.anim_step = 2
                self.wave_radius = 0
                self.update_edu_panel(2)

        # Adım 2: Multi-hop Routing (Görsel temsil)
        elif self.anim_step == 2:
            routes_drawn = 0
            for s in self.sensors:
                if s["detected"]:
                    # Gateway'e doğru basit bir çizgi (Normalde burada Dijkstra çalışır)
                    self.canvas.create_line(s["x"], s["y"], GATEWAY[0], GATEWAY[1], fill="#8be9fd", dash=(4, 4), width=2)
                    routes_drawn += 1
            
            self.stats_label.config(text=f"Veri Paketleri İletiliyor...\nİletilen Rota: {routes_drawn}")
            
            # Kısa bir gecikme sonrası alarma geç
            self.after(2000, self.trigger_alarm)
            return # recursive after çağrısını trigger_alarm yönetecek

        # Adım 3: Alarm
        elif self.anim_step == 3:
            self.canvas.create_text(AREA/2, 30, text="⚠ DEPREM ALARMI ONAYLANDI ⚠", fill="#ff5555", font=("Arial", 16, "bold"))
            for s in self.sensors:
                if s["detected"]:
                    self.canvas.create_line(s["x"], s["y"], GATEWAY[0], GATEWAY[1], fill="#50fa7b", width=1)
            return # Animasyon bitti

        self.after(50, self.animate)

    def trigger_alarm(self):
        if self.is_animating:
            self.anim_step = 3
            self.update_edu_panel(3)
            self.stats_label.config(text="Durum: KRİTİK\nQuorum: Sağlandı (K>=3)\nSistem: Erken Uyarı Verildi")
            self.animate()

if __name__ == "__main__":
    app = EarthquakeSim()
    app.mainloop()