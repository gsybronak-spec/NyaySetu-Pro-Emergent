import React from 'react';

export default function StatusBadge({ status }: { status: string }) {
  const norm = status.toLowerCase();
  let colorClass = '';
  if (norm === 'published') colorClass = 'badge-published';
  else if (norm === 'draft') colorClass = 'badge-draft';
  else if (norm === 'archived') colorClass = 'badge-archived';
  else if (norm === 'seed') colorClass = 'badge-seed';

  return (
    <span className={`badge ${colorClass}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
