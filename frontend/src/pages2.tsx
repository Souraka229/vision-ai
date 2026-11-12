import { useEffect, useState } from "react";
import { ShieldAlert, OctagonX } from "lucide-react";
import { api, Status } from "./lib";
import { EngineButtons, Toggle, Video } from "./pages1";

export function Studio({ s }: { s: Status }) {
  const [name, setName] = useState("");
  const [target, setTarget] = useState(30);
  const [msg, setMsg] = useState("");
  const run = (p: string, b?: unknown, m = "POST") => api(p, m, b).then(() => setMsg("")).catch((e) => setMsg(e.message));
  const rec = s.recording;
  const mm = s.model;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-xl font-semibold">Gesture Studio</h1><EngineButtons s={s} /></div>
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2"><Video s={s} /></div>
        <div className="space-y-3">
          <div className="card space-y-2">
            <div className="text-sm text-zinc-400">1. Enregistrer un geste</div>
            <input className="w-full bg-ink border border-edge rounded px-2 py-1 text-sm" placeholder="Nom du geste" value={name} onChange={(e) => setName(e.target.value)} />
            <label className="text-xs text-zinc-400 block">Répétitions : {target}
              <input type="range" min={10} max={100} value={target} onChange={(e) => setTarget(+e.target.value)} className="w-full accent-[#ff7a1a]" /></label>
            <button className="btn-accent w-full" disabled={!name || !s.running || !!rec} onClick={() => run("/api/gestures/record", { name, target })}>Enregistrer</button>
            {rec && <div className="text-sm text-accent">Enregistrement {rec.name} : {rec.count}/{rec.target}. Bougez légèrement la main.</div>}
            {msg && <div className="text-sm text-red-400">{msg}</div>}
          </div>
          <div className="card space-y-2">
            <div className="text-sm text-zinc-400">2. Gestes enregistrés</div>
            {Object.keys(s.custom).length === 0 && <div className="text-sm text-zinc-500">Aucun geste personnalisé.</div>}
            {Object.entries(s.custom).map(([k, v]) => (
              <div key={k} className="flex justify-between text-sm"><span>{k} <span className="text-zinc-500">({v})</span></span>
                <button className="text-xs text-zinc-400 hover:text-red-400" onClick={() => run(`/api/gestures/${k}`, undefined, "DELETE")}>supprimer</button></div>))}
            <button className="btn w-full" onClick={() => run("/api/gestures/train")}>Entraîner (Random Forest)</button>
            {mm?.accuracy_test !== undefined && <div className="text-sm">Précision sur test écarté : <b className="text-accent">{Math.round(mm.accuracy_test * 100)}%</b> ({mm.n_train} train / {mm.n_test} test)</div>}
          </div>
          <div className="card text-sm">3. Test en direct : <b className="text-accent">{s.state.gesture ?? "aucun"}</b> ({Math.round(s.state.confidence * 100)}%)</div>
        </div>
      </div>
    </div>
  );
}

