import { useEffect } from "react";

// The policy is a static page (public/privacy/index.html) so crawlers and store reviewers see it without JavaScript.
export default function Privacy() {
  useEffect(() => { window.location.replace("/privacy/index.html"); }, []);
  return null;
}
