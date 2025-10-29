import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom"; // ✅ redirect after completion
import Layout from "../components/Layout";

const pipelineSteps = [
  { id: "basecall", name: "Basecall" },
  { id: "demux", name: "Demultiplex" },
  { id: "filter", name: "Filter" },
  { id: "trim", name: "Trim" },
  { id: "chimera", name: "Chimera Detection" },
  { id: "cluster", name: "Sequence Clustering" },
  { id: "consensus", name: "Consensus Generation" },
  { id: "blast", name: "BLAST Search" },
  { id: "taxonomy", name: "Taxonomy Assignment" },
  { id: "polish_consensus", name: "Consensus Polishing" },
];

const defaultParams = {
  basecall: { model: "", device: "cuda:0", threads: 4 },
  demux: { barcode_kit: "", min_score: 60 },
  filter: { min_length: 0, min_quality: 20 },
  trim: { quality_threshold: 20, min_length: 100 },
  chimera: { method: "uchime_ref", min_score: 0.5 },
  cluster: { method: "vsearch", similarity_threshold: 0.97 },
  consensus: { tool: "medaka", iterations: 3 },
  blast: { database: "nt", evalue: 1e-5, max_target_seqs: 10 },
  taxonomy: { method: "lca", min_identity: 70.0, min_coverage: 50.0 },
  polish_consensus: { tool: "medaka", threads: 4, iterations: 3 },
};

const AnalysisPage = () => {
  const navigate = useNavigate();

  const [steps, setSteps] = useState(() =>
    pipelineSteps.reduce((acc, step, i) => {
      acc[step.id] = {
        status: i === 0 ? "in_progress" : "locked",
        params: { ...defaultParams[step.id] },
      };
      return acc;
    }, {})
  );

  // Check if all steps are complete → redirect to Result page
  useEffect(() => {
    const allCompleted = pipelineSteps.every(
      (s) => steps[s.id].status === "completed"
    );
    if (allCompleted) {
      // Small delay for UX smoothness
      setTimeout(() => navigate("/result"), 1000);
    }
  }, [steps, navigate]);

  const handleParamChange = (stepId, key, value) => {
    setSteps((prev) => ({
      ...prev,
      [stepId]: {
        ...prev[stepId],
        params: { ...prev[stepId].params, [key]: value },
      },
    }));
  };

  const handleRunStep = (stepId) => {
    const currentIndex = pipelineSteps.findIndex((s) => s.id === stepId);
    const nextStep = pipelineSteps[currentIndex + 1];

    setSteps((prev) => ({
      ...prev,
      [stepId]: { ...prev[stepId], status: "completed" },
      ...(nextStep && {
        [nextStep.id]: { ...prev[nextStep.id], status: "in_progress" },
      }),
    }));
  };

  return (
    <Layout>
      <div className="p-6 max-w-7xl mx-auto space-y-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">
            iONspID Pipeline Execution
          </h1>
          <p className="text-gray-600 mb-6">
            Configure and execute each pipeline stage sequentially. Each step
            can be customized with its specific parameters before proceeding.
          </p>

          {/* Pipeline Step Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {pipelineSteps.map((step) => {
              const { status, params } = steps[step.id];
              const locked = status === "locked";
              const completed = status === "completed";

              return (
                <div
                  key={step.id}
                  className={`border rounded-lg p-4 shadow-sm transition ${
                    locked
                      ? "bg-gray-50 border-gray-200"
                      : completed
                      ? "bg-green-50 border-green-400"
                      : "bg-white border-blue-200"
                  }`}
                >
                  <h2 className="text-lg font-semibold text-gray-800 mb-2">
                    {step.name}
                  </h2>
                  <p className="text-sm text-gray-600 mb-3">
                    {status === "locked" && "Locked 🔒"}
                    {status === "in_progress" && "Ready ⚙️"}
                    {status === "completed" && "Completed ✅"}
                  </p>

                  {/* Parameter Inputs */}
                  {status !== "locked" && (
                    <div className="grid grid-cols-2 gap-3 mb-4">
                      {Object.keys(params).map((key) => (
                        <div key={key} className="flex flex-col">
                          <label className="text-sm font-medium text-gray-700">
                            {key}
                          </label>
                          <input
                            type="text"
                            value={params[key]}
                            onChange={(e) =>
                              handleParamChange(step.id, key, e.target.value)
                            }
                            disabled={completed}
                            className="border rounded-md p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Step Buttons */}
                  {locked ? (
                    <button
                      disabled
                      className="w-full bg-gray-200 text-gray-500 py-2 rounded-md cursor-not-allowed"
                    >
                      Locked
                    </button>
                  ) : completed ? (
                    <button
                      disabled
                      className="w-full bg-green-500 text-white py-2 rounded-md cursor-not-allowed"
                    >
                      Done
                    </button>
                  ) : (
                    <button
                      onClick={() => handleRunStep(step.id)}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-md font-medium"
                    >
                      Run Step
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default AnalysisPage;
