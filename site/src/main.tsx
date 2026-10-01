import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
// Cyrillic for the Russian version: Clash Display and Satoshi have no Cyrillic glyphs, so
// these sit behind them in the font stacks and are fetched only when Cyrillic text is shown.
import "@fontsource-variable/geologica";
import "@fontsource-variable/onest";
import "./index.css";
import { LangProvider } from "./lib/i18n";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LangProvider>
      <App />
    </LangProvider>
  </StrictMode>,
);
