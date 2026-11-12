import { Status } from "./lib";

const GESTES: [string, string, string][] = [
  ["OPEN_PALM", "Main ouverte, 5 doigts écartés", "✋"],
  ["FIST", "Poing fermé", "✊"],
  ["POINTING", "Index levé, les autres doigts fermés", "☝️"],
  ["PEACE", "Index et majeur levés (V)", "✌️"],
  ["THUMBS_UP", "Pouce levé, poing fermé", "👍"],
  ["OK_SIGN", "Pouce et index en cercle, 3 autres doigts levés", "👌"],
];

const AIR: [string, string][] = [
  ["Déplacer le curseur", "Bougez simplement la main devant la caméra."],
  ["Clic gauche", "Pincez le pouce contre l'index, puis relâchez."],
  ["Glisser-déposer", "Pincez pouce + index et gardez 0,4 s, déplacez, puis relâchez."],
  ["Clic droit", "Pincez le pouce contre le majeur."],
  ["Défiler une page", "Levez index + majeur (V), puis montez ou descendez la main."],
];

export function Guide({ s }: { s: Status }) {
  const map = { ...s.settings.gesture_actions, ...s.settings.custom_actions } as Record<string, string>;
  const live = s.state.hands[0]?.gesture ?? null;
  return (
    <div className="space-y-5 max-w-3xl">
      <h1 className="text-xl font-semibold">Guide</h1>
      <div className="card space-y-2 text-sm">
        <div className="font-medium">À quoi ça sert ?</div>
        <p className="text-zinc-300">Piloter l'ordinateur <b>sans toucher ni clavier ni souris</b>, avec la main devant la caméra du PC ou d'un téléphone. Utile si vous avez mal aux mains ou au poignet, un handicap moteur, ou les mains occupées (cuisine, atelier, soins). Tout reste sur votre ordinateur, aucune image n'est enregistrée.</p>
      </div>

      <div className="card space-y-2 text-sm">
        <div className="font-medium">Démarrer en 3 étapes</div>
        <ol className="list-decimal ml-5 space-y-1 text-zinc-300">
          <li>Cliquez <b>Démarrer la caméra</b> (Overview) et placez votre main à 40-60 cm de la caméra.</li>
          <li>Dans <b>Computer Control</b>, cliquez <b>Activer</b>, puis activez <b>Souris aérienne</b>. Le bouton <b>STOP</b> coupe tout à tout moment.</li>
          <li>Bougez la main : le curseur suit. Pincez pour cliquer.</li>
        </ol>
        <div className="text-xs text-zinc-500">Le contrôle est désactivé par défaut : rien ne bouge sur votre PC tant que vous ne l'avez pas activé.</div>
      </div>

      <div className="card space-y-2 text-sm">
        <div className="font-medium">Souris aérienne</div>
        {AIR.map(([a, b]) => <div key={a} className="flex gap-3"><span className="w-40 shrink-0 text-accent">{a}</span><span className="text-zinc-300">{b}</span></div>)}
      </div>

      <div className="card space-y-2 text-sm">
        <div className="flex justify-between"><span className="font-medium">Gestes et actions</span>
          <span className="text-zinc-400">Détecté maintenant : <b className="text-accent">{live ?? "aucun"}</b></span></div>
        <div className="text-xs text-zinc-500">Chaque geste peut déclencher une action (volume, copier, onglet suivant…), à régler dans Computer Control. Montrez un geste pour voir la ligne s'allumer.</div>
        {GESTES.map(([k, how, ico]) => (
          <div key={k} className={`flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors ${live === k ? "bg-[#2a1a0a] border border-accent" : "border border-transparent"}`}>
            <span className="text-2xl w-8">{ico}</span>
            <div className="flex-1"><div className="font-medium">{k}</div><div className="text-zinc-400 text-xs">{how}</div></div>
            <span className="text-xs text-zinc-300">→ {map[k] ?? "none"}</span>
          </div>))}
        {Object.keys(s.custom).map((k) => (
          <div key={k} className={`flex items-center gap-3 rounded-lg px-2 py-1.5 ${live === k ? "bg-[#2a1a0a] border border-accent" : ""}`}>
            <span className="text-2xl w-8">⭐</span><div className="flex-1"><div className="font-medium">{k}</div><div className="text-zinc-400 text-xs">Votre geste personnalisé</div></div>
            <span className="text-xs text-zinc-300">→ {map[k] ?? "none"}</span></div>))}
      </div>

      <div className="card space-y-1 text-sm">
        <div className="font-medium">Créer votre propre geste</div>
        <p className="text-zinc-300">Dans <b>Gesture Studio</b> : donnez un nom, enregistrez 30 répétitions en bougeant légèrement la main, cliquez <b>Entraîner</b>, puis testez en direct. Idéal si les gestes standards sont difficiles pour vous.</p>
      </div>

      <div className="card space-y-1 text-sm">
        <div className="font-medium">Autres fonctions</div>
        <ul className="list-disc ml-5 text-zinc-300 space-y-0.5">
          <li><b>Téléphone comme caméra</b> : Camera Settings, scannez le QR code.</li>
          <li><b>People & Objects</b> : détecte personnes, téléphones, laptops (profil ADVANCED, plus lourd pour le PC).</li>
          <li><b>Analytics</b> : compte les gestes et commandes réellement observés.</li>
        </ul>
      </div>
    </div>
  );
}
