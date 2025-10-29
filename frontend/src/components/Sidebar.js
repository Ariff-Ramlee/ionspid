import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { useProgress } from "../context/ProgressContext";

export default function Sidebar({ className = "" }) {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(true);

  // Get from context
  const { uploaded, analysisDone } = useProgress();

  return (
    <aside
      className={`bg-se-gray text-white flex flex-col p-4 space-y-3 transition-all duration-300 
        ${isOpen ? "w-52" : "w-16"} ${className}`}
    >
      {/* Collapse / Expand */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bg-se-blue px-2 py-1 rounded-md text-left hover:bg-se-midgray"
      >
        {isOpen ? "⬅️ Collapse" : "➡️"}
      </button>

      {/* Upload (always blue) */}
      <button
        onClick={() => navigate("/upload")}
        className={`py-2 px-1 rounded-md font-medium transition ${
          isOpen ? "text-left" : "text-left"
        } bg-se-blue hover:bg-se-midgray`}
      >
        {isOpen ? "📁 Upload" : "📁"}
      </button>

      {/* Analysis (red until upload is done) */}
      <button
        disabled={!uploaded}
        onClick={() => uploaded && navigate("/analysis")}
        className={`py-2 px-1 rounded-md font-medium transition ${
          isOpen ? "text-left" : "text-left"
        } ${
          uploaded
            ? "bg-se-blue hover:bg-se-midgray"
            : "bg-red-400 cursor-not-allowed"
        }`}
      >
        {isOpen ? "🧬 Analysis" : "🧬"}
      </button>

      {/* Result (red until analysis is done) */}
      <button
        disabled={!analysisDone}
        onClick={() => analysisDone && navigate("/result")}
        className={`py-2 px-1 rounded-md font-medium transition ${
          isOpen ? "text-left" : "text-left"
        } ${
          analysisDone
            ? "bg-se-blue hover:bg-se-midgray"
            : "bg-red-400 cursor-not-allowed"
        }`}
      >
        {isOpen ? "📊 Result" : "📊"}
      </button>

      {/* History (always blue) */}
      <button
        onClick={() => navigate("/history")}
        className={`py-2 px-1 rounded-md font-medium transition ${
          isOpen ? "text-left" : "text-left"
        } bg-se-blue hover:bg-se-midgray`}
      >
        {isOpen ? "⌛ History" : "⌛"}
      </button>
    </aside>
  );
}
