import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../context/AuthContext";
import { uploadFile } from "../api";
import * as XLSX from "xlsx";
import { useProgress } from "../context/ProgressContext";
import API from "../api";

export default function UploadPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { uploaded, setUploaded } = useProgress();

  const [file, setFile] = useState(null);
  const [place, setPlace] = useState("");
  const [timestamp, setTimestamp] = useState("");
  const [weather, setWeather] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // ✅ New: Excel metadata state
  const [metadataRows, setMetadataRows] = useState([]);
  const [selectedRow, setSelectedRow] = useState(null);

  // Drag & drop handlers
  const [isDragging, setIsDragging] = useState(false);
  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
      e.dataTransfer.clearData();
    }
  };

  // ✅ Parse Excel with multiple rows
  const handleMetaFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      const data = new Uint8Array(evt.target.result);
      const workbook = XLSX.read(data, { type: "array" });
      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(worksheet);
      setMetadataRows(jsonData);
    };
    reader.readAsArrayBuffer(file);
  };

  // ✅ Select a row and auto-fill metadata
  const handleSelectRow = (index) => {
    const row = metadataRows[index];
    setSelectedRow(row);
    setPlace(row.place || row.Place || "");
    setWeather(row.weather || row.Weather || "");
    if (row.timestamp || row.Timestamp) {
      const raw = row.timestamp || row.Timestamp;
      try {
        const parsed = new Date(raw);
        setTimestamp(parsed.toISOString().slice(0, 16));
      } catch {
        setTimestamp(raw);
      }
    }
  };

  // ✅ Upload POD5 file
  const handleUpload = async () => {
    if (!file) return setError("Please select a .pod5 file first");
    if (!user) return setError("You must be logged in to upload");

    setError("");
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("place", place);
    formData.append("timestamp", timestamp || new Date().toISOString());
    formData.append("weather", weather);

    // include selected metadata row (optional JSON string)
    if (selectedRow) {
      formData.append("metadata", JSON.stringify(selectedRow));
    }

    try {
      const res = await uploadFile(formData);
      const fileId = res.data.file.file_id;

      const jobRes = await API.post("/pipelines/create-job", { file_id: fileId });
      const jobId = jobRes.data.job.job_id;

      setUploaded(true);
      navigate("/analysis", {
        state: {
          fileId,
          fileName: res.data.file.file_name,
          jobId,
        },
      });
    } catch (err) {
      setError(err.response?.data?.error || "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout uploaded={uploaded}>
      <div className="max-w-5xl mx-auto bg-white p-8 rounded-lg shadow space-y-6">
        <h2 className="text-2xl font-semibold mb-4 text-se-blue">Upload Sample</h2>

        {/* 🧭 Drag & Drop POD5 */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-lg cursor-pointer 
            ${isDragging ? "border-se-lime bg-green-50" : "border-se-blue hover:bg-gray-50"}`}
        >
          {file ? (
            <span>
              Selected: <b>{file.name}</b> ({(file.size / 1024).toFixed(1)} KB)
            </span>
          ) : (
            <span className="text-gray-500">
              Drag & drop .pod5 file here or click to select
            </span>
          )}
          <input
            type="file"
            accept=".pod5"
            onChange={(e) => setFile(e.target.files[0])}
            className="hidden"
            id="fileInput"
          />
          <label
            htmlFor="fileInput"
            className="mt-2 text-se-blue underline cursor-pointer"
          >
            Browse
          </label>
        </div>

        {/* 🧩 Upload Excel metadata */}
        <div>
          <p className="mb-1 text-sm text-gray-500">
            Upload metadata file (.xls/.xlsx)
          </p>
          <input type="file" accept=".xls,.xlsx" onChange={handleMetaFile} />
        </div>

        {/* 🧩 Show parsed rows */}
        {metadataRows.length > 0 && (
          <div className="overflow-x-auto border rounded-md">
            <table className="min-w-full text-sm text-left border-collapse">
              <thead className="bg-gray-100 border-b">
                <tr>
                  {Object.keys(metadataRows[0]).map((header) => (
                    <th key={header} className="px-4 py-2 font-semibold border-b">
                      {header}
                    </th>
                  ))}
                  <th className="px-4 py-2 font-semibold border-b text-center">Action</th>
                </tr>
              </thead>
              <tbody>
                {metadataRows.map((row, index) => (
                  <tr
                    key={index}
                    className={`hover:bg-blue-50 ${
                      selectedRow === row ? "bg-blue-100" : ""
                    }`}
                  >
                    {Object.values(row).map((val, i) => (
                      <td key={i} className="px-4 py-2 border-b">
                        {val?.toString() || "-"}
                      </td>
                    ))}
                    <td className="px-4 py-2 text-center border-b">
                      <button
                        onClick={() => handleSelectRow(index)}
                        className={`px-3 py-1 rounded-md text-white ${
                          selectedRow === row
                            ? "bg-green-600"
                            : "bg-blue-600 hover:bg-blue-700"
                        }`}
                      >
                        {selectedRow === row ? "Selected" : "Select"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 🧩 Selected metadata summary */}
        {selectedRow && (
          <div className="mt-6 p-4 bg-gray-50 border rounded-md">
            <h2 className="font-semibold mb-2">Selected Metadata</h2>
            {Object.entries(selectedRow).map(([key, value]) => (
              <p key={key} className="text-sm">
                <strong>{key}:</strong> {value?.toString() || "-"}
              </p>
            ))}
          </div>
        )}

        {/* 🧩 Manual input fallback */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Sample Metadata (Editable)</h3>
          <input
            type="text"
            placeholder="Place"
            value={place}
            onChange={(e) => setPlace(e.target.value)}
            className="w-full border rounded px-4 py-2"
          />
          <input
            type="datetime-local"
            value={timestamp}
            onChange={(e) => setTimestamp(e.target.value)}
            className="w-full border rounded px-4 py-2"
          />
          <input
            type="text"
            placeholder="Weather"
            value={weather}
            onChange={(e) => setWeather(e.target.value)}
            className="w-full border rounded px-4 py-2"
          />
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button
          onClick={handleUpload}
          disabled={loading}
          className="w-full bg-se-lime hover:bg-se-blue text-white font-semibold py-3 rounded-md transition"
        >
          {loading ? "Uploading..." : "Proceed to Analysis"}
        </button>
      </div>
    </Layout>
  );
}
