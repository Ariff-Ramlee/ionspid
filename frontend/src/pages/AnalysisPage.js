import React, { useState } from "react";
import Layout from "../components/Layout";

/* =========================================================
   STEP DEFINITIONS
   ========================================================= */
const pipelineSteps = [
  { id: "basecall", name: "Basecalling", description: "Convert raw POD5 data into FASTQ files using Dorado model." },
  { id: "qc1", name: "Quality Assessment 1", description: "Assess sequencing run quality and generate a summary report." },
  { id: "demux", name: "Demultiplexing", description: "Split reads based on barcode kit information." },
  { id: "qc2", name: "Quality Assessment 2", description: "Evaluate read-level sequencing quality after demultiplexing." },
  { id: "filter", name: "Filtering", description: "Filter reads based on quality, length, and other metrics." },
  { id: "trim", name: "Trimming", description: "Trim low-quality bases or adapters from reads." },
  { id: "chimera", name: "Chimera Removal", description: "Detect and remove chimeric sequences from reads." },
  { id: "cluster", name: "Clustering", description: "Cluster sequences based on similarity and algorithm type." },
  { id: "consensus", name: "Consensus Generation", description: "Generate consensus sequences from clustered reads." },
  { id: "taxonomy", name: "Taxonomy Assignment", description: "Identify species using taxonomy database." },
  { id: "report", name: "Reporting & Visualization", description: "Generate BLAST-based HTML reports and visualizations." },

];

/* =========================================================
   CLI ARGUMENT SCHEMAS
   ========================================================= */

// ---- basecall run ----
const basecallArgs = {
  input_path: { type: "text", label: "Input Path (required)", required: true },
  output_dir: { type: "text", label: "Output Directory (required)", required: true },
  model: { type: "text", label: "Model (optional)", required: false },
  device: { type: "text", label: "Device (cpu, cuda:0, auto)", default: "auto" },
  batch_size: { type: "number", label: "Batch Size", default: 32 },
  recursive: { type: "boolean", label: "Recursive Search" },
  threads: { type: "number", label: "CPU Threads", default: 4 },
  barcode_kit: { type: "text", label: "Barcode Kit" },
  sample_name: { type: "text", label: "Sample Name" },
  emit_fastq: { type: "boolean", label: "Emit FASTQ Files", default: true },
  modified_bases: { type: "boolean", label: "Detect Modified Bases" },
  max_reads: { type: "number", label: "Max Reads" },
  estimate: { type: "boolean", label: "Estimate Time Only" },
};

// ---- qc run (QA1) ----
const qc1Args = {
  summary: { type: "text", label: "Sequencing Summary File (required)", required: true },
  output_dir: { type: "text", label: "Output Directory" },
  tool: { type: "text", label: "Tool (native, pycoQC, etc.)", default: "native" },
  report_format: { type: "text", label: "Report Format (html, json, both)", default: "html" },
  title: { type: "text", label: "Report Title" },
  no_plots: { type: "boolean", label: "Disable Plots" },
};

// ---- demux run ----
const demuxArgs = {
  input_file: { type: "text", label: "FASTQ File to Demultiplex (required)", required: true },
  output_dir: { type: "text", label: "Output Directory (required)", required: true },
  kit: { type: "text", label: "Barcode Kit Name (required)", required: true },
  min_score: { type: "number", label: "Minimum Barcode Score", default: 60 },
  require_both_ends: { type: "boolean", label: "Require Both Ends" },
  trim: { type: "boolean", label: "Trim Barcodes from Reads" },
  threads: { type: "number", label: "CPU Threads", default: 4 },
};

// ---- qc reads (QA2) ----
const qc2Args = {
  fastq: { type: "text", label: "FASTQ File (required)", required: true },
  output_dir: { type: "text", label: "Output Directory" },
  tool: { type: "text", label: "QC Tool (FastQC, NanoPlot, etc.)", default: "FastQC" },
  report_format: { type: "text", label: "Report Format (html, json, both)", default: "html" },
  title: { type: "text", label: "Report Title" },
  no_plots: { type: "boolean", label: "Disable Plots" },
  sample_size: { type: "number", label: "Number of Reads to Sample", default: 1000 },
  threads: { type: "number", label: "CPU Threads", default: 4 },
};

