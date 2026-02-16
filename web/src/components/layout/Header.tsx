export function Header() {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Experiments</h2>
        </div>
        <div className="flex items-center space-x-4">
          <div className="h-8 w-8 rounded-full bg-brand-600 flex items-center justify-center text-white font-medium">
            U
          </div>
        </div>
      </div>
    </header>
  );
}