export function Control({ s }: { s: Status }) {
  const [acts, setActs] = useState<{ builtin: string[]; custom: string[]; actions: string[] }>({ builtin: [], custom: [], actions: [] });
  const [msg, setMsg] = useState("");
  useEffect(() => { api("/api/gestures").then(setActs); }, [Object.keys(s.custom).join()]);
  const en = s.control.enabled;
  const map = { ...s.settings.gesture_actions, ...s.settings.custom_actions };
  const setAct = (g: string, a: string) => {
    const key = acts.builtin.includes(g) ? "gesture_actions" : "custom_actions";
    api("/api/settings", "POST", { [key]: { ...s.settings[key], [g]: a } }).catch((e) => setMsg(e.message));
  };
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Computer Control</h1>
      <div className={`card flex items-center justify-between ${en ? "border-accent" : ""}`}>
        <div className="flex items-center gap-2"><ShieldAlert size={18} className={en ? "text-accent" : "text-zinc-500"} />
          <span className="text-sm">Contrôle {en ? "ACTIVÉ" : "désactivé (par défaut)"}</span></div>
        <div className="flex gap-2">
          {!en && <button className="btn-accent" onClick={() => api("/api/control/enable", "POST").catch((e) => setMsg(e.message))}>Activer</button>}
          <button className="btn !border-red-500 text-red-400" onClick={() => api("/api/control/stop", "POST")}><OctagonX size={14} className="inline mr-1" />STOP</button>
        </div>
      </div>
      {s.control.pending && (
        <div className="card border-accent flex items-center justify-between"><span className="text-sm">Action sensible en attente : <b>{s.control.pending}</b></span>
          <button className="btn-accent" onClick={() => api("/api/control/confirm", "POST")}>Confirmer</button></div>)}
      {msg && <div className="text-sm text-red-400">{msg}</div>}
      <div className="card text-sm space-y-1">
        <div className="text-zinc-400">Pour que le curseur suive votre main, il faut les 4 points :</div>
        {([
          [s.running, "Caméra démarrée"],
          [en, "Contrôle activé (bouton Activer ci-dessus ; il se désactive si vous arrêtez la caméra)"],
          [s.settings.air_mouse, "Souris aérienne activée (interrupteur ci-dessous)"],
          [s.state.hands.length > 0, "Une main est détectée par la caméra"],
        ] as [boolean, string][]).map(([ok, t]) => (
          <div key={t} className={ok ? "text-green-400" : "text-red-400"}>{ok ? "✓" : "✗"} <span className="text-zinc-300">{t}</span></div>))}
      </div>
      <div className="card">
        <Toggle on={s.settings.air_mouse} onChange={(v) => api("/api/settings", "POST", { air_mouse: v })} label="Souris aérienne : la main déplace le curseur" />
        <div className="text-xs text-zinc-400 mb-2">Pincer pouce + index = clic · maintenir 0,4 s = glisser-déposer · pouce + majeur = clic droit · deux doigts levés (PEACE) puis monter/descendre la main = défilement. Le contrôle doit être activé ci-dessus.</div>
        <label className="flex justify-between items-center text-sm">Lissage : {Math.round(s.settings.air_smoothing * 100)}%
          <input type="range" min={0} max={1} step={0.1} value={s.settings.air_smoothing} onChange={(e) => api("/api/settings", "POST", { air_smoothing: +e.target.value })} className="accent-[#ff7a1a]" /></label>
        <label className="flex justify-between items-center text-sm">Bords ignorés : {Math.round(s.settings.air_margin * 100)}%
          <input type="range" min={0} max={0.3} step={0.05} value={s.settings.air_margin} onChange={(e) => api("/api/settings", "POST", { air_margin: +e.target.value })} className="accent-[#ff7a1a]" /></label>
        <div className="text-sm text-zinc-400 mt-2 mb-1">Gestes → actions (liste blanche, aucune commande système arbitraire)</div>
        {[...acts.builtin, ...acts.custom].map((g) => (
          <div key={g} className="flex items-center justify-between py-1 text-sm"><span>{g}</span>
            <select className="bg-ink border border-edge rounded px-2 py-1" value={map[g] ?? "none"} onChange={(e) => setAct(g, e.target.value)}>
              {acts.actions.map((a) => <option key={a}>{a}</option>)}</select></div>))}
      </div>
      <div className="text-xs text-zinc-500">Astuce : amener la souris dans un coin de l'écran déclenche aussi l'arrêt de sécurité PyAutoGUI.</div>
    </div>
  );
}

export function People({ s }: { s: Status }) {
  const on = s.settings.modules.objects;
  const dets = s.state.objects;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-xl font-semibold">People & Objects</h1><EngineButtons s={s} /></div>
      <div className="card"><Toggle on={on} onChange={(v) => api("/api/settings", "POST", { modules: { objects: v } })} label="Activer la détection YOLO (profil ADVANCED)" />
        <div className="text-xs text-zinc-500">Identifiants anonymes et temporaires. Aucune image ni visage n'est enregistré.</div></div>
      {s.error?.startsWith("YOLO") && <div className="card text-sm text-red-400">{s.error}</div>}
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2"><Video s={s} /></div>
        <div className="card text-sm space-y-1">
          {!on ? <div className="text-zinc-500">Module désactivé.</div> : dets.length === 0 ? <div className="text-zinc-500">Rien détecté.</div>
            : dets.map((d: any, i) => <div key={i}>{d.id ? `#${d.id} ` : ""}{d.label} <span className="text-zinc-500">{Math.round(d.score * 100)}%</span></div>)}
          {on && <div className="pt-2 border-t border-edge mt-2 text-zinc-400">Téléphones visibles en usage (estimation visuelle, sans présumer d'intention) :</div>}
          {on && ((s.state.interactions as any[]) ?? []).length === 0 && <div className="text-zinc-500">Aucun.</div>}
          {on && ((s.state.interactions as any[]) ?? []).map((x, i) => <div key={i} className="text-accent">{x.label}</div>)}
        </div>
      </div>
    </div>
  );
}
