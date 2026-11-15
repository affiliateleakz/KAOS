import axios from "axios";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({
  baseURL: BACKEND,
  withCredentials: true,
});

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export function errMsg(e) {
  const detail=e?.response?.data?.detail;
  if(detail!=null)return formatApiErrorDetail(detail);
  if(e?.code==='ECONNABORTED'||e?.code==='ETIMEDOUT')return 'The KAOS server took too long to respond. It may be overloaded. Please try again later.';
  if(e?.response?.status>=500)return `KAOS server error (${e.response.status}). Please try again later.`;
  if(e?.code==='ERR_NETWORK')return 'Cannot reach the KAOS API. Check your connection or try again later.';
  return e?.message || formatApiErrorDetail(null);
}
