// src/components/ProtectedRoute.js
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user } = useAuth();

  // If no user, redirect to login/signup page
  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  // If logged in, render the page
  return children;
}
