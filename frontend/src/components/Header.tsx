import { Scale, Github, Menu } from "lucide-react";
import { useState } from "react";

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className='bg-white border-b border-gray-200 sticky top-0 z-50'>
      <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'>
        <div className='flex justify-between items-center h-16'>
          {/* Logo */}
          <div className='flex items-center gap-3'>
            <div className='w-10 h-10 rounded-xl gradient-saffron flex items-center justify-center shadow-md'>
              <Scale className='w-6 h-6 text-white' />
            </div>
            <div>
              <h1 className='text-xl font-bold text-gray-900'>NyayamGPT</h1>
              <p className='text-xs text-gray-500 hidden sm:block'>
                Indian Legal AI Assistant
              </p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className='hidden md:flex items-center gap-6'>
            <a
              href='#features'
              className='text-sm font-medium text-gray-600 hover:text-saffron-600 transition-colors'
            >
              Features
            </a>
            <a
              href='#about'
              className='text-sm font-medium text-gray-600 hover:text-saffron-600 transition-colors'
            >
              About
            </a>
            <a
              href='https://github.com'
              target='_blank'
              rel='noopener noreferrer'
              className='flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-saffron-600 transition-colors'
            >
              <Github className='w-4 h-4' />
              GitHub
            </a>
          </nav>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className='md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100'
            aria-label='Toggle mobile menu'
            title='Toggle menu'
          >
            <Menu className='w-6 h-6' />
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className='md:hidden py-4 border-t border-gray-100'>
            <div className='flex flex-col gap-4'>
              <a
                href='#features'
                className='text-sm font-medium text-gray-600 hover:text-saffron-600'
              >
                Features
              </a>
              <a
                href='#about'
                className='text-sm font-medium text-gray-600 hover:text-saffron-600'
              >
                About
              </a>
              <a
                href='https://github.com'
                target='_blank'
                rel='noopener noreferrer'
                className='flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-saffron-600'
              >
                <Github className='w-4 h-4' />
                GitHub
              </a>
            </div>
          </nav>
        )}
      </div>
    </header>
  );
}