// ---- filter run ----
const filterArgs = {
  input: { type: "text", label: "Input FASTQ/FASTA File (required)", required: true },
  output: { type: "text", label: "Output File (required)", required: true },
  failed: { type: "text", label: "Failed Reads Output File" },
  report: { type: "text", label: "HTML Report File" },
  format: { type: "text", label: "Input Format (fastq, fasta)", default: "fastq" },
  min_length: { type: "number", label: "Minimum Sequence Length" },
  max_length: { type: "number", label: "Maximum Sequence Length" },
  min_quality: { type: "number", label: "Minimum Mean Quality Score" },
  min_base_quality: { type: "number", label: "Minimum Base Quality" },
  window_size: { type: "number", label: "Sliding Window Size" },
  window_quality: { type: "number", label: "Minimum Mean Window Quality" },
  threads: { type: "number", label: "CPU Threads", default: 4 },
};

// ---- trim quality ----
const trimArgs = {
  input: { type: "text", label: "Input FASTQ File (required)", required: true },
  output: { type: "text", label: "Output FASTQ File (required)", required: true },
  discarded: { type: "text", label: "Discarded Reads File" },
  report: { type: "text", label: "HTML Report File" },
  format: { type: "text", label: "File Format (fastq)", default: "fastq" },
  threshold: { type: "number", label: "Quality Score Threshold" },
  algorithm: { type: "text", label: "Trimming Algorithm" },
  window_size: { type: "number", label: "Window Size" },
  min_length: { type: "number", label: "Minimum Sequence Length to Keep" },
  trim_5_end: { type: "boolean", label: "Trim 5' End" },
  trim_3_end: { type: "boolean", label: "Trim 3' End" },
  discard_untrimmed: { type: "boolean", label: "Discard Untrimmed Reads" },
  parallel: { type: "boolean", label: "Use Parallel Processing" },
  threads: { type: "number", label: "CPU Threads", default: 4 },
  chunk_size: { type: "number", label: "Chunk Size for Parallel Processing" },
};

// ---- chimera detect ----
const chimeraArgs = {
  input: { type: "text", label: "Input FASTA/FASTQ File (required)", required: true },
  output: { type: "text", label: "Output Non-Chimeric File (required)", required: true },
  chimeric_output: { type: "text", label: "Output Chimeric File" },
  method: { type: "text", label: "Detection Method (reference, denovo, both)", default: "both" },
  ref_db: { type: "text", label: "Reference Database" },
  score_threshold: { type: "number", label: "Score Threshold", default: 0.5 },
  report: { type: "text", label: "Report CSV Path" },
  vsearch_path: { type: "text", label: "Path to VSEARCH Executable" },
  threads: { type: "number", label: "CPU Threads", default: 4 },
};

// ---- cluster run ----
const clusterArgs = {
  input: { type: "text", label: "Input FASTA File (required)", required: true },
  output: { type: "text", label: "Output Directory (required)", required: true },
  algorithm: { type: "text", label: "Algorithm (vsearch, isonclust)", default: "vsearch" },
  identity: { type: "number", label: "Sequence Identity Threshold", default: 0.97 },
  min_cluster_size: { type: "number", label: "Minimum Cluster Size" },
  extra_params: { type: "text", label: "Extra Parameters (JSON)" },
  plot: { type: "boolean", label: "Generate Clustering Plots", default: false },
};

// ---- polish-consensus run ----
const consensusArgs = {
  consensus: { type: "text", label: "Consensus FASTA/FASTQ File (required)", required: true },
  reads: { type: "text", label: "Supporting Reads (required)", required: true },
  output: { type: "text", label: "Output Polished File (required)", required: true },
  polisher: { type: "text", label: "Polisher (medaka, racon, nanopolish)", default: "medaka" },
  rounds: { type: "number", label: "Number of Rounds", default: 1 },
  report: { type: "text", label: "Polishing Report Path" },
  threads: { type: "number", label: "CPU Threads", default: 4 },
  memory: { type: "number", label: "Memory Limit (GB)" },
  medaka_model: { type: "text", label: "Medaka Model Name" },
  racon_window_length: { type: "number", label: "Racon Window Length" },
  nanopolish_min_freq: { type: "number", label: "Nanopolish Min Frequency" },
  fast5_dir: { type: "text", label: "FAST5 Directory (for Nanopolish)" },
  chunk_size: { type: "number", label: "Chunk Size" },
  extra_args: { type: "text", label: "Extra Arguments (JSON)" },
  force: { type: "boolean", label: "Force Overwrite", default: false },
  keep_intermediate: { type: "boolean", label: "Keep Intermediate Files" },
};

