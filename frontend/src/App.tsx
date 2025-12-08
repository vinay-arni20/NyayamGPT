import { Suspense, lazy } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import { PageLoader } from "./components/ui/PageLoader";
import { useTheme } from "./hooks/useTheme";
import { AuthProvider, ProtectedRoute, GuestRoute } from "./components/auth";

// Lazy load pages
const ChatPage = lazy(() => import("./pages/ChatPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const SignupPage = lazy(() => import("./pages/SignupPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));

function App() {
  // Initialize theme globally
  useTheme();

  return (
    <HelmetProvider>
      <Router>
        <AuthProvider>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route
                path='/'
                element={
                  <ProtectedRoute>
                    <ChatPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path='/login'
                element={
                  <GuestRoute>
                    <LoginPage />
                  </GuestRoute>
                }
              />
              <Route
                path='/signup'
                element={
                  <GuestRoute>
                    <SignupPage />
                  </GuestRoute>
                }
              />
              <Route path='/about' element={<AboutPage />} />
              <Route path='*' element={<Navigate to='/' replace />} />
            </Routes>
          </Suspense>
        </AuthProvider>
      </Router>
    </HelmetProvider>
  );
}

export default App;
