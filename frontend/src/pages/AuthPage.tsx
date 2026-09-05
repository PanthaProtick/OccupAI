import { FormEvent, useState } from "react";
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, Sparkles, User } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { hasActiveSession, startSession } from "../auth/session";

export function AuthPage(){
  const [params,setParams]=useSearchParams(); const navigate=useNavigate(); const location=useLocation();
  const signup=params.get("mode")==="signup"; const [showPassword,setShowPassword]=useState(false);
  const setMode=(value:boolean)=>setParams(value?{mode:"signup"}:{});
  const destination=(location.state as {from?:string}|null)?.from ?? "/dashboard";
  const submit=(event:FormEvent)=>{event.preventDefault();startSession();navigate(destination,{replace:true})};
  if(hasActiveSession()) return <Navigate to="/dashboard" replace/>;
  return <div className="auth-page">
    <Link className="auth-back" to="/"><ArrowLeft size={17}/> Back home</Link>
    <motion.section initial={{opacity:0,y:24,scale:.98}} animate={{opacity:1,y:0,scale:1}} className="auth-shell">
      <div className="auth-story"><Link className="welcome-brand" to="/"><img src="/occupai-logo.png" alt=""/><span>Occup<span>AI</span></span></Link><div><p><Sparkles size={15}/> Your campus, in focus</p><h1>Intelligence that makes space feel effortless.</h1><span>Live visibility. Clear decisions. Better places to learn and work.</span></div><div className="auth-orbit" aria-hidden="true"><i/><i/><i/><span><img src="/occupai-logo.png" alt=""/></span></div></div>
      <div className="auth-form-wrap"><div className="auth-tabs" role="tablist" aria-label="Account access"><button role="tab" aria-selected={!signup} onClick={()=>setMode(false)}>Log in</button><button role="tab" aria-selected={signup} onClick={()=>setMode(true)}>Sign up</button></div><motion.div key={signup?"signup":"login"} initial={{opacity:0,x:18}} animate={{opacity:1,x:0}}><p className="auth-eyebrow">{signup?"Create your workspace":"Welcome back"}</p><h2>{signup?"Start with OccupAI":"Continue to your campus"}</h2><p className="auth-copy">{signup?"Set up your demo access and explore live space intelligence.":"Enter your details to open the live operations dashboard."}</p><form onSubmit={submit}>{signup&&<label><span>Your name</span><div><User size={18}/><input required autoComplete="name" placeholder="Alex Morgan"/></div></label>}<label><span>Email address</span><div><Mail size={18}/><input required type="email" autoComplete="email" placeholder="you@university.edu"/></div></label><label><span>Password</span><div><LockKeyhole size={18}/><input required minLength={6} type={showPassword?"text":"password"} autoComplete={signup?"new-password":"current-password"} placeholder="At least 6 characters"/><button type="button" aria-label={showPassword?"Hide password":"Show password"} onClick={()=>setShowPassword(!showPassword)}>{showPassword?<EyeOff size={18}/>:<Eye size={18}/>}</button></div></label><button className="auth-submit" type="submit">{signup?"Create demo workspace":"Open dashboard"}<ArrowRight size={18}/></button></form><small className="auth-note">Demo access only—credentials are not stored or transmitted.</small></motion.div></div>
    </motion.section>
  </div>
}
