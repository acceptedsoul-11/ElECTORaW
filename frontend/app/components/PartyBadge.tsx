"use client";

const LOGOS: Record<string, string> = {
  BJP: "/party-logos/bjp.svg",
  TDP: "/party-logos/tdp.png",
  "JD(U)": "/party-logos/jdu.svg",
  "JD(S)": "/party-logos/jds.svg",
  LJPRV: "/party-logos/ljp.svg",
  LJP: "/party-logos/ljp.svg",
  HAMS: "/party-logos/hams.svg",
  SAD: "https://commons.wikimedia.org/wiki/Special:FilePath/Shiromani%20Akali%20Dal_flag.svg?width=80",
  SHS: "https://commons.wikimedia.org/wiki/Special:FilePath/Shiv%20Sena_flag.svg?width=80",
};

function codeFor(party?: string) {
  return (party || "?").replace(/[^A-Za-z]/g, "").slice(0, 4).toUpperCase();
}

export function PartyBadge({ party, large = false }: { party?: string; large?: boolean }) {
  const logo = party ? LOGOS[party] : undefined;
  return <span className={`party-badge ${large ? "large" : ""}`} title={party || "Party not recorded"}>
    {logo && <img src={logo} alt="" aria-hidden="true" />}
    <span>{codeFor(party)}</span>
  </span>;
}

export function partyLogoFor(party?: string) {
  return party ? LOGOS[party] : undefined;
}
