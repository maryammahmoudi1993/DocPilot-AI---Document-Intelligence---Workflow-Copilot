import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <main className="min-h-screen bg-[#EEECF6] flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-[#232235] mb-4">404</h1>
        <p className="text-xl text-[#77758A] mb-8">Page not found</p>
        <Link
          to="/"
          className="inline-flex items-center px-6 py-3 bg-[#7257F5] text-white rounded-lg hover:bg-[#6047E8] transition-colors"
        >
          Return to Home
        </Link>
      </div>
    </main>
  );
}
