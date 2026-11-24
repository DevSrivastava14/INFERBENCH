import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { landingPurpose } from "../copy.js";
import "../styles/landing.css";

const HOLD_MS = 3600;

export function Landing() {
  const navigate = useNavigate();

  useEffect(() => {
    const id = window.setTimeout(() => {
      navigate("/overview", { replace: true });
    }, HOLD_MS);
    return () => window.clearTimeout(id);
  }, [navigate]);

  return (
    <main className="landing">
      <h1 className="landing-purpose">{landingPurpose}</h1>
      <p className="landing-name">
        <Link to="/overview" replace>
          InferBench
        </Link>
      </p>
    </main>
  );
}