// ---- taxonomy assign ----
const taxonomyArgs = {
  input_file: { type: "text", label: "Input FASTA File (required)", required: true },
  output_file: { type: "text", label: "Output Assignments File (required)", required: true },
  database: { type: "text", label: "BLAST Database Name or Path" },
  taxonomy_map: { type: "text", label: "Taxonomy Mapping CSV" },
  method: { type: "text", label: "Assignment Method (best_hit, lca)", default: "best_hit" },
  min_identity: { type: "number", label: "Minimum Percent Identity", default: 70 },
  min_coverage: { type: "number", label: "Minimum Query Coverage", default: 50 },
  max_evalue: { type: "number", label: "Maximum E-value Threshold" },
  min_bit_score: { type: "number", label: "Minimum Bit Score" },
  threads: { type: "number", label: "CPU Threads", default: 4 },
  top_hits: { type: "number", label: "Top Hits for Consensus", default: 1 },
  consensus_fraction: { type: "number", label: "Consensus Fraction", default: 0.5 },
  export_format: { type: "text", label: "Export Format (csv, json)", default: "csv" },
  include_confidence: { type: "boolean", label: "Include Confidence Scores", default: true },
};

// ---- blast report ----
const reportArgs = {
  assignments: { type: "text", label: "Assignments CSV File (required)", required: true },
  output: { type: "text", label: "Output Report File (required)", required: true },
  interactive: { type: "boolean", label: "Generate Interactive HTML Report", default: true },
  include_tree: { type: "boolean", label: "Include Taxonomic Tree Visualization", default: true },
  plot_format: { type: "text", label: "Plot Format (png, svg, pdf)", default: "html" },
  show_statistics: { type: "boolean", label: "Include Summary Statistics", default: true },
  group_by: { type: "text", label: "Group Results By (taxonomy, identity, evalue)", default: "taxonomy" },
  top_n: { type: "number", label: "Top N Results", default: 10 },
};

/* =========================================================
   ARG MAP
   ========================================================= */
const argMap = {
  basecall: basecallArgs,
  qc1: qc1Args,
  demux: demuxArgs,
  qc2: qc2Args,
  filter: filterArgs,
  trim: trimArgs,
  chimera: chimeraArgs,
  cluster: clusterArgs,
  consensus: consensusArgs,
  taxonomy: taxonomyArgs,
  report: reportArgs,
};

/* =========================================================
   MAIN COMPONENT
   ========================================================= */
