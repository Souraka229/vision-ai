import { useEffect, useState } from "react";
import { api, Status } from "./lib";
import { EngineButtons, Stat } from "./pages1";

export function Analytics({ s }: { s: Status }) {
  const [a, setA] = useState<any>(null);
  useEffect(() => { const f = () => api("/api/analytics").then(setA); f(); const t = setInterval(f, 2000); return () => clearInterval(t); }, []);
  if (!a) return <div className="text-zinc-500">Chargement…</div>;
  const list = (o: Record<string, number>) => Object.keys(o).length === 0 ? <div className="text-zinc-500 text-sm">Aucun événement.</div>
    : Object.entries(o).sort((x, y) => y[1] - x[1]).map(([k, v]) => <div key={k} className="flex justify-between text-sm py-0.5"><span>{k}</span><b>{v}</b></div>);
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Analytics</h1>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat icon={null} label="Pic de personnes" value={a.max_people} />
        <Stat icon={null} label="Pic de téléphones" value={a.max_phones} />
        <Stat icon={null} label="Interactions estimées" value={a.interactions} />
        <Stat icon={null} label="Latence moyenne" value={a.avg_latency_ms} unit="ms" />
        <Stat icon={null} label="FPS moyen" value={a.avg_fps} />
        <Stat icon={null} label="RAM moyenne" value={a.avg_ram_mb} unit="Mo" />
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card"><div className="text-sm text-zinc-400 mb-2">Gestes reconnus</div>{list(a.gestures)}</div>
        <div className="card"><div className="text-sm text-zinc-400 mb-2">Commandes exécutées</div>{list(a.commands)}</div>
      </div>
      <button className="btn" onClick={() => api("/api/analytics", "DELETE").catch(() => alert("Droits administrateur requis"))}>Effacer les statistiques</button>
    </div>
  );
}

function PhonePanel({ s }: { s: Status }) {
  const [qr, setQr] = useState<{ qr_svg: string; url: string } | null>(null);
  const [err, setErr] = useState("");
  const usingPhone = s.settings.camera_source === "phone";
  const pair = () => api("/api/phone/pair", "POST").then(setQr).then(() => setErr("")).catch((e) => setErr(e.message));
  const unpair = () => api("/api/phone/unpair", "POST").then(() => setQr(null));
  useEffect(() => { if (s.phone.active && !qr) api("/api/phone").then(setQr); }, [s.phone.active]);
  return (
    <div className="card space-y-3 text-sm">
      <div className="text-zinc-400">Téléphone comme caméra (QR code, même Wi-Fi)</div>
      {!s.phone.active ? (
        <button className="btn-accent" onClick={pair}>Afficher le QR code</button>
      ) : (
        <div className="flex flex-col sm:flex-row gap-4 items-start">
          {qr?.qr_svg && <div className="bg-white p-2 rounded-lg w-52 shrink-0" dangerouslySetInnerHTML={{ __html: qr.qr_svg }} />}
          <div className="space-y-2">
            <ol className="list-decimal ml-4 text-zinc-300 space-y-1">
              <li>Scannez ce QR avec l'appareil photo du téléphone.</li>
              <li>Le navigateur affiche un avertissement de certificat (normal, certificat local) : « Avancé » puis « Continuer ».</li>
              <li>Appuyez sur « Démarrer la caméra » et autorisez l'accès.</li>
            </ol>
            <div className={s.phone.connected ? "text-green-400" : "text-zinc-500"}>{s.phone.connected ? "Téléphone connecté, images reçues" : "En attente du téléphone…"}</div>
            <div className="flex gap-2">
              <button className={usingPhone ? "btn" : "btn-accent"} disabled={s.running} onClick={() => api("/api/settings", "POST", { camera_source: usingPhone ? "webcam" : "phone" })}>
                {usingPhone ? "Revenir à la webcam du PC" : "Utiliser le téléphone comme caméra"}</button>
              <button className="btn" onClick={unpair}>Fermer l'appairage</button>
            </div>
            {s.running && <div className="text-xs text-zinc-500">Arrêtez la caméra pour changer de source.</div>}
          </div>
        </div>)}
      {s.phone.active && <div className="text-xs text-zinc-500">Pendant l'appairage, le PC accepte des connexions sur votre réseau local avec un jeton unique. Fermez-le quand vous avez fini.</div>}
      {err && <div className="text-red-400">{err}</div>}
    </div>
  );
}

export function CameraSettings({ s }: { s: Status }) {
  const [cams, setCams] = useState<number[]>([]);
  const st = s.settings;
  useEffect(() => { api("/api/cameras").then((r) => setCams(r.cameras)); }, [s.running]);
  const set = (p: object) => api("/api/settings", "POST", p);
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-xl font-semibold">Camera Settings</h1><EngineButtons s={s} /></div>
      <PhonePanel s={s} />
      <div className="card space-y-3 text-sm">
        <label className="flex justify-between items-center">Caméra
          <select disabled={s.running} className="bg-ink border border-edge rounded px-2 py-1" value={st.camera_index} onChange={(e) => set({ camera_index: +e.target.value })}>
            {(cams.length ? cams : [st.camera_index]).map((c) => <option key={c} value={c}>Caméra {c}</option>)}</select></label>
        <label className="flex justify-between items-center">Résolution
          <select disabled={s.running} className="bg-ink border border-edge rounded px-2 py-1" value={`${st.width}x${st.height}`}
            onChange={(e) => { const [w, h] = e.target.value.split("x").map(Number); set({ width: w, height: h }); }}>
            <option>640x480</option><option>320x240</option><option>1280x720</option></select></label>
        <label className="flex justify-between items-center">Mains suivies
          <select disabled={s.running} className="bg-ink border border-edge rounded px-2 py-1" value={st.max_hands} onChange={(e) => set({ max_hands: +e.target.value })}>
            <option value={1}>1</option><option value={2}>2</option></select></label>
        <label className="flex justify-between items-center">Mode simulation (sans caméra, clairement signalé)
          <input type="checkbox" disabled={s.running} checked={st.simulate} onChange={(e) => set({ simulate: e.target.checked })} /></label>
        <label className="block">Téléphone / caméra IP (URL du flux, vide = webcam du PC)
          <input disabled={s.running} className="w-full mt-1 bg-ink border border-edge rounded px-2 py-1" placeholder="http://192.168.1.20:8080/video"
            defaultValue={st.camera_url} onBlur={(e) => set({ camera_url: e.target.value.trim() })} /></label>
        <div className="text-xs text-zinc-500">Android : appli « IP Webcam », bouton « Démarrer le serveur », URL = http://IP:8080/video. Le PC et le téléphone doivent être sur le même Wi-Fi. Les changements s'appliquent au prochain démarrage de la caméra.</div>
      </div>
    </div>
  );
}

