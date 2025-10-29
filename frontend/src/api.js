import axios from "axios";

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || `http://${window.location.hostname}:5000/api`,
});

// Attach token automatically
API.interceptors.request.use((config) => {
  const storedUser = sessionStorage.getItem("user"); // ✅ fixed
  if (storedUser) {
    const { token } = JSON.parse(storedUser);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  console.log("Attaching token:", config.headers.Authorization);
  return config;
});

// Exports
export const loginUser = (data) => API.post("/users/login", data);
export const signupUser = (data) => API.post("/users/signup", data);
export const getProfile = () => API.get("/users/me");
export const uploadFile = (formData) => API.post("/files/upload", formData);

export default API;
