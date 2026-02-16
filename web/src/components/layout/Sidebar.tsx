import { Link, useLocation } from 'react-router-dom';

export function Sidebar() {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path
      ? 'bg-brand-800 text-white'
      : 'text-gray-300 hover:bg-brand-900 hover:text-white';
  };

  return (
    <div className="w-64 bg-brand-900 text-white flex flex-col">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-brand-400">Agent Trade</h1>
        <p className="text-sm text-brand-300 mt-1">Multi-Agent Trading</p>
      </div>
      <nav className="flex-1 px-4 space-y-1">
        <Link
          to="/"
          className={`block px-4 py-3 rounded-lg transition-colors ${isActive('/')}`}
        >
          <div className="flex items-center">
            <span className="text-lg mr-3">📊</span>
            <span>Dashboard</span>
          </div>
        </Link>
      </nav>
      <div className="p-4 text-xs text-brand-300">
        <p>Agent Trade v1.0</p>
      </div>
    </div>
  );
}