const AnalysisPage = () => {
  const [activeStep, setActiveStep] = useState(null);
  const [params, setParams] = useState({});
  const [statusMap, setStatusMap] = useState(
    pipelineSteps.reduce((acc, step, i) => {
      acc[step.id] = i === 0 ? "unlocked" : "locked";
      return acc;
    }, {})
  );
  const [message, setMessage] = useState("");

  // Handle field changes
  const handleParamChange = (key, value) =>
    setParams((prev) => ({ ...prev, [key]: value }));

  const handleToggle = (key) =>
    setParams((prev) => ({ ...prev, [key]: !prev[key] }));

  // Run CLI step and unlock next
  const handleRunStep = async (stepId) => {
    setMessage(`Running ${stepId}...`);
    updateStatus(stepId, "running");

    try {
      // Map custom CLI command names
      const commandMap = {
        qc1: "qc run",
        qc2: "qc reads",
        trim: "trim quality",
        chimera: "chimera detect",
        consensus: "polish-consensus run",
        taxonomy: "taxonomy assign",
        report: "blast report",
      };

      const token = localStorage.getItem("token");

      const response = await fetch("/pipelines/run-step", {
        method: "POST",
        headers: { "Content-Type": "application/json" ,
                   "Authorization": 'Bearer ${token}',
        },
        body: JSON.stringify({
          command: commandMap[stepId] || `${stepId} run`,
          args: params,
        }),
      });

      if (!response.ok) throw new Error("Execution failed");
      await response.json();

      updateStatus(stepId, "completed");
      setMessage(`✅ ${stepId} completed successfully!`);

      const currentIndex = pipelineSteps.findIndex((s) => s.id === stepId);
      const nextStep = pipelineSteps[currentIndex + 1];

      if (nextStep) updateStatus(nextStep.id, "unlocked");
      else setMessage("🎉 All pipeline steps completed successfully!");
    } catch (err) {
      updateStatus(stepId, "error");
      setMessage(`❌ Error running ${stepId}: ${err.message}`);
    }
  };

  const updateStatus = (stepId, newStatus) => {
    setStatusMap((prev) => ({ ...prev, [stepId]: newStatus }));
  };

  /* =========================================================
     UI
     ========================================================= */
  return (
    <Layout>
      <div className="flex flex-col md:flex-row p-6 gap-6 max-w-7xl mx-auto">
        {/* LEFT SIDEBAR */}
        <div className="md:w-1/3 space-y-4">
          {pipelineSteps.map((step) => {
            const status = statusMap[step.id];
            const locked = status === "locked";
            const completed = status === "completed";
            const running = status === "running";

            return (
              <div
                key={step.id}
                onClick={() => {
                  if (!locked) {
                    setActiveStep(step.id);
                    setParams({});
                    setMessage("");
                  }
                }}
                className={`cursor-pointer border rounded-lg p-4 shadow-sm transition ${
                  locked
                    ? "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
                    : activeStep === step.id
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white hover:bg-gray-50 border-gray-200"
                }`}
              >
                <h2 className="font-semibold text-lg flex justify-between items-center">
                  {step.name}
                  {completed && <span className="text-green-400">✅</span>}
                  {running && <span className="animate-spin">⚙️</span>}
                </h2>
                <p className="text-sm mt-1 opacity-80">{step.description}</p>
              </div>
            );
          })}
        </div>

        {/* RIGHT FORM PANEL */}
        <div className="flex-1 bg-white rounded-lg shadow p-6">
          {activeStep ? (
            <>
              <h2 className="text-2xl font-bold mb-4 text-gray-800">
                ⚙️ {pipelineSteps.find((s) => s.id === activeStep)?.name}
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(argMap[activeStep]).map(([key, info]) => {
                  const value = params[key] ?? info.default ?? "";
                  return (
                    <div key={key} className="flex flex-col">
                      <label className="text-sm font-medium text-gray-700 mb-1">
                        {info.label}
                        {info.required && <span className="text-red-500 ml-1">*</span>}
                      </label>
                      {info.type === "boolean" ? (
                        <button
                          onClick={() => handleToggle(key)}
                          className={`py-2 rounded-md border ${
                            value
                              ? "bg-blue-600 text-white border-blue-600"
                              : "bg-gray-100 text-gray-700 border-gray-300"
                          }`}
                        >
                          {value ? "Enabled ✅" : "Disabled ❌"}
                        </button>
                      ) : (
                        <input
                          type={info.type}
                          value={value}
                          placeholder={`Enter ${key}`}
                          onChange={(e) => handleParamChange(key, e.target.value)}
                          className="border rounded-md p-2 text-sm focus:ring-2 focus:ring-blue-500"
                        />
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="mt-6">
                <button
                  onClick={() => handleRunStep(activeStep)}
                  disabled={statusMap[activeStep] === "running"}
                  className={`w-full py-3 rounded-md font-medium ${
                    statusMap[activeStep] === "running"
                      ? "bg-gray-400 cursor-not-allowed"
                      : "bg-blue-600 hover:bg-blue-700 text-white"
                  }`}
                >
                  {statusMap[activeStep] === "running" ? "Running..." : `Run ${activeStep}`}
                </button>
              </div>

              {message && (
                <div
                  className={`mt-4 text-sm font-medium ${
                    message.includes("Error")
                      ? "text-red-600"
                      : message.includes("completed")
                      ? "text-green-600"
                      : "text-gray-700"
                  }`}
                >
                  {message}
                </div>
              )}
            </>
          ) : (
            <div className="text-gray-500 italic">
              Select a step from the left to configure its parameters.
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default AnalysisPage;
