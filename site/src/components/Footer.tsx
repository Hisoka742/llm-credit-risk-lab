import { ArrowUpRight, GithubLogo, WarningCircle } from "@phosphor-icons/react";
import { type FormEvent, useState } from "react";
import { profile } from "../content/profile";
import { Magnetic } from "./Magnetic";
import { Reveal } from "./Reveal";

const REPRODUCE = `python -m scripts.prepare_data
python -m scripts.run_experiment --config configs/e0.yaml
python -m scripts.embed --config configs/e1.yaml
python -m scripts.run_experiment --config configs/e1.yaml
python -m scripts.make_report`;

const INPUT =
  "mt-2 w-full rounded-xl border border-paper/25 bg-paper/[0.04] px-4 py-3 text-paper placeholder:text-muted/80 transition-colors duration-200 hover:border-paper/45 focus:border-paper";

/**
 * Contact form. There is no server: submitting opens the visitor's mail client with the
 * message filled in. Rendered only when an address is configured in content/profile.ts.
 */
function ContactForm({ email }: { email: string }) {
  const [error, setError] = useState<string | null>(null);

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const from = String(data.get("from") ?? "").trim();
    const message = String(data.get("message") ?? "").trim();
    if (!message) {
      setError("Write a message before sending.");
      return;
    }
    setError(null);
    const subject = encodeURIComponent("LLM Credit Risk Lab");
    const body = encodeURIComponent(`${message}\n\n${from}`);
    window.location.href = `mailto:${email}?subject=${subject}&body=${body}`;
  };

  return (
    <form onSubmit={onSubmit} noValidate className="max-w-xl">
      <div>
        <label htmlFor="from" className="text-sm font-medium">
          Your name
        </label>
        <input id="from" name="from" type="text" autoComplete="name" className={INPUT} />
      </div>
      <div className="mt-5">
        <label htmlFor="message" className="text-sm font-medium">
          Message
        </label>
        <textarea
          id="message"
          name="message"
          rows={4}
          className={`${INPUT} resize-y`}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? "message-error" : "message-help"}
        />
        {error ? (
          <p id="message-error" className="mt-2 flex items-center gap-2 text-sm font-medium text-paper" role="alert">
            <WarningCircle size={18} weight="fill" aria-hidden="true" />
            {error}
          </p>
        ) : (
          <p id="message-help" className="mt-2 text-sm text-muted">
            Opens your mail app with the message filled in.
          </p>
        )}
      </div>
      <button type="submit" className="btn btn-ghost mt-6">
        Send message
        <ArrowUpRight size={18} aria-hidden="true" />
      </button>
    </form>
  );
}

export function Footer() {
  return (
    <footer id="contact" className="relative z-10 flex min-h-[100dvh] flex-col justify-between bg-ink/60 pt-28">
      <div className="mx-auto w-full max-w-[1400px] px-5 md:px-10">
        <Reveal>
          <h2 className="max-w-[17ch] font-display text-[clamp(3rem,9vw,6rem)] font-medium leading-[0.98] tracking-[-0.035em]">
            A small effect, measured properly.
          </h2>
        </Reveal>

        <div className="mt-14 grid gap-14 lg:grid-cols-2 lg:gap-20">
          <Reveal className="min-w-0">
            <p className="max-w-[46ch] text-lg leading-relaxed text-muted">
              Every number on this page is generated from the repository's own run outputs. The
              code, the configuration and the tests are there to be checked.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              {profile.github ? (
                <Magnetic>
                  <a href={profile.github} className="btn btn-primary" target="_blank" rel="noreferrer">
                    <GithubLogo size={20} weight="fill" aria-hidden="true" />
                    Open the repository
                  </a>
                </Magnetic>
              ) : null}
              <a href="#top" className="btn btn-ghost">
                Back to the top
              </a>
            </div>
          </Reveal>

          {/* min-w-0: a grid item otherwise grows to fit the code block and overflows phones. */}
          <Reveal delay={0.08} className="min-w-0">
            <h3 className="font-display text-xl font-medium">Reproduce it</h3>
            {/* Real commands from the repository, so they are set as code. */}
            <pre className="glass mt-4 overflow-x-auto p-5 font-mono text-[13px] leading-[1.9] text-paper/90">
              <code>{REPRODUCE}</code>
            </pre>
            {profile.email ? (
              <div className="mt-10">
                <ContactForm email={profile.email} />
              </div>
            ) : null}
          </Reveal>
        </div>
      </div>

      <div className="mx-auto mt-24 flex w-full max-w-[1400px] flex-wrap items-center justify-between gap-4 border-t border-line px-5 py-7 text-sm text-muted md:px-10">
        <p>
          LLM Credit Risk Lab{profile.name ? `, by ${profile.name}` : ""}. Data: Lending Club accepted
          loans, 2007 to 2018.
        </p>
        <p>Built with Vite, React and Three.js.</p>
      </div>
    </footer>
  );
}
