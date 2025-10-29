import HeroCarousel from "../components/HeroCarousel";
import Layout from "../components/Layout";

export default function Home() {
  return (
    <Layout>
      {/* Hero Section */}
      <div className="w-full relative">
        <HeroCarousel
          images={["/Sample2.jpg"]}
          className="h-56 md:h-80 object-cover rounded-lg shadow"
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <h1 className="text-2xl md:text-4xl font-bold text-white drop-shadow-lg">
            Bioinformatics Made Simple
          </h1>
        </div>
      </div>

      {/* About & Person in Charge */}
      <div className="max-w-6xl mx-auto px-6 py-12 grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* About */}
        <div className="bg-white p-8 rounded-lg shadow h-full flex flex-col">
          <h2 className="text-2xl font-bold mb-4 text-se-blue">About the Website</h2>
          <p className="text-lg leading-relaxed text-gray-700">
            This platform provides bioinformatics pipeline tools, data upload, and
            result visualization for sequencing projects. Users can easily manage
            workflows and generate detailed reports with intuitive interfaces.
          </p>
        </div>

        {/* Person in Charge */}
        <div className="bg-se-blue p-8 rounded-lg shadow h-full flex flex-col items-center text-white">
          <img
            src="/photo.jpeg"
            alt="Person in Charge"
            className="w-28 h-28 rounded-full object-cover border-4 border-white mb-4"
          />
          <h2 className="text-xl font-semibold">Dr. John Doe</h2>
          <p className="text-lg">Lead Researcher</p>
          <p className="mt-2 text-sm text-se-midgray text-center">
            Responsible for managing the analysis pipeline and ensuring data integrity.
          </p>
        </div>
      </div>
    </Layout>
  );
}
