import { createContext, createElement, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { api, AuthUser } from "../api/client";
type AuthState={user:AuthUser|null;loading:boolean;login(email:string,password:string):Promise<void>;signup(name:string,email:string,password:string):Promise<void>;logout():Promise<void>};
export const AuthContext=createContext<AuthState|null>(null);
export function AuthProvider({children}:{children:ReactNode}){
  const [user,setUser]=useState<AuthUser|null>(null);const [loading,setLoading]=useState(true);
  useEffect(()=>{let active=true;api.me().then(r=>{if(active)setUser(r.data)}).catch(()=>{if(active)setUser(null)}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[]);
  const value=useMemo<AuthState>(()=>({user,loading,
    login:async(email,password)=>{const r=await api.login({email,password});setUser(r.data)},
    signup:async(name,email,password)=>{const r=await api.signup({name,email,password});setUser(r.data)},
    logout:async()=>{try{await api.logout()}finally{setUser(null)}}}),[user,loading]);
  return createElement(AuthContext.Provider,{value},children);
}
export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error("useAuth requires AuthProvider");return value}
