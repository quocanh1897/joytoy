export type Language = "en" | "vi";

export function getLanguage(): Language {
  const saved = localStorage.getItem("jt-language");
  return saved === "vi" ? "vi" : "en";
}

export function applyLanguage(language: Language): void {
  document.documentElement.lang = language;
  document.documentElement.dataset.language = language;
  localStorage.setItem("jt-language", language);

  document.querySelectorAll<HTMLElement>("[data-en][data-vi]").forEach((element) => {
    element.textContent = element.dataset[language] ?? element.textContent;
  });
  document.querySelectorAll<HTMLElement>("[data-placeholder-en][data-placeholder-vi]").forEach((element) => {
    if (element instanceof HTMLInputElement) {
      element.placeholder = language === "vi" ? element.dataset.placeholderVi ?? "" : element.dataset.placeholderEn ?? "";
    }
  });
  document.querySelectorAll<HTMLButtonElement>("[data-language-toggle]").forEach((button) => {
    button.textContent = language === "en" ? "VI" : "EN";
    button.setAttribute("aria-label", language === "en" ? "Chuyển sang tiếng Việt" : "Switch to English");
  });
}

export function bindLanguageToggle(onChange?: (language: Language) => void): Language {
  let language = getLanguage();
  applyLanguage(language);
  document.querySelectorAll<HTMLButtonElement>("[data-language-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      language = language === "en" ? "vi" : "en";
      applyLanguage(language);
      onChange?.(language);
    });
  });
  return language;
}
