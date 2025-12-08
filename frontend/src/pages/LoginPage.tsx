/**
 * NyayamGPT Login Page
 * Professional, modern login UI inspired by Perplexity/Notion
 */

import { useState, useCallback } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Button, Input } from "@/components/ui";
import { useAuthStore } from "@/hooks/useAuthStore";
import { cn } from "@/lib/utils";

// Icons
const MailIcon = () => (
  <svg
    xmlns='http://www.w3.org/2000/svg'
    width='18'
    height='18'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2'
    strokeLinecap='round'
    strokeLinejoin='round'
  >
    <rect width='20' height='16' x='2' y='4' rx='2' />
    <path d='m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7' />
  </svg>
);

const LockIcon = () => (
  <svg
    xmlns='http://www.w3.org/2000/svg'
    width='18'
    height='18'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2'
    strokeLinecap='round'
    strokeLinejoin='round'
  >
    <rect width='18' height='11' x='3' y='11' rx='2' ry='2' />
    <path d='M7 11V7a5 5 0 0 1 10 0v4' />
  </svg>
);

const EyeIcon = () => (
  <svg
    xmlns='http://www.w3.org/2000/svg'
    width='18'
    height='18'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2'
    strokeLinecap='round'
    strokeLinejoin='round'
  >
    <path d='M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z' />
    <circle cx='12' cy='12' r='3' />
  </svg>
);

const EyeOffIcon = () => (
  <svg
    xmlns='http://www.w3.org/2000/svg'
    width='18'
    height='18'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2'
    strokeLinecap='round'
    strokeLinejoin='round'
  >
    <path d='M9.88 9.88a3 3 0 1 0 4.24 4.24' />
    <path d='M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68' />
    <path d='M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61' />
    <line x1='2' x2='22' y1='2' y2='22' />
  </svg>
);

const LoaderIcon = () => (
  <svg
    className='animate-spin'
    xmlns='http://www.w3.org/2000/svg'
    width='18'
    height='18'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2'
    strokeLinecap='round'
    strokeLinejoin='round'
  >
    <path d='M21 12a9 9 0 1 1-6.219-8.56' />
  </svg>
);

