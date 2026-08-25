import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./Layout";
import { Customer } from "./pages/Customer";
import { Drift } from "./pages/Drift";
import { Models } from "./pages/Models";
import { Overview } from "./pages/Overview";
import { Pipeline } from "./pages/Pipeline";
import { Risk } from "./pages/Risk";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Overview />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/customers/:id" element={<Customer />} />
          <Route path="/models" element={<Models />} />
          <Route path="/drift" element={<Drift />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
