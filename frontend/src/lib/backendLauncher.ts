let backendStarted = false;

export const launchBackend = async (): Promise<void> => {
  if (backendStarted) return;
  const isTauri = Boolean((window as { __TAURI__?: unknown }).__TAURI__);
  if (!isTauri) return;

  try {
    const mod = await import("@tauri-apps/plugin-shell");
    const command = mod.Command.sidecar("quorum-backend");
    await command.spawn();
    backendStarted = true;
  } catch (error) {
    console.error("Failed to launch backend sidecar:", error);
  }
};
