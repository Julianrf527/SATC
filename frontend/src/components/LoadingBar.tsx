export default function LoadingBar() {
  return (
    <div className="relative w-full h-1.5 bg-base-300 rounded-full overflow-hidden shadow-inner">
      <div className="absolute h-full w-1/3 bg-success rounded-full animate-loading-bar" />
      <style>
        {`
          @keyframes loading-bar {
            0% {
              left: -33.333%;
            }
            50% {
              left: 50%;
            }
            100% {
              left: 100%;
            }
          }
          .animate-loading-bar {
            animation: loading-bar 1.5s ease-in-out infinite;
          }
        `}
      </style>
    </div>
  );
}
