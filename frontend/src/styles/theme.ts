/**
 * NyayamGPT Premium Theme System
 * ================================
 * Glassmorphism design with premium legal-tech aesthetics
 */

// Typography
export const fonts = {
  heading: "'Playfair Display', Georgia, serif",
  body: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  mono: "'JetBrains Mono', 'Fira Code', monospace",
};

// Premium Color Palette
export const colors = {
  // Brand Colors
  gold: {
    50: '#fefce8',
    100: '#fef9c3',
    200: '#fef08a',
    300: '#fde047',
    400: '#facc15',
    500: '#d4af37', // Primary gold
    600: '#b8972f',
    700: '#9a7b27',
    800: '#7c5f1f',
    900: '#5e4317',
  },
  
  // Mode Colors
  modes: {
    normal: {
      primary: '#3b82f6', // Blue
      secondary: '#60a5fa',
      bg: 'linear-gradient(135deg, #1e3a8a 0%, #1e40af 50%, #2563eb 100%)',
      light: '#dbeafe',
    },
    lawyer: {
      primary: '#d4af37', // Gold
      secondary: '#f59e0b',
      bg: 'linear-gradient(135deg, #78350f 0%, #92400e 50%, #b45309 100%)',
      light: '#fef3c7',
    },
    qa: {
      primary: '#22c55e', // Green
      secondary: '#4ade80',
      bg: 'linear-gradient(135deg, #14532d 0%, #166534 50%, #15803d 100%)',
      light: '#dcfce7',
    },
    web: {
      primary: '#f97316', // Orange
      secondary: '#fb923c',
      bg: 'linear-gradient(135deg, #7c2d12 0%, #9a3412 50%, #c2410c 100%)',
      light: '#ffedd5',
    },
    deep: {
      primary: '#a855f7', // Purple
      secondary: '#c084fc',
      bg: 'linear-gradient(135deg, #581c87 0%, #6b21a8 50%, #7e22ce 100%)',
      light: '#f3e8ff',
    },
  },
  
  // Dark Mode Colors
  dark: {
    bg: {
      primary: '#0a0a0a',
      secondary: '#141414',
      tertiary: '#1a1a1a',
      elevated: '#1f1f1f',
    },
    border: {
      subtle: '#2a2a2a',
      default: '#333333',
      strong: '#404040',
    },
    text: {
      primary: '#fafafa',
      secondary: '#a3a3a3',
      muted: '#737373',
      accent: '#d4af37',
    },
  },
  
  // Light Mode Colors
  light: {
    bg: {
      primary: '#fafafa',
      secondary: '#ffffff',
      tertiary: '#f5f5f5',
      elevated: '#ffffff',
    },
    border: {
      subtle: '#e5e5e5',
      default: '#d4d4d4',
      strong: '#a3a3a3',
    },
    text: {
      primary: '#0a0a0a',
      secondary: '#525252',
      muted: '#737373',
      accent: '#b8972f',
    },
  },
};

// Glassmorphism Effects
export const glassmorphism = {
  light: {
    background: 'rgba(255, 255, 255, 0.7)',
    backdropFilter: 'blur(12px) saturate(180%)',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)',
  },
  dark: {
    background: 'rgba(20, 20, 20, 0.8)',
    backdropFilter: 'blur(12px) saturate(180%)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
  },
  strong: {
    background: 'rgba(255, 255, 255, 0.9)',
    backdropFilter: 'blur(20px) saturate(200%)',
    border: '1px solid rgba(255, 255, 255, 0.5)',
    boxShadow: '0 12px 48px rgba(0, 0, 0, 0.12)',
  },
};

// Shadows
export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
  gold: '0 4px 14px rgba(212, 175, 55, 0.25)',
  glow: {
    blue: '0 0 20px rgba(59, 130, 246, 0.5)',
    gold: '0 0 20px rgba(212, 175, 55, 0.5)',
    green: '0 0 20px rgba(34, 197, 94, 0.5)',
    orange: '0 0 20px rgba(249, 115, 22, 0.5)',
    purple: '0 0 20px rgba(168, 85, 247, 0.5)',
  },
};

// Animations
export const animations = {
  spring: {
    type: 'spring',
    stiffness: 300,
    damping: 30,
  },
  smooth: {
    type: 'tween',
    duration: 0.3,
    ease: 'easeInOut',
  },
  bounce: {
    type: 'spring',
    stiffness: 400,
    damping: 17,
  },
};

// Border Radius
export const radii = {
  sm: '6px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '24px',
  full: '9999px',
};

// Spacing
export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  '2xl': '48px',
  '3xl': '64px',
};

// Breakpoints
export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

// Z-Index Layers
export const zIndex = {
  base: 0,
  dropdown: 100,
  sticky: 200,
  modal: 300,
  popover: 400,
  tooltip: 500,
  toast: 600,
};

// Mode Configurations - v2.0 with 2023 Criminal Code Support
export const modeConfig = {
  normal: {
    id: 'normal',
    name: 'Normal User',
    description: 'Simple explanations in 11+ languages including Hindi, Tamil, Bengali',
    icon: 'User',
    color: colors.modes.normal.primary,
    gradient: colors.modes.normal.bg,
    placeholder: 'Ask about Indian laws (IPC/BNS) in simple language...',
  },
  lawyer: {
    id: 'lawyer',
    name: 'Lawyer Mode',
    description: 'Precise legal analysis with BNS 2023, BNSS, BSA cross-references',
    icon: 'Scale',
    color: colors.modes.lawyer.primary,
    gradient: colors.modes.lawyer.bg,
    placeholder: 'Ask for detailed legal analysis with IPC/BNS sections...',
  },
  qa: {
    id: 'qa',
    name: 'Quick Q&A',
    description: 'Instant answers with <2% hallucination rate',
    icon: 'Zap',
    color: colors.modes.qa.primary,
    gradient: colors.modes.qa.bg,
    placeholder: 'Ask for a quick verified answer...',
  },
  web: {
    id: 'web',
    name: 'Web Search',
    description: 'Latest legal updates, court judgments & news',
    icon: 'Globe',
    color: colors.modes.web.primary,
    gradient: colors.modes.web.bg,
    placeholder: 'Search for latest legal news and judgments...',
  },
  deep: {
    id: 'deep',
    name: 'Deep Research',
    description: 'Expert analysis with citations from 11 legal codes',
    icon: 'BookOpen',
    color: colors.modes.deep.primary,
    gradient: colors.modes.deep.bg,
    placeholder: 'Ask for in-depth research across IPC, BNS, CrPC, BNSS...',
  },
};

// Theme Object
export const theme = {
  fonts,
  colors,
  glassmorphism,
  shadows,
  animations,
  radii,
  spacing,
  breakpoints,
  zIndex,
  modeConfig,
};

export type ThemeMode = 'light' | 'dark';
export type ChatMode = keyof typeof modeConfig;

export default theme;
