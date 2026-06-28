import type React from "react";
import { Navigate, Outlet, type RouteObject } from "react-router-dom";

import { AuthGuard } from "@/components/AuthGuard";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import CarritosGuardadosPage from "@/pages/CarritosGuardados";
import CompraGuiadaPage from "@/pages/CompraGuiada";
import ConfigurarDistribucionPage from "@/pages/ConfigurarDistribucion";
import HomePage from "@/pages/Home";
import LoginPage from "@/pages/Login";
import PerfilPage from "@/pages/Perfil";
import ProductoDetallePage from "@/pages/ProductoDetalle";
import RecuperarPasswordPage from "@/pages/RecuperarPassword";
import RegistroPage from "@/pages/Registro";
import ResultadoDistribucionPage from "@/pages/ResultadoDistribucion";

function RootLayout(): React.ReactElement {
  return (
    <>
      <Header />
      <main className="min-h-[calc(100vh-8rem)]">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}

function NotFoundPage(): React.ReactElement {
  return <p>404 - Página no encontrada</p>;
}

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <RootLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "carrito", element: <Navigate to="/" replace /> },
      { path: "productos/:id", element: <ProductoDetallePage /> },
      {
        path: "carritos",
        element: <AuthGuard />,
        children: [{ index: true, element: <CarritosGuardadosPage /> }],
      },
      {
        path: "perfil",
        element: <AuthGuard />,
        children: [{ index: true, element: <PerfilPage /> }],
      },
      {
        path: "distribuir",
        element: <AuthGuard />,
        children: [{ index: true, element: <ConfigurarDistribucionPage /> }],
      },
      {
        path: "distribucion",
        element: <AuthGuard />,
        children: [{ index: true, element: <ResultadoDistribucionPage /> }],
      },
      {
        path: "compra-guiada/:id",
        element: <AuthGuard />,
        children: [{ index: true, element: <CompraGuiadaPage /> }],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/registro",
    element: <RegistroPage />,
  },
  {
    path: "/recuperar",
    element: <RecuperarPasswordPage />,
  },
  {
    path: "/old",
    element: <Navigate to="/" replace />,
  },
];
