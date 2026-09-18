import React from "react";
import { createRoot } from "react-dom/client";
import { AssessmentProvider } from "./context/AssessmentContext";
import App from "./App";
import "./styles.css";
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AssessmentProvider>
      <App />
    </AssessmentProvider>
  </React.StrictMode>,
);
