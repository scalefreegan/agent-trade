export function AdvisorIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M12 2C8.13 2 5 5.13 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.87-3.13-7-7-7zm2 13h-4v-1h4v1zm.5-3.42l-.5.35V13h-4v-1.07l-.5-.35A4.987 4.987 0 017 9c0-2.76 2.24-5 5-5s5 2.24 5 5a4.987 4.987 0 01-2.5 4.58z"
        fill="currentColor"
      />
      <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1z" fill="currentColor" />
    </svg>
  );
}
