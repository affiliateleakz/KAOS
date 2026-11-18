import {useEffect} from 'react';
import {captureReferral} from './visitorTracking';

// Global VisitorTracker owns click capture. This hook preserves purchase attribution only.
export function useReferralCapture(search){useEffect(()=>captureReferral(search),[search]);}
