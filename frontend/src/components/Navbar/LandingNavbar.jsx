import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Button from '../Button/Button';

const LandingNavbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 w-full bg-white/90 backdrop-blur-md border-b border-gray-200">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-12">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex-shrink-0">
            <Link to="/" className="flex items-center gap-2">
              <img
                src="/logo.png"
                alt="QLOP Logo"
                className="w-8 h-8 object-contain"
              />
              <span className="text-2xl font-black text-gray-900 tracking-tighter">
                QLOP
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex space-x-10 items-center">
            <a href="/#how-to-use" className="text-sm font-semibold text-gray-600 hover:text-gray-900 transition-colors">
              How to Use
            </a>
            <a href="/#streamlit" className="text-sm font-semibold text-gray-600 hover:text-gray-900 transition-colors">
              Streamlit
            </a>
            <Link to="/about" className="text-sm font-semibold text-gray-600 hover:text-gray-900 transition-colors">
              About Us
            </Link>
          </div>

          {/* Desktop Auth Buttons */}
          <div className="hidden md:flex items-center gap-6">
            <Link to="/login" className="text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors">
              Login
            </Link>
            <div className="w-24">
              <Link to="/register">
                <Button variant="primary">Register</Button>
              </Link>
            </div>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="text-gray-600 hover:text-gray-900 focus:outline-none p-2 cursor-pointer"
            >
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Panel */}
      {isOpen && (
        <div className="md:hidden absolute w-full left-0 bg-white border-b border-gray-100 shadow-xl px-4 pt-2 pb-6 space-y-4">
          <a 
            href="/#how-to-use" 
            onClick={() => setIsOpen(false)}
            className="block text-base font-semibold text-gray-700 hover:text-blue-600 py-2"
          >
            How to Use
          </a>
          <a 
            href="/#streamlit" 
            onClick={() => setIsOpen(false)}
            className="block text-base font-semibold text-gray-700 hover:text-blue-600 py-2"
          >
            Streamlit
          </a>
          <Link 
            to="/about" 
            onClick={() => setIsOpen(false)}
            className="block text-base font-semibold text-gray-700 hover:text-blue-600 py-2"
          >
            About Us
          </Link>
          
          <div className="pt-4 mt-2 border-t border-gray-100 flex flex-col gap-3">
            <Link to="/login" onClick={() => setIsOpen(false)}>
              <Button variant="outline">Login to Dashboard</Button>
            </Link>
            <Link to="/register" onClick={() => setIsOpen(false)}>
              <Button variant="primary">Register Now</Button>
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
};

export default LandingNavbar;