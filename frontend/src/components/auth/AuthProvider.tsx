/**
 * NyayamGPT Auth Components
 * Protected route wrappers and auth context
 */

import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuthStore } from "@/hooks/useAuthStore";
import type { UserRole } from "@/types";

// Loading spinner component
function AuthLoading() {
  return (
    <div className='min-h-screen flex items-center justify-center bg-background'>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className='flex flex-col items-center gap-4'
      >
        <div className='relative'>
          <div className='h-12 w-12 rounded-full border-4 border-amber-500/30' />
          <div className='absolute top-0 left-0 h-12 w-12 rounded-full border-4 border-amber-500 border-t-transparent animate-spin' />
        </div>
        <p className='text-muted-foreground text-sm'>Loading...</p>
      </motion.div>
    </div>
  );
}

interface AuthProviderProps {
  children: React.ReactNode;
}

/**
 * AuthProvider - Initializes auth state on app load
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [isInitialized, setIsInitialized] = useState(false);
  const checkAuth = useAuthStore((state) => state.checkAuth);

  useEffect(() => {
    const init = async () => {
      try {
        await checkAuth();
      } catch {
        // Ignore errors, user is just not authenticated
      } finally {
        setIsInitialized(true);
      }
    };
    init();
  }, [checkAuth]);

  if (!isInitialized) {
    return <AuthLoading />;
  }

  return <>{children}</>;
}

interface ProtectedRouteProps {
  children: React.ReactNode;
  roles?: UserRole[];
  requireAuth?: boolean;
}

/**
 * ProtectedRoute - Restricts access to authenticated users
 * Optionally checks for specific roles
 */
export function ProtectedRoute({
  children,
  roles,
  requireAuth = true,
}: ProtectedRouteProps) {
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user = useAuthStore((state) => state.user);
  const isLoading = useAuthStore((state) => state.isLoading);

  // Show loading while checking auth
  if (isLoading) {
    return <AuthLoading />;
  }

  // Redirect to login if not authenticated
  if (requireAuth && !isAuthenticated) {
    return <Navigate to='/login' state={{ from: location.pathname }} replace />;
  }

  // Check role requirements
  if (roles && roles.length > 0 && user) {
    if (!roles.includes(user.role)) {
      // User doesn't have required role
      return (
        <div className='min-h-screen flex items-center justify-center bg-background'>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className='text-center p-8'
          >
            <div className='text-6xl mb-4'>🔒</div>
            <h1 className='text-2xl font-bold mb-2'>Access Denied</h1>
            <p className='text-muted-foreground mb-6'>
              You don't have permission to access this page.
            </p>
            <a href='/' className='text-primary hover:underline'>
              Go back to home
            </a>
          </motion.div>
        </div>
      );
    }
  }

  return <>{children}</>;
}

interface GuestRouteProps {
  children: React.ReactNode;
}

/**
 * GuestRoute - Only accessible to non-authenticated users
 * Redirects to home if already logged in
 */
export function GuestRoute({ children }: GuestRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const location = useLocation();

  // Get redirect path from location state or default to home
  const from = (location.state as { from?: string })?.from || "/";

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  return <>{children}</>;
}
