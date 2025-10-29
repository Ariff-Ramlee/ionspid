import React, { useState } from "react";

const pipelineSteps = [
  { id: "basecall", name: "Basecall" },
  { id: "demux", name: "Demultiplex" },
  { id: "filter", name: "Filter" },
  { id: "trim", name: "Trim" },
  { id: "chimera", name: "Chimera Detection" },
  { id: "cluster", name: "Sequence Clustering" },
  { id: "consensus", name: "Consensus Generation" }
];

// 🧩 Default parameters for each stage
const defaultParams = {
  basecall: { model: "", device: "cuda:0", threads: 4 },
  demux: { barcode_kit: "", min_score: 60 },
  filter: { min_length: 0, min_quality: 20 },
  trim: { quality_threshold: 20, min_length: 100 },
  chimera: { method: "uchime_ref", min_score: 0.5 },
  cluster: { method: "vsearch", similarity_threshold: 0.97 },
  consensus: { tool: "medaka", iterations: 3 }
};

const PipelineStepCard = ({ step, data, onParamChange, onRun }) => {
  const { status, params } = data;
  const disabled = status === "locked";
  const running = status === "in_progress";

  return (
    <div
      className={`border rounded-lg p-4 shadow-sm ${
        running ? "bg-blue-50 border-blue-300" : "bg-white"
      }`}
    >
      <h3 className="text-lg font-semibold mb-2">{step.name}</h3>
      <p className="text-sm text-gray-600 mb-3 capitalize">
        {status === "locked" && "Locked 🔒"}
        {status === "pending" && "Pending ⏳"}
        {status === "in_progress" && "In Progress ⚙️"}
        {status === "completed" && "Completed ✅"}
      </p>

      {/* Parameter Form (only visible if step unlocked or running) */}
      {status !== "locked" && (
        <div className="grid grid-cols-2 gap-3 mb-3">
          {Object.keys(params).map((key) => (
            <div key={key} className="flex flex-col">
              <label className="text-sm text-gray-600">{key}</label>
              <input
                type="text"
                value={params[key]}
                onChange={(e) => onParamChange(step.id, key, e.target.value)}
                disabled={running}
                className="border rounded-md p-1 text-sm"
              />
            </div>
          ))}
        </div>
      )}

      {/* Action Button */}
      {status === "locked" ? (
        <button
          disabled
          className="bg-gray-200 text-gray-600 px-3 py-1 rounded-md cursor-not-allowed"
        >
          Locked
        </button>
      ) : status === "completed" ? (
        <button
          disabled
          className="bg-green-500 text-white px-3 py-1 rounded-md cursor-not-allowed"
        >
          Done
        </button>
      ) : (
        <button
          onClick={() => onRun(step.id)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded-md"
        >
          Run Step
        </button>
      )}
    </div>
  );
};

const AnalysisPipeline = () => {
  const [steps, setSteps] = useState(() =>
    pipelineSteps.reduce((acc, step, i) => {
      acc[step.id] = {
        status: i === 0 ? "in_progress" : "locked", // first step active
        params: { ...defaultParams[step.id] }
      };
      return acc;
    }, {})
  );

  const handleParamChange = (stepId, key, value) => {
    setSteps((prev) => ({
      ...prev,
      [stepId]: {
        ...prev[stepId],
        params: { ...prev[stepId].params, [key]: value }
      }
    }));
  };

  const handleRunStep = (stepId) => {
    // Mark step complete and unlock next
    const currentIndex = pipelineSteps.findIndex((s) => s.id === stepId);
    const nextStep = pipelineSteps[currentIndex + 1];

    setSteps((prev) => ({
      ...prev,
      [stepId]: { ...prev[stepId], status: "completed" },
      ...(nextStep && {
        [nextStep.id]: { ...prev[nextStep.id], status: "in_progress" }
      })
    }));
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {pipelineSteps.map((step) => (
        <PipelineStepCard
          key={step.id}
          step={step}
          data={steps[step.id]}
          onParamChange={handleParamChange}
          onRun={handleRunStep}
        />
      ))}
    </div>
  );
};

export default AnalysisPipeline;
