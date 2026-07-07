// A classic red trash can. The lid is a separate <g> so it can lift/tilt on
// hover (the hover rule lives in index.css, keyed off .thread-row:hover).
export default function TrashIcon() {
  return (
    <svg className="trash" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      {/* lid (handle + bar) — animated */}
      <g className="trash-lid">
        <rect x="9" y="2.5" width="6" height="2" rx="1" />
        <rect x="4" y="5" width="16" height="2.2" rx="1.1" />
      </g>
      {/* can body */}
      <path
        className="trash-can"
        d="M6 8.2h12l-1.05 12.1a1.6 1.6 0 0 1-1.6 1.45H8.65a1.6 1.6 0 0 1-1.6-1.45L6 8.2Z"
      />
      {/* ridges */}
      <line className="trash-streak" x1="9.7" y1="11" x2="10" y2="19" />
      <line className="trash-streak" x1="12" y1="11" x2="12" y2="19" />
      <line className="trash-streak" x1="14.3" y1="11" x2="14" y2="19" />
    </svg>
  );
}
