import { useEffect } from "react";

// The policy is a static page (public/privacy.html) so crawlers and store reviewers see it without JavaScript.
export default function Privacy() {
  useEffect(() => { window.location.replace("/privacy.html"); }, []);
  return null;
}