const ScaleIcon = () => (
  <svg
    xmlns='http://www.w3.org/2000/svg'
    width='32'
    height='32'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2'
    strokeLinecap='round'
    strokeLinejoin='round'
  >
    <path d='m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z' />
    <path d='m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z' />
    <path d='M7 21h10' />
    <path d='M12 3v18' />
    <path d='M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2' />
  </svg>
);

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, error, clearError } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [validationErrors, setValidationErrors] = useState<{
    email?: string;
    password?: string;
  }>({});

  // Get redirect path from location state
  const from = (location.state as { from?: string })?.from || "/";

  const validate = useCallback(() => {
    const errors: { email?: string; password?: string } = {};

    if (!email) {
      errors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = "Please enter a valid email address";
    }

    if (!password) {
      errors.password = "Password is required";
    } else if (password.length < 6) {
      errors.password = "Password must be at least 6 characters";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [email, password]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      clearError();

      if (!validate()) return;

      try {
        await login({ email, password });
        navigate(from, { replace: true });
      } catch {
        // Error is already set in store
      }
    },
    [email, password, login, navigate, from, validate, clearError]
  );

  return (
    <div className='min-h-screen flex'>
      {/* Left side - Decorative */}
      <div className='hidden lg:flex lg:w-1/2 bg-gradient-to-br from-amber-500 via-orange-500 to-orange-600 relative overflow-hidden'>
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-20" />
        <div className='relative z-10 flex flex-col justify-center px-16 text-white'>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className='flex items-center gap-3 mb-8'>
              <ScaleIcon />
              <span className='text-3xl font-bold'>NyayamGPT</span>
            </div>
            <h1 className='text-4xl font-bold mb-4'>Your AI Legal Assistant</h1>
            <p className='text-lg text-white/90 mb-8 max-w-md'>
              Get instant answers to your legal questions with accurate
              citations from Indian law. Powered by AI, verified for accuracy.
            </p>
            <div className='flex flex-col gap-4'>
              <div className='flex items-center gap-3'>
                <div className='h-10 w-10 rounded-full bg-white/20 flex items-center justify-center'>
                  <svg
                    xmlns='http://www.w3.org/2000/svg'
                    width='20'
                    height='20'
                    viewBox='0 0 24 24'
                    fill='none'
                    stroke='currentColor'
                    strokeWidth='2'
                    strokeLinecap='round'
                    strokeLinejoin='round'
                  >
                    <polyline points='20 6 9 17 4 12' />
                  </svg>
                </div>
                <span>IPC, CrPC, and more covered</span>
              </div>
              <div className='flex items-center gap-3'>
                <div className='h-10 w-10 rounded-full bg-white/20 flex items-center justify-center'>
                  <svg
                    xmlns='http://www.w3.org/2000/svg'
                    width='20'
                    height='20'
                    viewBox='0 0 24 24'
                    fill='none'
                    stroke='currentColor'
                    strokeWidth='2'
                    strokeLinecap='round'
                    strokeLinejoin='round'
                  >
                    <polyline points='20 6 9 17 4 12' />
                  </svg>
                </div>
                <span>Verified legal citations</span>
              </div>
              <div className='flex items-center gap-3'>
                <div className='h-10 w-10 rounded-full bg-white/20 flex items-center justify-center'>
                  <svg
                    xmlns='http://www.w3.org/2000/svg'
                    width='20'
                    height='20'
                    viewBox='0 0 24 24'
                    fill='none'
                    stroke='currentColor'
                    strokeWidth='2'
                    strokeLinecap='round'
                    strokeLinejoin='round'
                  >
                    <polyline points='20 6 9 17 4 12' />
                  </svg>
                </div>
                <span>Simple, clear explanations</span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Decorative circles */}
        <div className='absolute -bottom-32 -left-32 w-96 h-96 rounded-full bg-white/10' />
        <div className='absolute -top-20 -right-20 w-72 h-72 rounded-full bg-white/10' />
      </div>

      {/* Right side - Login Form */}
      <div className='flex-1 flex items-center justify-center px-6 py-12 lg:px-8 bg-background'>
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className='w-full max-w-md'
        >
          {/* Mobile logo */}
          <div className='flex lg:hidden items-center justify-center gap-2 mb-8'>
            <div className='text-amber-500'>
              <ScaleIcon />
            </div>
            <span className='text-2xl font-bold'>NyayamGPT</span>
          </div>

          <div className='text-center mb-8'>
            <h2 className='text-2xl font-bold tracking-tight'>Welcome back</h2>
            <p className='mt-2 text-muted-foreground'>
              Sign in to your account to continue
            </p>
          </div>

          <form onSubmit={handleSubmit} className='space-y-5'>
            {/* Error Alert */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className='p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm'
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Email Field */}
            <div className='space-y-2'>
              <label htmlFor='email' className='text-sm font-medium'>
                Email address
              </label>
              <Input
                id='email'
                type='email'
                placeholder='you@example.com'
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setValidationErrors((v) => ({ ...v, email: undefined }));
                }}
                leftIcon={<MailIcon />}
                error={!!validationErrors.email}
                errorMessage={validationErrors.email}
                autoComplete='email'
                disabled={isLoading}
              />
            </div>

            {/* Password Field */}
            <div className='space-y-2'>
              <div className='flex items-center justify-between'>
                <label htmlFor='password' className='text-sm font-medium'>
                  Password
                </label>
                <Link
                  to='/forgot-password'
                  className='text-sm text-primary hover:underline'
                >
                  Forgot password?
                </Link>
              </div>
              <Input
                id='password'
                type={showPassword ? "text" : "password"}
                placeholder='••••••••'
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setValidationErrors((v) => ({ ...v, password: undefined }));
                }}
                leftIcon={<LockIcon />}
                rightIcon={
                  <button
                    type='button'
                    onClick={() => setShowPassword(!showPassword)}
                    className='hover:text-foreground transition-colors'
                  >
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                }
                error={!!validationErrors.password}
                errorMessage={validationErrors.password}
                autoComplete='current-password'
                disabled={isLoading}
              />
            </div>

            {/* Submit Button */}
            <Button
              type='submit'
              variant='gradient'
              size='lg'
              className='w-full'
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <LoaderIcon />
                  <span className='ml-2'>Signing in...</span>
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          {/* Divider */}
          <div className='relative my-8'>
            <div className='absolute inset-0 flex items-center'>
              <div className='w-full border-t border-border' />
            </div>
            <div className='relative flex justify-center text-xs uppercase'>
              <span className='bg-background px-2 text-muted-foreground'>
                New to NyayamGPT?
              </span>
            </div>
          </div>

          {/* Signup Link */}
          <div className='text-center'>
            <Link
              to='/signup'
              className={cn(
                "inline-flex items-center justify-center w-full h-11 px-4",
                "rounded-xl border border-input bg-background shadow-sm",
                "text-sm font-medium transition-all duration-200",
                "hover:bg-accent hover:text-accent-foreground"
              )}
            >
              Create an account
            </Link>
          </div>

          {/* Terms */}
          <p className='mt-8 text-center text-xs text-muted-foreground'>
            By signing in, you agree to our{" "}
            <Link to='/terms' className='underline hover:text-foreground'>
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link to='/privacy' className='underline hover:text-foreground'>
              Privacy Policy
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
