import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, X } from "lucide-react";
import { mitreTactics, mitreTechniques } from "@/lib/mitreData";
import type { MitreTechnique } from "@/lib/mitreData";

const severityColor = (severity: string, detections: number) => {
  if (detections === 0) return { bg: "hsl(var(--muted))", border: "hsl(var(--border))", text: "hsl(var(--muted-foreground))" };
  switch (severity) {
    case "CRITICAL": return { bg: "hsl(var(--critical) / 0.25)", border: "hsl(var(--critical) / 0.6)", text: "hsl(var(--critical))" };
    case "HIGH": return { bg: "hsl(var(--high) / 0.2)", border: "hsl(var(--high) / 0.5)", text: "hsl(var(--high))" };
    case "MEDIUM": return { bg: "hsl(var(--medium) / 0.15)", border: "hsl(var(--medium) / 0.4)", text: "hsl(var(--medium))" };
    case "LOW": return { bg: "hsl(var(--low) / 0.12)", border: "hsl(var(--low) / 0.35)", text: "hsl(var(--low))" };
    default: return { bg: "hsl(var(--muted))", border: "hsl(var(--border))", text: "hsl(var(--muted-foreground))" };
  }
};

export default function MitreHeatmap() {
  const [selected, setSelected] = useState<MitreTechnique | null>(null);

  const grouped = mitreTactics.map(tactic => ({
    tactic,
    techniques: mitreTechniques.filter(t => t.tactic === tactic),
  }));

  const totalDetections = mitreTechniques.reduce((sum, t) => sum + t.detections, 0);
  const coveredTactics = mitreTactics.filter(t => mitreTechniques.some(tech => tech.tactic === t && tech.detections > 0)).length;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="cyber-card overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Shield className="w-4 h-4 text-cyan" /> MITRE ATT&CK Heatmap
          </h3>
          <p className="text-xs text-muted-foreground">{coveredTactics}/{mitreTactics.length} tactics covered · {totalDetections} total detections</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          {["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"].map(s => {
            const c = severityColor(s, s === "NONE" ? 0 : 1);
            return (
              <div key={s} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm" style={{ background: c.bg, border: `1px solid ${c.border}` }} />
                <span className="text-muted-foreground capitalize">{s.toLowerCase()}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="p-4 overflow-x-auto">
        <div className="grid grid-cols-12 gap-1 min-w-[900px]">
          {grouped.map(({ tactic, techniques }) => (
            <div key={tactic} className="space-y-1">
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider text-center px-1 pb-1 border-b border-border/50 truncate" title={tactic}>
                {tactic.replace("and ", "& ")}
              </div>
              {techniques.map(tech => {
                const colors = severityColor(tech.severity, tech.detections);
                return (
                  <motion.button
                    key={tech.id}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setSelected(tech)}
                    className="w-full rounded-sm p-1.5 text-left transition-all cursor-pointer"
                    style={{ background: colors.bg, border: `1px solid ${colors.border}` }}
                    title={`${tech.id}: ${tech.name}`}
                  >
                    <div className="text-[9px] font-mono font-semibold truncate" style={{ color: colors.text }}>{tech.id}</div>
                    <div className="text-[8px] truncate text-muted-foreground">{tech.name}</div>
                    {tech.detections > 0 && (
                      <div className="text-[9px] font-mono font-bold mt-0.5" style={{ color: colors.text }}>{tech.detections}</div>
                    )}
                  </motion.button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Detail popup */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="mx-4 mb-4 p-4 rounded-md border border-border"
            style={{ background: "hsl(var(--muted))" }}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-cyan font-semibold">{selected.id}</span>
                  <span className={`badge-${selected.severity.toLowerCase()}`}>{selected.severity}</span>
                </div>
                <h4 className="text-sm font-semibold text-foreground mt-1">{selected.name}</h4>
              </div>
              <button onClick={() => setSelected(null)} className="p-1 rounded hover:bg-background/50 transition-colors">
                <X className="w-4 h-4 text-muted-foreground" />
              </button>
            </div>
            <div className="grid grid-cols-3 gap-4 text-xs">
              <div><span className="text-muted-foreground">Tactic</span><p className="font-medium text-foreground mt-0.5">{selected.tactic}</p></div>
              <div><span className="text-muted-foreground">Detections</span><p className="font-mono font-bold text-cyan mt-0.5">{selected.detections}</p></div>
              <div><span className="text-muted-foreground">Coverage</span><p className="font-medium mt-0.5" style={{ color: severityColor(selected.severity, selected.detections).text }}>{selected.detections > 0 ? "Active" : "No Coverage"}</p></div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
