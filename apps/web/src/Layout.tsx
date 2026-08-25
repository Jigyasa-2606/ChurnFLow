import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Overview" },
  { to: "/risk", label: "Risk" },
  { to: "/models", label: "Models" },
  { to: "/drift", label: "Drift" },
  { to: "/pipeline", label: "Pipeline" },
];

export function Layout() {
  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <span className="brand-kicker">Internal ML Ops</span>
          <strong>Churn Flow</strong>
        </div>
        <nav>
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === "/"}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <p className="rail-note">
          Simulated shoppers are the data source. This is not a storefront.
          <br />
          <a href="http://localhost:3000" target="_blank" rel="noreferrer">
            Grafana
          </a>
        </p>
      </aside>
      <main className="stage">
        <Outlet />
      </main>
    </div>
  );
}
