import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import { QtGateway } from "./gateway/QtGateway";
import { PreviewGateway } from "./gateway/PreviewGateway";
import "./styles.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Elemento root não encontrado");
}

createRoot(root).render(
  <StrictMode>
    <App gateway={import.meta.env.DEV && new URLSearchParams(location.search).has("preview") ? new PreviewGateway() : new QtGateway()} />
  </StrictMode>,
);
