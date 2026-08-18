const HOME_PATH = "/";

function isHomePath(): boolean {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  return path === HOME_PATH;
}

function isInteractiveTarget(target: EventTarget | null): boolean {
  return target instanceof Element && Boolean(target.closest("a, button, input, select, textarea, label, summary, [role='button']"));
}

function isTypingTarget(): boolean {
  const active = document.activeElement;
  return (
    active instanceof HTMLInputElement ||
    active instanceof HTMLTextAreaElement ||
    active instanceof HTMLSelectElement ||
    (active instanceof HTMLElement && active.isContentEditable)
  );
}

export function initHomeEscape(): void {
  if (isHomePath()) return;

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || event.defaultPrevented || isTypingTarget()) return;
    window.location.assign(HOME_PATH);
  });

  document.addEventListener(
    "click",
    (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const main = document.getElementById("main-content");
      if (!main || main.contains(target) || isInteractiveTarget(target)) return;
      window.location.assign(HOME_PATH);
    },
    true,
  );
}
