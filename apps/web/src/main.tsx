import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";

const container = document.querySelector("#root");
if (!container) throw new Error("root element is missing");

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

