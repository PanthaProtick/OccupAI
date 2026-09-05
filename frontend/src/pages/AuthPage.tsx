import { FormEvent, useState } from "react";
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, Sparkles, User } from "lucide-react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../auth/session";
import { ApiError } from "../api/client";
import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH } from "../auth/passwordPolicy";

export function AuthPage(){
  const [params,setParams]=useSearchParams(); const navigate=useNavigate(); const location=useLocation();
  const signup=params.get("mode")==="signup"; const [showPassword,setShowPassword]=useState(false);
  const [name,setName]=useState("");const [email,setEmail]=useState("");const [password,setPassword]=useState("");const [error,setError]=useState("");const [pending,setPending]=useState(false);
  const auth=useAuth();
  const setMode=(value:boolean)=>setParams(value?{mode:"signup"}:{});
  const destination=(location.state as {from?:string}|null)?.from ?? "/dashboard";
  const submit=async(event:FormEvent)=>{event.preventDefault();setError("");setPending(true);try{if(signup)await auth.signup(name,email,password);else await auth.login(email,password);navigate(destination,{replace:true})}catch(value){setError(value instanceof ApiError?value.message:"Authentication failed. Please try again.")}finally{setPending(false)}};
  return <div className="auth-page">
    <Link className="auth-back" to="/"><ArrowLeft size={17}/> Back home</Link>
    <motion.section initial={{opacity:0,y:24,scale:.98}} animate={{opacity:1,y:0,scale:1}} className="auth-shell">
      <div className="auth-story"><Link className="welcome-brand" to="/"><img src="/occupai-logo.png" alt=""/><span>Occup<span>AI</span></span></Link><div><p><Sparkles size={15}/> Your campus, in focus</p><h1>Intelligence that makes space feel effortless.</h1><span>Live visibility. Clear decisions. Better places to learn and work.</span></div><div className="auth-orbit" aria-hidden="true"><i/><i/><i/><span><img src="/occupai-logo.png" alt=""/></span></div></div>
      <div className="auth-form-wrap"><div className="auth-tabs" role="tablist" aria-label="Account access"><button role="tab" aria-selected={!signup} onClick={()=>setMode(false)}>Log in</button><button role="tab" aria-selected={signup} onClick={()=>setMode(true)}>Sign up</button></div><motion.div key={signup?"signup":"login"} initial={{opacity:0,x:18}} animate={{opacity:1,x:0}}><p className="auth-eyebrow">{signup?"Create your workspace":"Welcome back"}</p><h2>{signup?"Start with OccupAI":"Continue to your campus"}</h2><p className="auth-copy">{signup?"Register with your AUST email to explore live space intelligence.":"Enter your details to open the live operations dashboard."}</p><form onSubmit={submit}>{signup&&<label><span>Your name</span><div><User size={18}/><input required autoComplete="name" placeholder="Alex Morgan" value={name} onChange={e=>setName(e.target.value)}/></div></label>}<label><span>Email address</span><div><Mail size={18}/><input required type="email" autoComplete="email" placeholder="you@aust.edu" value={email} onChange={e=>setEmail(e.target.value)} pattern={signup?"[^@\\s]+@(?:[Aa][Uu][Ss][Tt])\\.(?:[Ee][Dd][Uu])$":undefined} title={signup?"Use your AUST email address ending in @aust.edu.":undefined}/></div></label><label><span>Password</span><div><LockKeyhole size={18}/><input required minLength={signup?PASSWORD_MIN_LENGTH:1} maxLength={PASSWORD_MAX_LENGTH} type={showPassword?"text":"password"} autoComplete={signup?"new-password":"current-password"} placeholder={signup?"At least 6 characters":"Your password"} value={password} onChange={e=>setPassword(e.target.value)}/><button type="button" aria-label={showPassword?"Hide password":"Show password"} onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff size={18}/>:<Eye size={18}/>}</button></div></label>{error&&<p role="alert">{error}</p>}<button className="auth-submit" type="submit" disabled={pending}>{pending?"Please wait…":signup?"Create account":"Open dashboard"}<ArrowRight size={18}/></button></form><small className="auth-note">Passwords are securely hashed and your session is protected by an HTTP-only cookie.</small></motion.div></div>
    </motion.section>
  </div>
}
