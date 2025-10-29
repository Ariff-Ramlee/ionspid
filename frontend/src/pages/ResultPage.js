import { useLocation, useNavigate } from "react-router-dom";
import Layout from "../components/Layout";

export default function ResultPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const config = location.state?.config || {};

  // Mock species data
  const speciesData = [
    { name: "E. coli", count: 120, percent: 40 },
    { name: "B. subtilis", count: 90, percent: 30 },
    { name: "S. aureus", count: 60, percent: 20 },
    { name: "Others", count: 30, percent: 10 },
  ];

  return (
    <Layout>
      <div className="max-w-5xl mx-auto p-6 space-y-8">
        {/* Header */}
        <div className="bg-white shadow rounded-lg p-6 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-semibold text-se-blue">Analysis Result</h2>
            <p className="text-gray-500 text-sm">
              Completed on {new Date().toLocaleString()}
            </p>
          </div>
          <span className="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full">
            ✅ Completed
          </span>
        </div>

        {/* Config Summary */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-xl font-semibold text-se-blue mb-3">Configuration Summary</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border rounded">
              <p className="text-gray-500 text-sm">Mode</p>
              <p className="font-medium">{config.mode || "N/A"}</p>
            </div>
            <div className="p-4 border rounded">
              <p className="text-gray-500 text-sm">Filter</p>
              <p className="font-medium">{config.filter || "N/A"}</p>
            </div>
            <div className="p-4 border rounded">
              <p className="text-gray-500 text-sm">Trim Range</p>
              <p className="font-medium">
                {config.trimMin && config.trimMax
                  ? `${config.trimMin} - ${config.trimMax}`
                  : "N/A"}
              </p>
            </div>
          </div>
        </div>

        {/* Species Distribution */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-xl font-semibold text-se-blue mb-3">Species Distribution</h3>
          <table className="w-full border-collapse border text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="border px-4 py-2 text-left">Species</th>
                <th className="border px-4 py-2 text-center">Count</th>
                <th className="border px-4 py-2 text-center">Percentage</th>
              </tr>
            </thead>
            <tbody>
              {speciesData.map((s) => (
                <tr key={s.name}>
                  <td className="border px-4 py-2">{s.name}</td>
                  <td className="border px-4 py-2 text-center">{s.count}</td>
                  <td className="border px-4 py-2 text-center">{s.percent}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Actions */}
        <div className="flex justify-between">
          <button
            onClick={() => navigate("/")}
            className="bg-gray-300 hover:bg-gray-400 text-black px-6 py-2 rounded"
          >
            Back to Home
          </button>
          <button
            onClick={() => alert("Download report not implemented yet")}
            className="bg-se-blue hover:bg-se-lime text-white px-6 py-2 rounded"
          >
            Download Report
          </button>
        </div>
      </div>
    </Layout>
  );
}
