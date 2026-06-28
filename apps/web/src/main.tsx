import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Providers } from "@/components/Providers";
import { routes } from "@/router";
import "@/globals.css";

const container = document.getElementById("root");

if (!container) {
  throw new Error("No se encontró el contenedor #root");
}

const router = createBrowserRouter(routes);

createRoot(container).render(
  <StrictMode>
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  </StrictMode>,
);