export function System({ s }: { s: Status }) {
  const st = s.settings;
  const [users, setUsers] = useState<{ users: any[]; setup_needed: boolean }>({ users: [], setup_needed: false });
  const [me, setMe] = useState<any>(null);
  const [f, setF] = useState({ name: "", pin: "", role: "standard" });
  const [msg, setMsg] = useState("");
  const load = () => { api("/api/users").then(setUsers); api("/api/me").then((r) => setMe(r.user)); };
  useEffect(load, []);
  const set = (p: object) => api("/api/settings", "POST", p).catch((e) => setMsg(e.message));
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">System Settings</h1>
      <div className="card text-sm space-y-2">
        <div className="text-zinc-400">Profil de performance</div>
        <div className="flex gap-2">{["LITE", "ADVANCED"].map((p) => (
          <button key={p} className={st.profile === p ? "btn-accent" : "btn"} onClick={() => set({ profile: p })}>{p}</button>))}</div>
        <div className="text-xs text-zinc-500">LITE : mains + gestes + contrôle. ADVANCED : ajoute YOLO (personnes/objets).</div>
        <label className="flex justify-between items-center pt-2">Seuil de confiance : {Math.round(st.min_confidence * 100)}%
          <input type="range" min={0.4} max={0.95} step={0.05} value={st.min_confidence} onChange={(e) => set({ min_confidence: +e.target.value })} className="accent-[#ff7a1a]" /></label>
        <label className="flex justify-between items-center">Cooldown : {st.cooldown}s
          <input type="range" min={0.5} max={5} step={0.5} value={st.cooldown} onChange={(e) => set({ cooldown: +e.target.value })} className="accent-[#ff7a1a]" /></label>
      </div>
      <div className="card text-sm space-y-2">
        <div className="text-zinc-400">Profils locaux (PIN) {me ? <span className="text-accent">· connecté : {me.name} ({me.role})</span> : null}</div>
        <div className="text-xs text-zinc-500">Un geste n'est jamais une preuve d'identité. {users.setup_needed && "Le premier profil créé devient administrateur."}</div>
        {users.users.map((u) => <div key={u.name}>{u.name} <span className="text-zinc-500">({u.role})</span></div>)}
        <div className="flex gap-2 flex-wrap">
          <input className="bg-ink border border-edge rounded px-2 py-1 w-32" placeholder="Nom" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
          <input className="bg-ink border border-edge rounded px-2 py-1 w-24" placeholder="PIN" type="password" value={f.pin} onChange={(e) => setF({ ...f, pin: e.target.value })} />
          <select className="bg-ink border border-edge rounded px-2" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="standard">standard</option><option value="guest">invité</option><option value="admin">admin</option></select>
          <button className="btn" onClick={() => api("/api/users", "POST", f).then(() => { setMsg(""); load(); }).catch((e) => setMsg(e.message))}>Créer</button>
          <button className="btn" onClick={() => api("/api/login", "POST", { name: f.name, pin: f.pin }).then((r) => { localStorage.setItem("token", r.token); setMsg(""); load(); }).catch((e) => setMsg(e.message))}>Connexion</button>
        </div>
        {msg && <div className="text-red-400">{msg}</div>}
      </div>
    </div>
  );
}
