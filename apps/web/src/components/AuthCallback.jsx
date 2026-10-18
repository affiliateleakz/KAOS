import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
export default function AuthCallback(){ const nav=useNavigate(); useEffect(()=>{ nav("/login", {replace:true}); },[nav]); return null; }
export { AuthCallback };
