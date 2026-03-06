import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Database, Download, KeyRound, Shield } from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import {
  downloadExportedSystemLog,
  exportSystemLog,
  getEncryptionConfig,
  getStorageStatus,
  updateEncryptionConfig,
  updateStorageQuota,
  type EncryptionConfig,
  type StorageStatus,
} from "@/lib/api-functions";
import { toast } from "sonner";

const fallbackStorage: StorageStatus = {
  quota_bytes: 0,
  used_bytes: 0,
  usage_by_category: {},
  utilization_percent: 0,
  alert_level: "normal",
  cleanup_suggestions: [],
};

const fallbackEncryption: EncryptionConfig = {
  signature_algorithm: "RSA-PSS-4096",
  hash_algorithm: "SHA-256",
  key_rotation_days: 90,
};

const toGb = (bytes: number) => bytes / (1024 * 1024 * 1024);

export default function Settings() {
  const [storage, setStorage] = useState<StorageStatus>(fallbackStorage);
  const [encryption, setEncryption] = useState<EncryptionConfig>(fallbackEncryption);
  const [quotaGbInput, setQuotaGbInput] = useState("4");
  const [passphrase, setPassphrase] = useState("");
  const [encryptExport, setEncryptExport] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const [s, e] = await Promise.all([getStorageStatus(), getEncryptionConfig()]);
    setStorage(s);
    setEncryption(e);
    setQuotaGbInput(String(toGb(s.quota_bytes).toFixed(2)));
  };

  useEffect(() => {
    void load();
  }, []);

  const alertColor = useMemo(() => {
    if (storage.alert_level === "critical") return "hsl(var(--critical))";
    if (storage.alert_level === "warning") return "hsl(var(--high))";
    return "hsl(var(--low))";
  }, [storage.alert_level]);

  const saveQuota = async () => {
    const next = Number(quotaGbInput);
    if (!Number.isFinite(next) || next <= 0) {
      toast.error("Invalid quota value");
      return;
    }
    setBusy(true);
    try {
      const data = await updateStorageQuota(next);
      setStorage(data);
      toast.success("Storage quota updated");
    } catch (error) {
      console.error(error);
      toast.error("Failed to update quota");
    } finally {
      setBusy(false);
    }
  };

  const saveEncryption = async () => {
    setBusy(true);
    try {
      const data = await updateEncryptionConfig(encryption);
      setEncryption(data);
      toast.success("Encryption settings updated");
    } catch (error) {
      console.error(error);
      toast.error("Failed to update encryption settings");
    } finally {
      setBusy(false);
    }
  };

  const exportLogs = async () => {
    if (!passphrase.trim()) {
      toast.error("Passphrase required");
      return;
    }
    setBusy(true);
    try {
      const result = await exportSystemLog(passphrase.trim(), encryptExport);
      const blob = await downloadExportedSystemLog(result.filename);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(`Export downloaded (${result.sha256.slice(0, 12)}...)`);
    } catch (error) {
      console.error(error);
      toast.error("Log export failed (check passphrase)");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppLayout title="Settings" subtitle="Storage, encryption, and secure system log export">
      <div className="space-y-6 max-w-5xl">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-4 h-4 text-cyan" />
            <h3 className="text-sm font-semibold">Storage Allocation</h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="space-y-3">
              <label className="text-xs text-muted-foreground uppercase tracking-wide">Max Quota (GB)</label>
              <div className="flex gap-2">
                <input
                  value={quotaGbInput}
                  onChange={(e) => setQuotaGbInput(e.target.value)}
                  className="flex-1 bg-muted border border-border rounded-md px-3 py-2 text-sm text-foreground font-mono outline-none focus:border-cyan/40"
                />
                <button onClick={() => void saveQuota()} disabled={busy} className="px-3 py-2 rounded-md text-xs font-semibold border border-border">
                  Save
                </button>
              </div>
              <p className="text-xs font-mono text-muted-foreground">
                Utilization: <span style={{ color: alertColor }}>{storage.utilization_percent}% ({storage.alert_level})</span>
              </p>
              <div className="h-2 rounded bg-muted overflow-hidden">
                <div className="h-full" style={{ width: `${Math.min(storage.utilization_percent, 100)}%`, background: alertColor }} />
              </div>
            </div>
            <div className="space-y-1 text-xs font-mono">
              {Object.entries(storage.usage_by_category).map(([k, v]) => (
                <p key={k} className="text-muted-foreground">
                  {k}: <span className="text-foreground">{toGb(v).toFixed(3)} GB</span>
                </p>
              ))}
              {storage.cleanup_suggestions.map((s, idx) => (
                <p key={`${s}-${idx}`} className="text-cyber-high">- {s}</p>
              ))}
            </div>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4 text-cyan" />
            <h3 className="text-sm font-semibold">Encryption Configuration</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">Signature</label>
              <select
                value={encryption.signature_algorithm}
                onChange={(e) => setEncryption((prev) => ({ ...prev, signature_algorithm: e.target.value }))}
                className="w-full bg-muted border border-border rounded-md px-3 py-2 text-sm text-foreground"
              >
                <option value="RSA-PSS-4096">RSA-PSS 4096-bit</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">Hashing Mode</label>
              <select
                value={encryption.hash_algorithm}
                onChange={(e) => setEncryption((prev) => ({ ...prev, hash_algorithm: e.target.value }))}
                className="w-full bg-muted border border-border rounded-md px-3 py-2 text-sm text-foreground"
              >
                <option value="SHA-256">SHA-256</option>
                <option value="SHA-512">SHA-512</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground uppercase tracking-wide block mb-2">Key Rotation (days)</label>
              <input
                type="number"
                value={encryption.key_rotation_days}
                onChange={(e) =>
                  setEncryption((prev) => ({
                    ...prev,
                    key_rotation_days: Number(e.target.value || 90),
                  }))
                }
                className="w-full bg-muted border border-border rounded-md px-3 py-2 text-sm text-foreground font-mono"
              />
            </div>
          </div>
          <button onClick={() => void saveEncryption()} disabled={busy} className="mt-4 px-3 py-2 rounded-md text-xs font-semibold border border-border">
            Save Encryption Settings
          </button>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="cyber-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <KeyRound className="w-4 h-4 text-cyan" />
            <h3 className="text-sm font-semibold">System Log Download</h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
            <input
              type="password"
              placeholder="Authentication passphrase"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              className="lg:col-span-2 bg-muted border border-border rounded-md px-3 py-2 text-sm text-foreground font-mono"
            />
            <label className="text-xs text-muted-foreground flex items-center gap-2">
              <input
                type="checkbox"
                checked={encryptExport}
                onChange={(e) => setEncryptExport(e.target.checked)}
              />
              Encrypted export (.enc)
            </label>
            <button
              onClick={() => void exportLogs()}
              disabled={busy}
              className="px-3 py-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 border border-cyan/40 text-cyan"
            >
              <Download className="w-3.5 h-3.5" />
              Export quorum.log
            </button>
          </div>
        </motion.div>
      </div>
    </AppLayout>
  );
}
