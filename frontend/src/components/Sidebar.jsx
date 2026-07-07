import TrashIcon from "./TrashIcon";

// Left panel: new-thread trigger, the list of threads (each deletable), and
// the footer controls. Clicking a row opens it; clicking the bin deletes it.
export default function Sidebar({
  sessions,
  activeSessionId,
  onNewThread,
  onOpenThread,
  onDeleteThread,
  onModifyParams,
  onLogout,
}) {
  return (
    <aside id="docs" className="sidebar">
      <button className="new-thread-btn" onClick={onNewThread}>
        + New Strategy Thread
      </button>

      <div className="sidebar-label">Active Threads</div>

      <div className="thread-list">
        {sessions.length === 0 && (
          <div className="thread-empty">No threads yet. Start one above.</div>
        )}

        {sessions.map((s) => (
          <div
            key={s.id}
            className={"thread-row" + (s.id === activeSessionId ? " active" : "")}
            onClick={() => onOpenThread(s.id)}
          >
            <span className="thread-title">📁 {s.title}</span>
            <button
              className="thread-delete"
              title="Delete thread"
              aria-label={`Delete ${s.title}`}
              onClick={(e) => {
                e.stopPropagation(); // don't also open the thread
                onDeleteThread(s.id);
              }}
            >
              <TrashIcon />
            </button>
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <button className="ghost-btn" onClick={onModifyParams}>
          ← Modify Parameters
        </button>
        <button className="ghost-btn logout" onClick={onLogout}>
          Log Out
        </button>
      </div>
    </aside>
  );
}
