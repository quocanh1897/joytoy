import { bindLanguageToggle } from "./language";

export function initProductGallery(): void {
  bindLanguageToggle();
  const mainImage = document.querySelector<HTMLImageElement>("[data-gallery-main]");
  const counter = document.querySelector<HTMLElement>("[data-gallery-counter]");
  const buttons = [...document.querySelectorAll<HTMLButtonElement>("[data-gallery-thumb]")];
  if (!mainImage || !buttons.length) return;

  let active = 0;
  const select = (index: number) => {
    active = (index + buttons.length) % buttons.length;
    const button = buttons[active];
    if (!button) return;
    mainImage.src = button.dataset.src ?? mainImage.src;
    mainImage.width = Number(button.dataset.width) || mainImage.width;
    mainImage.height = Number(button.dataset.height) || mainImage.height;
    buttons.forEach((item, itemIndex) => {
      item.classList.toggle("active", itemIndex === active);
      item.setAttribute("aria-current", itemIndex === active ? "true" : "false");
    });
    if (counter) counter.textContent = `${active + 1} / ${buttons.length}`;
  };

  buttons.forEach((button, index) => button.addEventListener("click", () => select(index)));
  document.querySelector<HTMLButtonElement>("[data-gallery-prev]")?.addEventListener("click", () => select(active - 1));
  document.querySelector<HTMLButtonElement>("[data-gallery-next]")?.addEventListener("click", () => select(active + 1));
  document.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") select(active - 1);
    if (event.key === "ArrowRight") select(active + 1);
  });
}
