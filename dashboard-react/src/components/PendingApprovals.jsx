import { useEffect, useState } from "react";
import { approveCommand, getPendingApprovals, rejectCommand } from "../api.js";

export default function PendingApprovals({ refreshKey }) {
  const [approvals, setApprovals] = useState([]);
  const [actingOn, setActingOn] = useState(null);
  const [error, setError] = useState(null);

  const load = () => {
    getPendingApprovals()
      .then(setApprovals)
      .catch((err) => setError(err.message));
  };

  useEffect(load, [refreshKey]);

  const act = async (approvalId, action) => {
    setActingOn(approvalId);
    try {
      if (action === "approve") await approveCommand(approvalId);
      else await rejectCommand(approvalId);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setActingOn(null);
    }
  };

  if (error) return null; // approvals are a bonus card — don't block the rest of the page on it
  if (approvals.length === 0) return null;

  return (
    <div className="card">
      <p className="card-title">
        Pending approvals
        <span className="updated-at">{approvals.length}</span>
      </p>
      {approvals.map((approval) => (
        <div key={approval.approval_request_id} className="list-row" style={{ flexDirection: "column", alignItems: "stretch", gap: 6 }}>
          <div className="list-row" style={{ padding: 0, border: "none" }}>
            <span className="list-row-label">Command {approval.command_id.slice(0, 8)}</span>
            <span className="list-row-value">{approval.risk_level}</span>
          </div>
          <div className="approval-actions">
            <button
              className="secondary-button approve"
              disabled={actingOn === approval.approval_request_id}
              onClick={() => act(approval.approval_request_id, "approve")}
            >
              Approve
            </button>
            <button
              className="secondary-button reject"
              disabled={actingOn === approval.approval_request_id}
              onClick={() => act(approval.approval_request_id, "reject")}
            >
              Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
