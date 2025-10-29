import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import API from "../api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from "recharts";

export default function HistoryPage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [filterPlace, setFilterPlace] = useState("");
  const [filterWeather, setFilterWeather] = useState("");
  const [filterDate, setFilterDate] = useState("");
  const [filterUser, setFilterUser] = useState("");
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await API.get("/pipelines/all-jobs");
        setJobs(res.data.jobs || []);
      } catch (err) {
        console.error("Failed to fetch jobs:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchJobs();
  }, []);

  // ✅ Apply filters using file_timestamp
  const filteredJobs = jobs.filter((job) => {
    const jobDate = new Date(job.file_timestamp || job.timestamp_job)
      .toISOString()
      .slice(0, 10); // yyyy-mm-dd
    return (
      (filterPlace ? job.file_place === filterPlace : true) &&
      (filterWeather ? job.file_weather === filterWeather : true) &&
      (filterDate ? jobDate === filterDate : true)&&
      (filterUser ? job.full_name === filterUser : true) &&
      (filterDate ? jobDate === filterDate : true)
    );
  });


  // ✅ Chart data
  const jobsByWeather = Object.values(
    filteredJobs.reduce((acc, job) => {
      acc[job.file_weather] = acc[job.file_weather] || { name: job.file_weather, value: 0 };
      acc[job.file_weather].value += 1;
      return acc;
    }, {})
  );

  const jobsByPlace = Object.values(
    filteredJobs.reduce((acc, job) => {
      acc[job.file_place] = acc[job.file_place] || { name: job.file_place, count: 0 };
      acc[job.file_place].count += 1;
      return acc;
    }, {})
  );

  const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#ff7f50", "#00c49f"];

  return (
    <Layout>
      <div className="max-w-6xl mx-auto p-6 space-y-8">
        <h2 className="text-2xl font-semibold text-se-blue">Job History Dashboard</h2>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <select
            value={filterPlace}
            onChange={(e) => setFilterPlace(e.target.value)}
            className="border rounded px-3 py-2"
          >
            <option value="">All Places</option>
            {[...new Set(jobs.map((j) => j.file_place))].map((place) => (
              <option key={place} value={place}>{place}</option>
            ))}
          </select>

          <select
            value={filterWeather}
            onChange={(e) => setFilterWeather(e.target.value)}
            className="border rounded px-3 py-2"
          >
            <option value="">All Weather</option>
            {[...new Set(jobs.map((j) => j.file_weather))].map((weather) => (
              <option key={weather} value={weather}>{weather}</option>
            ))}
          </select>

          <input
            type="date"
            value={filterDate}
            onChange={(e) => setFilterDate(e.target.value)}
            className="border rounded px-3 py-2"
          />
        </div>

        {loading ? (
          <p>Loading jobs...</p>
        ) : filteredJobs.length === 0 ? (
          <p className="text-gray-600">No jobs match filters.</p>
        ) : (
          <>
            {/* Charts Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Bar Chart (Jobs by Place) */}
              <div className="bg-white shadow rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-2">Jobs by Place</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={jobsByPlace}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#8884d8" onClick={(d) => setFilterPlace(d.name)} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Pie Chart (Jobs by Weather) */}
              <div className="bg-white shadow rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-2">Jobs by Weather</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={jobsByWeather}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label
                      onClick={(d) => setFilterWeather(d.name)}
                    >
                      {jobsByWeather.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Table */}
            <div className="bg-white shadow rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-2">Job Details</h3>
              <table className="w-full border-collapse border border-gray-300">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="border p-2">Job ID</th>
                    <th className="border p-2">Title</th>
                    <th className="border p-2">File</th>
                    <th className="border p-2">Place</th>
                    <th className="border p-2">Weather</th>
                    <th className="border p-2">User</th>
                    <th className="border p-2">File Date</th>
                    <th className="border p-2">Job Date</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredJobs.map((job) => (
                    <tr key={job.job_id} className="hover:bg-gray-50">
                      <td className="border p-2">{job.job_id}</td>
                      <td className="border p-2">{job.title}</td>
                      <td className="border p-2">{job.file_name}</td>
                      <td className="border p-2">{job.file_place}</td>
                      <td className="border p-2">{job.file_weather}</td>
                      <td className="border p-2">{job.full_name}</td>
                      <td className="border p-2">
                        {job.file_timestamp
                          ? new Date(job.file_timestamp).toLocaleString()
                          : "—"}
                      </td>
                      <td className="border p-2">
                        {job.timestamp_job
                          ? new Date(job.timestamp_job).toLocaleString()
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
