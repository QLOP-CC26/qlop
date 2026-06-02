import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Button from '../Button/Button';

const AppNavbar = ({ activeTab }) => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  const tabClass = (tab) =>
    tab === activeTab
      ? 'text-sm font-bold text-blue-600 transition-colors'
      : 'text-sm font-semibold text-gray-600 hover:text-gray-900 transition-colors';

  return (
    <nav className="fixed top-0 left-0 z-50 w-full bg-white/90 backdrop-blur-md border-b border-gray-200">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-12 w-full">
        <div className="flex items-center justify-between h-16 w-full">
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
            <Link to="/analyze" className={tabClass('analyze')}>
              Analyze
            </Link>
            <Link to="/history" className={tabClass('history')}>
              History
            </Link>
          </div>

          {/* Desktop Auth/Actions */}
          <div className="hidden md:flex items-center gap-6">
            <div className="w-24">
              <Button variant="outline" onClick={handleLogout}>
                Logout
              </Button>
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
        <div className="md:hidden absolute w-full left-0 top-16 bg-white border-b border-gray-100 shadow-xl px-4 pt-2 pb-6 space-y-4">
          <Link
            to="/analyze"
            onClick={() => setIsOpen(false)}
            className={`block text-base font-semibold py-2 ${
              activeTab === 'analyze' ? 'text-blue-600' : 'text-gray-700 hover:text-blue-600'
            }`}
          >
            Analyze
          </Link>
          <Link
            to="/history"
            onClick={() => setIsOpen(false)}
            className={`block text-base font-semibold py-2 ${
              activeTab === 'history' ? 'text-blue-600' : 'text-gray-700 hover:text-blue-600'
            }`}
          >
            History
          </Link>
          
          <div className="pt-4 mt-2 border-t border-gray-100 flex flex-col gap-3">
            <Button
              variant="outline"
              onClick={() => {
                setIsOpen(false);
                handleLogout();
              }}
            >
              Logout
            </Button>
          </div>
        </div>
      )}
    </nav>
  );
};

export default AppNavbar;
