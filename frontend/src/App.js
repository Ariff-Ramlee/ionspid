import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import AuthPage from "./pages/AuthPage";
import UploadPage from "./pages/UploadPage";
import AnalysisPage from "./pages/AnalysisPage";
import ResultPage from "./pages/ResultPage";
import ProtectedRoute from "./components/ProtectedRoute";
import HistoryPage from "./pages/HistoryPage";

function App() {
  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Home />} />
        <Route path="/auth" element={<AuthPage />} />

        {/* Protected routes */}
        <Route
          path="/upload"
          element={
            <ProtectedRoute>
              <UploadPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analysis"
          element={
            <ProtectedRoute>
              <AnalysisPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/result"
          element={
            <ProtectedRoute>
              <ResultPage />
            </ProtectedRoute>
          }
        />
        <Route 
          path="/history" 
          element={
          <ProtectedRoute>
            <HistoryPage />
          </ProtectedRoute>
        }
       />
      </Routes>
    </Router>
  );
}

export default App;
