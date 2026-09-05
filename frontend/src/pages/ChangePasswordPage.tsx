import { useState } from "react";
import { ArrowLeft, Eye, EyeOff } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, PASSWORD_REQUIREMENTS, validateNewPassword } from "../auth/passwordPolicy";

const emptyForm = { current: "", next: "", confirm: "" };

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [visible, setVisible] = useState({ current: false, next: false, confirm: false });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (pending) return;
    setError("");
    const policyError = validateNewPassword(form.next);
    if (policyError) {
      setError(policyError);
      return;
    }
    if (form.next !== form.confirm) {
      setError("New passwords do not match.");
      return;
    }
    setPending(true);
    try {
      await api.changePassword({ current_password: form.current, new_password: form.next });
      setForm(emptyForm);
      navigate("/profile", { replace: true, state: { passwordChanged: true } });
    } catch (value) {
      setError(value instanceof ApiError ? value.message : "Unable to change your password.");
    } finally {
      setPending(false);
    }
  };

  const field = (key: keyof typeof form, label: string, autoComplete: string) => <div className="form-group">
    <label htmlFor={`password-${key}`}>{label}</label>
    <div className="password-input-wrap">
      <input id={`password-${key}`} className="profile-input" required
        minLength={key === "current" ? undefined : PASSWORD_MIN_LENGTH}
        maxLength={PASSWORD_MAX_LENGTH}
        type={visible[key] ? "text" : "password"} autoComplete={autoComplete}
        value={form[key]} onChange={(event) => setForm({...form, [key]: event.target.value})} />
      <button type="button" aria-label={`${visible[key] ? "Hide" : "Show"} ${label.toLowerCase()}`}
        onClick={() => setVisible({...visible, [key]: !visible[key]})}>
        {visible[key] ? <EyeOff size={17}/> : <Eye size={17}/>} 
      </button>
    </div>
  </div>;

  return <div className="profile-container">
    <div className="profile-header">
      <Link to="/profile" className="back-link"><ArrowLeft size={16}/> Back to Profile</Link>
      <h1>Change Password</h1>
      <p>Choose a new password for your OccupAI account.</p>
    </div>
    <div className="profile-card profile-security">
      <p className="info-help">{PASSWORD_REQUIREMENTS} Your new password must differ from the current password.</p>
      <form onSubmit={submit} className="password-form">
        {field("current", "Current Password", "current-password")}
        {field("next", "New Password", "new-password")}
        {field("confirm", "Confirm New Password", "new-password")}
        {error && <div className="alert error" role="alert">{error}</div>}
        <button type="submit" className="reset-btn" disabled={pending}>
          {pending ? "Updating…" : "Update Password"}
        </button>
      </form>
    </div>
  </div>;
}
