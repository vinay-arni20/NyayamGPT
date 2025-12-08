/**
 * NyayamGPT Signup Page
 * Professional, modern signup UI with role selection
 */

import { useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Button, Input, Select } from "@/components/ui";
import { useAuthStore } from "@/hooks/useAuthStore";
import { cn } from "@/lib/utils";

// Icons
const UserIcon = () => (
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
    <path d='M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2' />
    <circle cx='12' cy='7' r='4' />
  </svg>
);

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

const CheckIcon = () => (
  <svg
    xmlns='http://www.w3.org/2000/svg'
    width='14'
    height='14'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2.5'
    strokeLinecap='round'
    strokeLinejoin='round'
  >
    <polyline points='20 6 9 17 4 12' />
  </svg>
);

const XIcon = () => (
  <svg
    xmlns='http://www.w3.org/2000/svg'
    width='14'
    height='14'
    viewBox='0 0 24 24'
    fill='none'
    stroke='currentColor'
    strokeWidth='2.5'
    strokeLinecap='round'
    strokeLinejoin='round'
  >
    <line x1='18' y1='6' x2='6' y2='18' />
    <line x1='6' y1='6' x2='18' y2='18' />
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

interface FormData {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
  language: string;
}

interface ValidationErrors {
  fullName?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

const languageOptions = [
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi (हिन्दी)" },
  { value: "ta", label: "Tamil (தமிழ்)" },
  { value: "te", label: "Telugu (తెలుగు)" },
  { value: "bn", label: "Bengali (বাংলা)" },
  { value: "mr", label: "Marathi (मराठी)" },
  { value: "gu", label: "Gujarati (ગુજરાતી)" },
  { value: "kn", label: "Kannada (ಕನ್ನಡ)" },
];

// Password strength checker
function checkPasswordStrength(password: string) {
  return {
    hasMinLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecial: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };
}

export default function SignupPage() {
  const navigate = useNavigate();
  const { signup, isLoading, error, clearError } = useAuthStore();

  const [formData, setFormData] = useState<FormData>({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
    language: "en",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>(
    {}
  );
  const [step, setStep] = useState(1);

  const passwordStrength = checkPasswordStrength(formData.password);
  const isPasswordValid = Object.values(passwordStrength).every(Boolean);

  const updateField = useCallback(
    (field: keyof FormData, value: string) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
      setValidationErrors((prev) => ({ ...prev, [field]: undefined }));
      clearError();
    },
    [clearError]
  );

  const validateStep1 = useCallback(() => {
    const errors: ValidationErrors = {};

    if (!formData.fullName.trim()) {
      errors.fullName = "Full name is required";
    } else if (formData.fullName.trim().length < 2) {
      errors.fullName = "Name must be at least 2 characters";
    }

    if (!formData.email) {
      errors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = "Please enter a valid email address";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formData]);

  const validateStep2 = useCallback(() => {
    const errors: ValidationErrors = {};

    if (!formData.password) {
      errors.password = "Password is required";
    } else if (!isPasswordValid) {
      errors.password = "Password does not meet all requirements";
    }

    if (!formData.confirmPassword) {
      errors.confirmPassword = "Please confirm your password";
    } else if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = "Passwords do not match";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formData, isPasswordValid]);

  const handleNext = useCallback(() => {
    if (step === 1 && validateStep1()) {
      setStep(2);
    }
  }, [step, validateStep1]);

  const handleBack = useCallback(() => {
    setStep(1);
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      clearError();

      if (!validateStep2()) return;

      try {
        await signup({
          email: formData.email,
          password: formData.password,
          confirm_password: formData.confirmPassword,
          full_name: formData.fullName,
          role: "citizen",
          preferred_language: formData.language,
        });
        navigate("/", { replace: true });
      } catch {
        // Error is already set in store
      }
    },
    [formData, signup, navigate, validateStep2, clearError]
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
            <h1 className='text-4xl font-bold mb-4'>
              Join India's Legal AI Platform
            </h1>
            <p className='text-lg text-white/90 mb-8 max-w-md'>
              Create your account and get access to instant legal insights,
              verified citations, and AI-powered legal assistance.
            </p>
          </motion.div>
        </div>

        {/* Decorative circles */}
        <div className='absolute -bottom-32 -left-32 w-96 h-96 rounded-full bg-white/10' />
        <div className='absolute -top-20 -right-20 w-72 h-72 rounded-full bg-white/10' />
      </div>

      {/* Right side - Signup Form */}
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

          {/* Step indicator */}
          <div className='flex items-center justify-center gap-2 mb-6'>
            <div
              className={cn(
                "h-2 w-8 rounded-full transition-colors",
                step >= 1 ? "bg-amber-500" : "bg-muted"
              )}
            />
            <div
              className={cn(
                "h-2 w-8 rounded-full transition-colors",
                step >= 2 ? "bg-amber-500" : "bg-muted"
              )}
            />
          </div>

          <div className='text-center mb-8'>
            <h2 className='text-2xl font-bold tracking-tight'>
              {step === 1 ? "Create your account" : "Secure your account"}
            </h2>
            <p className='mt-2 text-muted-foreground'>
              {step === 1
                ? "Enter your details to get started"
                : "Create a strong password"}
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

            {/* Step 1: Basic Info */}
            <AnimatePresence mode='wait'>
              {step === 1 && (
                <motion.div
                  key='step1'
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className='space-y-4'
                >
                  {/* Full Name */}
                  <div className='space-y-2'>
                    <label htmlFor='fullName' className='text-sm font-medium'>
                      Full Name
                    </label>
                    <Input
                      id='fullName'
                      type='text'
                      placeholder='Your full name'
                      value={formData.fullName}
                      onChange={(e) => updateField("fullName", e.target.value)}
                      leftIcon={<UserIcon />}
                      error={!!validationErrors.fullName}
                      errorMessage={validationErrors.fullName}
                      autoComplete='name'
                    />
                  </div>

                  {/* Email */}
                  <div className='space-y-2'>
                    <label htmlFor='email' className='text-sm font-medium'>
                      Email address
                    </label>
                    <Input
                      id='email'
                      type='email'
                      placeholder='you@example.com'
                      value={formData.email}
                      onChange={(e) => updateField("email", e.target.value)}
                      leftIcon={<MailIcon />}
                      error={!!validationErrors.email}
                      errorMessage={validationErrors.email}
                      autoComplete='email'
                    />
                  </div>

                  {/* Language */}
                  <div className='space-y-2'>
                    <label htmlFor='language' className='text-sm font-medium'>
                      Preferred Language
                    </label>
                    <Select
                      id='language'
                      value={formData.language}
                      onChange={(e) => updateField("language", e.target.value)}
                      options={languageOptions}
                    />
                  </div>

                  <Button
                    type='button'
                    variant='gradient'
                    size='lg'
                    className='w-full'
                    onClick={handleNext}
                  >
                    Continue
                  </Button>
                </motion.div>
              )}

              {/* Step 2: Password */}
              {step === 2 && (
                <motion.div
                  key='step2'
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className='space-y-4'
                >
                  {/* Password */}
                  <div className='space-y-2'>
                    <label htmlFor='password' className='text-sm font-medium'>
                      Password
                    </label>
                    <Input
                      id='password'
                      type={showPassword ? "text" : "password"}
                      placeholder='Create a strong password'
                      value={formData.password}
                      onChange={(e) => updateField("password", e.target.value)}
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
                      autoComplete='new-password'
                      disabled={isLoading}
                    />
                  </div>

                  {/* Password Requirements */}
                  <div className='p-4 rounded-xl bg-muted/50 space-y-2'>
                    <p className='text-xs font-medium text-muted-foreground mb-2'>
                      Password requirements:
                    </p>
                    <div className='grid grid-cols-2 gap-2 text-xs'>
                      <PasswordRequirement
                        met={passwordStrength.hasMinLength}
                        text='8+ characters'
                      />
                      <PasswordRequirement
                        met={passwordStrength.hasUppercase}
                        text='Uppercase letter'
                      />
                      <PasswordRequirement
                        met={passwordStrength.hasLowercase}
                        text='Lowercase letter'
                      />
                      <PasswordRequirement
                        met={passwordStrength.hasNumber}
                        text='Number'
                      />
                      <PasswordRequirement
                        met={passwordStrength.hasSpecial}
                        text='Special character'
                      />
                    </div>
                  </div>

                  {/* Confirm Password */}
                  <div className='space-y-2'>
                    <label
                      htmlFor='confirmPassword'
                      className='text-sm font-medium'
                    >
                      Confirm Password
                    </label>
                    <Input
                      id='confirmPassword'
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder='Confirm your password'
                      value={formData.confirmPassword}
                      onChange={(e) =>
                        updateField("confirmPassword", e.target.value)
                      }
                      leftIcon={<LockIcon />}
                      rightIcon={
                        <button
                          type='button'
                          onClick={() =>
                            setShowConfirmPassword(!showConfirmPassword)
                          }
                          className='hover:text-foreground transition-colors'
                        >
                          {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
                        </button>
                      }
                      error={!!validationErrors.confirmPassword}
                      errorMessage={validationErrors.confirmPassword}
                      autoComplete='new-password'
                      disabled={isLoading}
                    />
                  </div>

                  <div className='flex gap-3'>
                    <Button
                      type='button'
                      variant='outline'
                      size='lg'
                      className='flex-1'
                      onClick={handleBack}
                      disabled={isLoading}
                    >
                      Back
                    </Button>
                    <Button
                      type='submit'
                      variant='gradient'
                      size='lg'
                      className='flex-1'
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <>
                          <LoaderIcon />
                          <span className='ml-2'>Creating...</span>
                        </>
                      ) : (
                        "Create Account"
                      )}
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </form>

          {/* Divider */}
          <div className='relative my-8'>
            <div className='absolute inset-0 flex items-center'>
              <div className='w-full border-t border-border' />
            </div>
            <div className='relative flex justify-center text-xs uppercase'>
              <span className='bg-background px-2 text-muted-foreground'>
                Already have an account?
              </span>
            </div>
          </div>

          {/* Login Link */}
          <div className='text-center'>
            <Link
              to='/login'
              className={cn(
                "inline-flex items-center justify-center w-full h-11 px-4",
                "rounded-xl border border-input bg-background shadow-sm",
                "text-sm font-medium transition-all duration-200",
                "hover:bg-accent hover:text-accent-foreground"
              )}
            >
              Sign in instead
            </Link>
          </div>

          {/* Terms */}
          <p className='mt-8 text-center text-xs text-muted-foreground'>
            By creating an account, you agree to our{" "}
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

// Password requirement indicator component
function PasswordRequirement({ met, text }: { met: boolean; text: string }) {
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 transition-colors",
        met ? "text-green-600 dark:text-green-400" : "text-muted-foreground"
      )}
    >
      {met ? <CheckIcon /> : <XIcon />}
      <span>{text}</span>
    </div>
  );
}
