import { useState } from "react";
import { Guide } from "./pages4";
import { BarChart3, BookOpen, Camera, Gauge, Hand, MousePointer2, ScanEye, Settings, Users } from "lucide-react";
import { useStatus } from "./lib";
import { Live, Overview } from "./pages1";
import { Control, People, Studio } from "./pages2";
import { Analytics, CameraSettings, System } from "./pages3";

const NAV = [
  ["Guide", BookOpen, Guide], ["Overview", Gauge, Overview], ["Live Vision", ScanEye, Live], ["Gesture Studio", Hand, Studio],
  ["Computer Control", MousePointer2, Control], ["People & Objects", Users, People],
  ["Analytics", BarChart3, Analytics], ["Camera Settings", Camera, CameraSettings], ["System Settings", Settings, System],
] as const;

export default function App() {
  const s = useStatus();
  const [i, setI] = useState(0);
  const Page = NAV[i][2];
  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <nav className="md:w-56 bg-panel border-b md:border-b-0 md:border-r border-edge p-3 flex md:flex-col gap-1 overflow-x-auto">
        <div className="hidden md:block px-2 py-3 font-semibold tracking-wide">VISION <span className="text-accent">AI</span></div>
        {NAV.map(([name, Icon], k) => (
          <button key={name} onClick={() => setI(k)} className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm whitespace-nowrap transition-colors ${k === i ? "bg-[#1f1f25] text-accent" : "text-zinc-400 hover:text-white"}`}>
            <Icon size={16} />{name}</button>))}
      </nav>
      <main className="flex-1 p-4 md:p-6 max-w-6xl">
        {s ? <Page s={s} /> : <div className="text-zinc-400">Backend injoignable sur 127.0.0.1:8000. Lancez start.bat.</div>}
      </main>
    </div>
  );
}
