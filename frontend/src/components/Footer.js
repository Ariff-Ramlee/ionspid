// src/components/Footer.js
export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-se-midgray text-black py-4">
      <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center text-sm space-y-2 md:space-y-0">
        <p>© {year} iONspID — All Rights Reserved.</p>

        <div className="flex space-x-4">
          <a
            href="https://github.com/Ariff-Ramlee"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-se-lime transition"
          >
            GitHub
          </a>
          <a
            href="https://sarawakenergy.com"
            className="hover:text-se-lime transition"
          >
            Contact
          </a>
        </div>
      </div>
    </footer>
  );
}
