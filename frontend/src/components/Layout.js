import TopBar from "./TopBar";
import Sidebar from "./Sidebar";
import Footer from "./Footer";
import { useAuth } from "../context/AuthContext";
import { useProgress } from "../context/ProgressContext";

export default function Layout({ children }) {
  const { user } = useAuth();
  const { uploaded, analysisDone } = useProgress();

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <TopBar />

      {/* Middle section fills all available vertical space */}
      <div className="flex flex-1 pt-16">
        {user && (
          <Sidebar uploaded={uploaded} analysisDone={analysisDone} />
        )}

        {/* ✅ Make main take all height and remove default margin */}
        <main className="flex-1 p-6 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* ✅ Footer sticks to the very bottom */}
      <Footer />
    </div>
  );
}
