import type { ReactNode } from "react";
import { Build } from "./components/Build";
import { FieldLayer } from "./components/FieldLayer";
import { Footer } from "./components/Footer";
import { Hero } from "./components/Hero";
import { Hook } from "./components/Hook";
import { Limits } from "./components/Limits";
import { Live } from "./components/Live";
import { Method } from "./components/Method";
import { Nav } from "./components/Nav";
import { Results } from "./components/Results";
import { SmoothScroll } from "./components/SmoothScroll";
import { Stability } from "./components/Stability";
import { Voices } from "./components/Voices";
import { Words } from "./components/Words";

const SECTIONS: [string, ReactNode][] = [
  ["top", <Hero key="top" />],
  ["question", <Hook key="question" />],
  ["voices", <Voices key="voices" />],
  ["method", <Method key="method" />],
  ["results", <Results key="results" />],
  ["words", <Words key="words" />],
  ["stability", <Stability key="stability" />],
  // Renders nothing unless the live API (scripts.serve) is reachable.
  ["live", <Live key="live" />],
  ["limits", <Limits key="limits" />],
  ["build", <Build key="build" />],
];

// Review aid: `?capture&only=method` renders a single section so it can be screenshotted
// without scrolling. Normal visits render everything.
const ONLY = new URLSearchParams(window.location.search).get("only");

export default function App() {
  const sections = ONLY ? SECTIONS.filter(([id]) => id === ONLY) : SECTIONS;
  return (
    <>
      <SmoothScroll />
      <FieldLayer />
      <Nav />
      <main>{sections.map(([, node]) => node)}</main>
      {!ONLY || ONLY === "contact" ? <Footer /> : null}
    </>
  );
}
