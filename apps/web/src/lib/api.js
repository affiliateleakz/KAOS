import axios from "axios";
import {storedTrackingIds} from "./visitorTracking";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({
  baseURL: BACKEND,
  withCredentials: true,
});

api.interceptors.request.use(config=>{
 if(typeof config.url==='string'&&config.url.startsWith('/api/')){
  const ids=storedTrackingIds();if(ids){config.headers['X-KAOS-Visitor']=ids.visitorId;config.headers['X-KAOS-Session']=ids.sessionId;}
 }
 return config;
});

export function apiHtmlProblem(data) {
  if (typeof data !== 'string' || !/<(?:!doctype\s+html|html|head|body)\b/i.test(data)) return null;
  return /bot verification|lsrecaptcha|recaptcha|captcha|verify you are human/i.test(data)
    ? 'KAOS hosting returned a bot-verification page instead of API data. Contact KAOS support; the hosting/security layer must allow API requests.'
    : 'KAOS returned a web page instead of API data. Contact KAOS support to check API routing and hosting.';
}

function htmlApiError(response) {
  if (response?.config?.responseType && response.config.responseType !== 'json') return null;
  const message = apiHtmlProblem(response?.data);
  if (!message) return null;
  const error = new Error(message);
  error.code = 'KAOS_API_HTML';
  error.response = {status: response.status, data: {detail: message}};
  return error;
}
api.interceptors.response.use(response => {
  const error = htmlApiError(response);
  if (error) throw error;
  return response;
}, error => Promise.reject(htmlApiError(error?.response) || error));

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
