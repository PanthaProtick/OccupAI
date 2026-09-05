import { useState } from "react";
import { User, Mail, Shield, Save, ArrowLeft } from "lucide-react";
import { useAuth } from "../auth/session";
import { Link } from "react-router-dom";

export function ProfilePage() {
  const { session } = useAuth();
  
  const [username, setUsername] = useState(session?.user?.username || "Campus Admin");
  const [isEditingUsername, setIsEditingUsername] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved">("idle");
  
  const [passwordForm, setPasswordForm] = useState({ current: "", new: "", confirm: "" });
  const [passResetStatus, setPassResetStatus] = useState<"idle" | "resetting" | "success" | "error">("idle");

  const handleUsernameSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaveStatus("saving");
    // Simulate API call
    setTimeout(() => {
      setSaveStatus("saved");
      setIsEditingUsername(false);
      setTimeout(() => setSaveStatus("idle"), 2000);
    }, 800);
  };

  const handlePasswordReset = (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordForm.new !== passwordForm.confirm) {
      setPassResetStatus("error");
      return;
    }
    setPassResetStatus("resetting");
    // Simulate API call
    setTimeout(() => {
      setPassResetStatus("success");
      setPasswordForm({ current: "", new: "", confirm: "" });
      setTimeout(() => setPassResetStatus("idle"), 3000);
    }, 1000);
  };

  return (
    <div className="profile-container">
      <div className="profile-header">
        <Link to="/dashboard" className="back-link"><ArrowLeft size={16} /> Back to Dashboard</Link>
        <h1>Account Settings</h1>
        <p>Manage your profile, email, and security preferences.</p>
      </div>

      <div className="profile-grid">
        <div className="profile-card profile-info">
          <h2><User size={18} /> Profile Details</h2>
          <div className="profile-details-content">
            <div className="info-group">
              <label><Mail size={14}/> Email Address</label>
              <div className="info-value">{session?.user?.email || "admin@occupai.edu"}</div>
              <span className="info-help">Your email is managed by your organization and cannot be changed here.</span>
            </div>

            <div className="info-group">
              <label><User size={14}/> Username</label>
              {!isEditingUsername ? (
                <div className="info-value-row">
                  <div className="info-value">{username}</div>
                  <button className="edit-btn" onClick={() => setIsEditingUsername(true)}>Edit</button>
                </div>
              ) : (
                <form onSubmit={handleUsernameSave} className="edit-username-form">
                  <input 
                    type="text" 
                    value={username} 
                    onChange={e => setUsername(e.target.value)} 
                    autoFocus 
                    className="profile-input"
                  />
                  <div className="edit-actions">
                    <button type="button" className="cancel-btn" onClick={() => setIsEditingUsername(false)}>Cancel</button>
                    <button type="submit" className="save-btn" disabled={saveStatus === 'saving'}>
                      {saveStatus === 'saving' ? 'Saving...' : <><Save size={14}/> Save</>}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>

        <div className="profile-card profile-security">
          <h2><Shield size={18} /> Password Reset</h2>
          <form onSubmit={handlePasswordReset} className="password-form">
            <div className="form-group">
              <label>Current Password</label>
              <input 
                type="password" 
                required 
                value={passwordForm.current}
                onChange={e => setPasswordForm({...passwordForm, current: e.target.value})}
                className="profile-input"
              />
            </div>
            <div className="form-group">
              <label>New Password</label>
              <input 
                type="password" 
                required 
                value={passwordForm.new}
                onChange={e => setPasswordForm({...passwordForm, new: e.target.value})}
                className="profile-input"
              />
            </div>
            <div className="form-group">
              <label>Confirm New Password</label>
              <input 
                type="password" 
                required 
                value={passwordForm.confirm}
                onChange={e => setPasswordForm({...passwordForm, confirm: e.target.value})}
                className="profile-input"
              />
            </div>
            
            {passResetStatus === 'error' && <div className="alert error">Passwords do not match.</div>}
            {passResetStatus === 'success' && <div className="alert success">Password updated successfully.</div>}
            
            <button type="submit" className="reset-btn" disabled={passResetStatus === 'resetting'}>
              {passResetStatus === 'resetting' ? 'Resetting...' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
