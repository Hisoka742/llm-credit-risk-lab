// Author details. If any of these is left empty, the footer hides the repository button
// and the contact form instead of showing invented details.
const real = {
  name: "Atmania Slmane",
  github: "https://github.com/Hisoka742/llm-credit-risk-lab",
  email: "atmaniaslmane@gmail.com",
};

// Review aid, development server only: `?demo` fills obviously fake details so the footer's
// full state (repository button + contact form) can be inspected before the real ones exist.
// `import.meta.env.DEV` is false in a production build, so visitors can never reach it.
const demo = {
  name: "Demo Author",
  github: "https://github.com/example/llm-credit-risk-lab",
  email: "demo@example.com",
};

const useDemo =
  import.meta.env.DEV &&
  typeof window !== "undefined" &&
  new URLSearchParams(window.location.search).has("demo");

export const profile = useDemo ? demo : real;
