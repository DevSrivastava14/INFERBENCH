import { NavLink, Outlet, useMatches } from "react-router-dom";

const links = [
  { to: "/overview", label: "Overview", end: true },
  { to: "/benchmark", label: "Benchmark" },
  { to: "/results", label: "Results" },
  { to: "/history", label: "History" },
  { to: "/comparisons", label: "Comparisons" },
  { to: "/routing", label: "Routing" },
];

function RailMark({ label }) {
  const common = {
    width: 16,
    height: 16,
    viewBox: "0 0 16 16",
    "aria-hidden": true,
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.4,
  };
  if (label === "Overview") {
    return (
      <svg {...common}>
        <rect x="1.5" y="1.5" width="5" height="5" />
        <rect x="9.5" y="1.5" width="5" height="5" />
        <rect x="1.5" y="9.5" width="5" height="5" />
        <rect x="9.5" y="9.5" width="5" height="5" />
      </svg>
    );
  }
  if (label === "Benchmark") {
    return (
      <svg {...common}>
        <path d="M2 4h12M2 8h12M2 12h8" />
      </svg>
    );
  }
  if (label === "Results") {
    return (
      <svg {...common}>
        <path d="M3 13V8M8 13V3M13 13V6" />
      </svg>
    );
  }
  if (label === "History") {
    return (
      <svg {...common}>
        <path d="M2 3h12M2 8h12M2 13h12" />
      </svg>
    );
  }
  if (label === "Comparisons") {
    return (
      <svg {...common}>
        <rect x="1.5" y="2.5" width="5" height="11" />
        <rect x="9.5" y="2.5" width="5" height="11" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M2 8h5M7 8l4-4M7 8l4 4" />
    </svg>
  );
}

export function Shell() {
  const matches = useMatches();
  const handle = [...matches].reverse().find((match) => match.handle?.title)?.handle;
  const title = handle?.title;
  const lede = handle?.lede;

  return (
    <div className="shell">
      <aside className="rail">
        <p className="product-name">InferBench</p>
        <nav aria-label="Pages">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}>
              <RailMark label={link.label} />
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <header className="page-head">
          <h1 className="page-title">{title}</h1>
          <p className="lede">{lede}</p>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
