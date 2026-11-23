import { NavLink, Outlet, useMatches } from "react-router-dom";

const links = [
  { to: "/", label: "Overview", end: true },
  { to: "/benchmark", label: "Benchmark" },
  { to: "/results", label: "Results" },
  { to: "/history", label: "History" },
];

export function Shell() {
  const matches = useMatches();
  const title = [...matches].reverse().find((match) => match.handle?.title)?.handle
    .title;

  return (
    <div className="shell">
      <aside className="rail">
        <p className="rail-name">InferBench</p>
        <nav aria-label="Pages">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}>
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <h1 className="page-title">{title}</h1>
        <Outlet />
      </main>
    </div>
  );
}
