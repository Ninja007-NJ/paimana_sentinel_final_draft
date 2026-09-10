export function SkeletonCard() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <div className="skeleton-line w-32" />
      <div className="skeleton-line w-48 h-7 mt-2.5" />
      <div className="skeleton-line w-24 mt-2" />
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="skeleton-chart" aria-hidden="true">
      <div className="skeleton-line w-40" />
      <div className="skeleton-box mt-4" />
    </div>
  );
}
