import { Link, useNavigate } from 'react-router-dom';

const AppNavbar = ({ activeTab }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const tabClass = (tab) =>
    tab === activeTab
      ? 'px-2 py-2 text-base font-semibold text-[#2563EB] border-b-4 border-[#2563EB] rounded-t-lg transition-colors'
      : 'px-2 py-2 text-base font-medium text-[#475569] hover:text-[#2563EB] transition-colors';

  return (
    <nav className="fixed top-0 left-0 w-full h-18 bg-white border-b border-black/5 flex items-center px-5 gap-5 z-50">
      <Link to="/" className="text-2xl font-bold tracking-[-1.2px] text-[#0F172A] flex-shrink-0">
        QLOP
      </Link>
      <div className="flex items-center gap-1 ml-4 h-full">
        <Link to="/analyze" className={tabClass('analyze')}>Analyze</Link>
        <Link to="/history" className={tabClass('history')}>History</Link>
      </div>
      <button
        onClick={handleLogout}
        className="ml-auto px-4 py-2 border border-red-200 text-red-600 hover:bg-red-50 text-sm font-semibold rounded-lg transition-all active:scale-[0.98]"
      >
        Logout
      </button>
    </nav>
  );
};

export default AppNavbar;
