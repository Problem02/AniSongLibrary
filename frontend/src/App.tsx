import "./App.css";
import React, { Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";

import Header from "@/components/HeaderComponent";
import { PlayerProvider } from "@/components/PlayerBarComponent";
import { LoginPage, RegisterPage } from "@/pages/AuthPage";
import { AuthProvider, isUserLoggedIn } from "@/services/auth";

const HomePage = React.lazy(() => import("@/pages/HomePage"));
const ExplorePage = React.lazy(() => import("@/pages/ExplorePage"));
const AnimeDetailsPage = React.lazy(() => import("@/pages/AnimeDetailsPage"));
const ArtistDetailsPage = React.lazy(() => import("@/pages/ArtistDetailsPage"));
const LibraryPage = React.lazy(() => import("@/pages/LibraryPage"));
const AccountPage = React.lazy(() => import("@/pages/AccountPage"));
const NotFoundPage = React.lazy(() => import("@/pages/NotFoundPage"));

function AuthenticatedRoute({ children }: { children: React.ReactElement }) {
  const authed = isUserLoggedIn();
  return authed ? children : <Navigate to="/login" replace />;
}

/** Sets body[data-auth-page] = true on /login and /register */
function useAuthBodyFlag() {
  const { pathname } = useLocation();
  const isAuth = pathname === "/login" || pathname === "/register";
  useEffect(() => {
    document.body.setAttribute("data-auth-page", isAuth ? "true" : "false");
    return () => document.body.removeAttribute("data-auth-page");
  }, [isAuth]);
  return isAuth;
}

/** Full-viewport center for auth pages; header/footer are overlays via CSS */
function AuthCenter({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen grid place-items-center p-6 bg-gradient-to-b from-[#14001a] to-[#1f0b2b]">
      <div className="w-full max-w-md">{children}</div>
    </main>
  );
}

function AppShell() {
  const isAuth = useAuthBodyFlag();

  if (isAuth) {
    // AUTH LAYOUT: header + centered viewport (no page scroll).
    // Header/footer are fixed overlays via CSS; do NOT reserve space with flex.
    return (
      <div className="min-h-screen">
        <Header />
        <Suspense fallback={<div className="p-6">Loading…</div>}>
          <Routes>
            <Route path="/login" element={<AuthCenter><LoginPage /></AuthCenter>} />
            <Route path="/register" element={<AuthCenter><RegisterPage /></AuthCenter>} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Suspense>
      </div>
    );
  }

  // NON-AUTH LAYOUT (scrolling pages with true sticky footer via flex):
  // Make the outer wrapper a flex column that fills the viewport.
  // Place PlayerProvider as the LAST child; it renders the <footer> (player)
  // at that position, so it naturally sits at the bottom of the page.
  return (
    <div className="layout flex flex-col min-h-screen">
      <Header />
      <main className="flex-1">
        <Suspense fallback={<div className="p-6">Loading…</div>}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/anime/:id" element={<AnimeDetailsPage />} />
            <Route path="/artist/:id" element={<ArtistDetailsPage />} />
            <Route
              path="/library"
              element={
                <AuthenticatedRoute>
                  <LibraryPage />
                </AuthenticatedRoute>
              }
            />
            <Route
              path="/account"
              element={
                <AuthenticatedRoute>
                  <AccountPage />
                </AuthenticatedRoute>
              }
            />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </main>

      {/* Important: Provider here has an empty fragment as children.
         Because the context provider renders no DOM wrapper, the player's <footer>
         is emitted right here as the last flex child, behaving like a normal page footer. */}
      <PlayerProvider>
        <></>
      </PlayerProvider>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </BrowserRouter>
  );
}
