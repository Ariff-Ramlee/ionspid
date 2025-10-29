import { useAuth } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";

export default function TopBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/auth");
  };

  return (
    <header className="fixed top-0 left-0 w-full bg-se-grayLight text-black flex justify-between items-center px-8 py-3 shadow z-50">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <img src="logo.png" alt="Logo" className="h-10" />
        <span className="font-bold text-xl tracking-wide">Sarawak Energy</span>
      </div>

      {/* Navigation */}
      <nav className="flex items-center gap-6">
        {user ? (
          <>
            <button
              onClick={handleLogout}
              className="bg-red-500 hover:bg-red-600 px-3 py-1 rounded-md text-sm font-medium"
            >
              Sign Out
            </button>
            <span className="font-semibold text-lg">Hi, {user.full_name}</span>
            <Link to="/" className="hover:text-se-blue text-lg">
              Home
            </Link>
          </>
        ) : (
          <>
            <a href="/" className="hover:text-se-blue text-lg">
              Home
            </a>
            <a href="/auth" className="hover:text-se-blue text-lg">
              Log In / Sign Up
            </a>
          
          </>
        )}
      </nav>
    </header>
  );
}
