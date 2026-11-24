import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Shell } from "./layout/Shell.jsx";
import { Benchmark } from "./pages/Benchmark.jsx";
import { Comparisons } from "./pages/Comparisons.jsx";
import { History } from "./pages/History.jsx";
import { Landing } from "./pages/Landing.jsx";
import { Overview } from "./pages/Overview.jsx";
import { Results } from "./pages/Results.jsx";
import { Routing } from "./pages/Routing.jsx";

const router = createBrowserRouter([
  { path: "/", element: <Landing /> },
  {
    element: <Shell />,
    children: [
      { path: "overview", handle: { title: "Overview" }, element: <Overview /> },
      {
        path: "benchmark",
        handle: { title: "Benchmark configuration" },
        element: <Benchmark />,
      },
      { path: "results", handle: { title: "Results" }, element: <Results /> },
      {
        path: "history",
        handle: { title: "Experiment history" },
        element: <History />,
      },
      {
        path: "comparisons",
        handle: { title: "Comparisons" },
        element: <Comparisons />,
      },
      { path: "routing", handle: { title: "Routing" }, element: <Routing /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
