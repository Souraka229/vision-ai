import { useState } from "react";
import { Activity, Camera, Cpu, Hand, MemoryStick, Play, Square, Timer } from "lucide-react";
import { api, fmtTime, Status } from "./lib";

export const Stat = ({ icon, label, value, unit }: { icon: React.ReactNode; label: string; value: string | number; unit?: string }) => (
  <div className="card fade">
    <div className="flex items-center gap-2 text-xs text-zinc-400">{icon}{label}</div>
    <div className="text-2xl font-semibold mt-1">{value}<span className="text-sm text-zinc-500 ml-1">{unit}</span></div>
  </div>
);

export const Toggle = ({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) => (
  <label className="flex items-center justify-between gap-4 py-2 cursor-pointer">
    <span className="text-sm">{label}</span>
    <button onClick={() => onChange(!on)} className={`w-10 h-5 rounded-full transition-colors ${on ? "bg-accent" : "bg-edge"}`}>
      <span className={`block w-4 h-4 bg-white rounded-full transition-transform mx-0.5 ${on ? "translate-x-5" : ""}`} />
    </button>
  </label>
);

export function Video({ s }: { s: Status }) {
  return (
    <div className="card p-2 relative aspect-[4/3] flex items-center justify-center overflow-hidden">
      {s.running
        ? <img src="/stream.mjpg" className="w-full h-full object-contain rounded-lg" style={{ transform: "scaleX(-1)" }} alt="flux" />
        : <div className="text-zinc-500 text-sm">Caméra arrêtée</div>}
      {s.running && s.settings.camera_source === "phone" && !s.phone.connected &&
        <div className="absolute text-zinc-400 text-sm">En attente du flux du téléphone…</div>}
      {s.running && s.simulate && <span className="absolute top-3 left-3 bg-accent text-black text-xs px-2 py-0.5 rounded">MODE SIMULATION</span>}
    </div>
  );
}

export function EngineButtons({ s }: { s: Status }) {
  const [err, setErr] = useState("");
  const go = (p: string) => api(p, "POST").then(() => setErr("")).catch((e) => setErr(e.message));
  return (
    <div className="flex items-center gap-3">
      {s.running
        ? <button className="btn" onClick={() => go("/api/engine/stop")}><Square size={14} className="inline mr-1" />Arrêter</button>
        : <button className="btn-accent" onClick={() => go("/api/engine/start")}><Play size={14} className="inline mr-1" />Démarrer la caméra</button>}
      {(err || s.error) && <span className="text-sm text-red-400">{err || s.error}</span>}
    </div>
  );
}

export function Overview({ s }: { s: Status }) {
  const m = s.metrics, st = s.state;
  const people = st.objects.filter((o) => o.label === "person").length;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-xl font-semibold">Overview</h1><EngineButtons s={s} /></div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat icon={<Activity size={14} />} label="Système" value={s.running ? "En marche" : "Arrêté"} />
        <Stat icon={<Camera size={14} />} label="Caméra" value={s.running ? (s.simulate ? "Simulation" : "Connectée") : "Non connectée"} />
        <Stat icon={<Hand size={14} />} label="Geste stable" value={st.gesture ?? "aucun"} />
        <Stat icon={<Activity size={14} />} label="Personnes (YOLO)" value={s.settings.modules.objects ? people : "module off"} />
        <Stat icon={<Timer size={14} />} label="FPS" value={m.fps} />
        <Stat icon={<Timer size={14} />} label="Latence" value={m.latency_ms} unit="ms" />
        <Stat icon={<MemoryStick size={14} />} label="RAM (backend)" value={m.ram_mb} unit="Mo" />
        <Stat icon={<Cpu size={14} />} label="CPU (backend)" value={m.cpu} unit="%" />
      </div>
      <div className="card">
        <div className="text-sm text-zinc-400 mb-2">Derniers événements (réels)</div>
        {s.events.filter((e) => ["gesture", "command", "interaction"].includes(e.kind)).length === 0
          ? <div className="text-sm text-zinc-500">Aucun événement pour l'instant.</div>
          : s.events.filter((e) => ["gesture", "command", "interaction"].includes(e.kind)).map((e, i) => (
            <div key={i} className="text-sm flex gap-3 py-0.5"><span className="text-zinc-500">{fmtTime(e.ts)}</span><span className="text-accent">{e.kind}</span><span>{e.name}</span></div>))}
      </div>
    </div>
  );
}

export function Live({ s }: { s: Status }) {
  const mods = s.settings.modules;
  const set = (k: string, v: boolean) => api("/api/settings", "POST", { modules: { [k]: v } });
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-xl font-semibold">Live Vision</h1><EngineButtons s={s} /></div>
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2"><Video s={s} /></div>
        <div className="space-y-3">
          <div className="card"><div className="text-sm text-zinc-400">Modules</div>
            <Toggle on={mods.hands} onChange={(v) => set("hands", v)} label="Mains (MediaPipe)" />
            <Toggle on={mods.objects} onChange={(v) => set("objects", v)} label="Personnes & objets (YOLO)" />
          </div>
          <div className="card text-sm space-y-1">
            <div>FPS : <b>{s.metrics.fps}</b> · Latence : <b>{s.metrics.latency_ms} ms</b></div>
            <div>RAM : <b>{s.metrics.ram_mb} Mo</b> · CPU : <b>{s.metrics.cpu}%</b></div>
            {s.state.hands.length === 0 ? <div className="text-zinc-500">Aucune main détectée</div>
              : s.state.hands.map((h, i) => <div key={i}>Main {h.handedness} : <b className="text-accent">{h.gesture ?? "?"}</b> ({Math.round(h.confidence * 100)}%)</div>)}
          </div>
        </div>
      </div>
    </div>
  );
}
