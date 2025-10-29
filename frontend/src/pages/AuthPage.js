import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { loginUser, signupUser } from "../api";

export default function AuthPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [isLogin, setIsLogin] = useState(true);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    staff_role: "Intern",
  });
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      let data;
      if (isLogin) {
        const res = await loginUser({ email: form.email, password: form.password });
        data = res.data;
      } else {
        const res = await signupUser(form);
        data = res.data;
      }

      login(data); // Save to AuthContext (sessionStorage inside)
      navigate("/upload");
    } catch (err) {
      setError(err.response?.data?.error || "Something went wrong");
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 px-4">
      <div className="w-full max-w-lg bg-white rounded-lg shadow-lg p-10">
        {/* Tabs */}
        <div className="flex mb-8 border-b">
          <button
            className={`flex-1 py-3 text-lg font-semibold ${
              isLogin ? "border-b-2 border-se-blue text-se-blue" : "text-gray-500"
            }`}
            onClick={() => setIsLogin(true)}
          >
            Log In
          </button>
          <button
            className={`flex-1 py-3 text-lg font-semibold ${
              !isLogin ? "border-b-2 border-se-blue text-se-blue" : "text-gray-500"
            }`}
            onClick={() => setIsLogin(false)}
          >
            Sign Up
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {!isLogin && (
            <input
              type="text"
              name="full_name"
              placeholder="Full Name"
              value={form.full_name}
              onChange={handleChange}
              className="w-full border rounded-md px-5 py-3 text-lg"
              required
            />
          )}
          <input
            type="email"
            name="email"
            placeholder="Email"
            value={form.email}
            onChange={handleChange}
            className="w-full border rounded-md px-5 py-3 text-lg"
            required
          />
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              name="password"
              placeholder="Password"
              value={form.password}
              onChange={handleChange}
              className="w-full border rounded-md px-5 py-3 text-lg"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-3 flex items-center text-sm text-gray-500"
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
          {!isLogin && (
            <select
              name="staff_role"
              value={form.staff_role}
              onChange={handleChange}
              className="w-full border rounded-md px-5 py-3 text-lg"
            >
              <option value="Intern">Intern</option>
              <option value="Staff">Staff</option>
              <option value="Admin">Admin</option>
            </select>
          )}
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            className="w-full bg-se-blue hover:bg-se-lime text-white font-semibold py-3 rounded-md text-lg transition"
          >
            {isLogin ? "Log In" : "Sign Up"}
          </button>
        </form>
      </div>
    </div>
  );
}
