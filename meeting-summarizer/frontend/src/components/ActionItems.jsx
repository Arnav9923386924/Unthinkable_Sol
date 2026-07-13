export default function ActionItems({ items }) {
  if (!items || items.length === 0) {
    return (
      <div className="empty-state">
        <p>No action items identified in this meeting.</p>
      </div>
    );
  }

  const priorityLabel = (p) => {
    const val = (p || "medium").toLowerCase();
    if (val === "high") return "🔴 High";
    if (val === "low") return "🟢 Low";
    return "🟡 Medium";
  };

  return (
    <div className="action-items-table-wrapper">
      <table className="action-items-table">
        <thead>
          <tr>
            <th>Task</th>
            <th>Owner</th>
            <th>Deadline</th>
            <th>Priority</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={index}>
              <td className="task-cell">{item.task}</td>
              <td>
                <span className={`owner-badge ${item.owner === "Unassigned" ? "unassigned" : ""}`}>
                  {item.owner}
                </span>
              </td>
              <td>
                <span className={`deadline-badge ${item.deadline === "Not specified" ? "no-deadline" : ""}`}>
                  {item.deadline}
                </span>
              </td>
              <td>
                <span className={`priority-badge priority-${(item.priority || "medium").toLowerCase()}`}>
                  {priorityLabel(item.priority)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
