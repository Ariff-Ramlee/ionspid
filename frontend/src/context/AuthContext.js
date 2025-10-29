import { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);   // user profile
  const [token, setToken] = useState(null); // jwt token

  // Load from sessionStorage on startup
  useEffect(() => {
    const stored = sessionStorage.getItem("user");
    if (stored) {
      const parsed = JSON.parse(stored);
      setUser(parsed.user);
      setToken(parsed.token);
    }
  }, []);

  // Save both user + token
  const login = (data) => {
    setUser(data.user);
    setToken(data.token);
    sessionStorage.setItem("user", JSON.stringify(data)); // keep {user, token}
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    sessionStorage.removeItem("user");
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
