import { useEffect, useState } from "react";
import { ArrowLeft, KeyRound, Mail, Save, Shield, User } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Profile } from "../api/types";

export function ProfilePage() {
  const location = useLocation();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(
    (location.state as { passwordChanged?: boolean } | null)?.passwordChanged
      ? "Password updated successfully."
      : "",
  );

  const load = async (signal?: AbortSignal) => {
    setLoading(true);
    setLoadError("");
    try {
      const value = await api.getProfile({ signal });
      setProfile(value);
      setName(value.name);
    } catch (error) {
      if (!(error instanceof ApiError && error.code === "cancelled")) {
        setLoadError(error instanceof ApiError ? error.message : "Unable to load your profile.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, []);

  const saveName = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleanName = name.trim().replace(/\s+/g, " ");
    setMessage("");
    if (!cleanName || cleanName.length > 120) {
      setMessage("Enter a name between 1 and 120 characters.");
      return;
    }
    setSaving(true);
    try {
      const updated = await api.updateProfile({ name: cleanName });
      setProfile(updated);
      setName(updated.name);
      setEditing(false);
      setMessage("Profile updated successfully.");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Unable to update your profile.");
    } finally {
      setSaving(false);
    }
  };

  return <div className="profile-container">
    <div className="profile-header">
      <Link to="/dashboard" className="back-link"><ArrowLeft size={16} /> Back to Dashboard</Link>
      <h1>Account Settings</h1>
      <p>Manage your profile, email, and security preferences.</p>
    </div>
    {loading && <p role="status">Loading your profile…</p>}
    {loadError && <div className="alert error" role="alert">{loadError} <button onClick={() => void load()}>Try again</button></div>}
    {message && <div className={message.includes("successfully") ? "alert success" : "alert error"} role="status">{message}</div>}
    {profile && !loading && <div className="profile-grid">
      <div className="profile-card profile-info">
        <h2><User size={18} /> Profile Details</h2>
        <div className="profile-details-content">
          <div className="info-group">
            <label><Mail size={14}/> Email Address</label>
            <div className="info-value">{profile.email}</div>
            <span className="info-help">Your registered AUST email cannot be changed here.</span>
          </div>
          <div className="info-group">
            <label htmlFor="profile-name"><User size={14}/> Name</label>
            {!editing ? <div className="info-value-row">
              <div className="info-value">{profile.name}</div>
              <button className="edit-btn" onClick={() => { setEditing(true); setMessage(""); }}>Edit</button>
            </div> : <form onSubmit={saveName} className="edit-username-form">
              <input id="profile-name" type="text" value={name} maxLength={120}
                onChange={(event) => setName(event.target.value)} autoFocus className="profile-input" />
              <div className="edit-actions">
                <button type="button" className="cancel-btn" onClick={() => { setName(profile.name); setEditing(false); }}>Cancel</button>
                <button type="submit" className="save-btn" disabled={saving}>
                  {saving ? "Saving…" : <><Save size={14}/> Save</>}
                </button>
              </div>
            </form>}
          </div>
        </div>
      </div>
      <div className="profile-card profile-security">
        <h2><Shield size={18} /> Account Security</h2>
        <p className="info-help">Update your password from the protected password page.</p>
        <Link className="reset-btn profile-change-password" to="/profile/change-password">
          <KeyRound size={16}/> Change password
        </Link>
      </div>
    </div>}
  </div>;
}
