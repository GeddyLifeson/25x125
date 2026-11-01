import Link from "next/link";
import { notFound } from "next/navigation";
import questionsFile from "../../../../../data/rules/incentive_questions.json";
import { getDeal, getParcel, getSavedEdits, getZoning, postFeasibility, settle } from "../../../../lib/engine";
import { getSession } from "../../../../lib/session";
import { titleCase } from "../../../../lib/format";
import { FeasibilityScreen, type Question } from "./FeasibilityScreen";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ pin: string }>; searchParams: Promise<{ exit?: string; target?: string; deal?: string }> };

export default async function FeasibilityPage({ params, searchParams }: Props) {
  const { pin } = await params;
  const sp = await searchParams;
  // Opened from a deal: start from the deal's saved edits, exit, target and scenario.
  const dealR = sp.deal && /^\d+$/.test(sp.deal) ? await settle(getDeal(sp.deal)) : null;
  const deal = dealR?.ok && dealR.value.pin10 === pin.replace(/\D/g, "").slice(0, 10) ? dealR.value : null;
  const exit = (deal?.exit ?? sp.exit) === "hold" ? "hold" : "sell";
  const target = deal ? deal.target : (sp.target ?? null);
  const session = await getSession();
  const canSaveEdits = session ? session.org.features.includes("saved_edits") : null;
  const [parcelR, zoningR, feasR, editsR] = await Promise.all([
    settle(getParcel(pin)),
    settle(getZoning(pin)),
    settle(postFeasibility(pin, exit, target, deal?.overrides ?? {})),
    canSaveEdits && !deal ? settle(getSavedEdits(pin)) : Promise.resolve(null),
  ]);
  if (!parcelR.ok && (parcelR.status === 404 || parcelR.status === 400)) notFound();
  if (!parcelR.ok || !feasR.ok) {
    return (
      <main className="wrap">
        <Link href={`/parcels/${pin}`}>Back to parcel</Link>
        <p className="err">Could not run feasibility: {!parcelR.ok ? parcelR.error : !feasR.ok ? feasR.error : ""}</p>
      </main>
    );
  }
  const p = parcelR.value;
  // Rezoning targets the engine lists: the default target first, then "other targets: ..." from the path notes.
  const rez = zoningR.ok ? zoningR.value.paths.find((x) => x.id === "rezoning") : undefined;
  const others = rez?.notes.find((n) => n.startsWith("other targets:"))?.replace("other targets:", "").split(",") ?? [];
  const targets = rez ? [rez.district, ...others.map((s) => s.trim()).filter(Boolean)] : [];

  return (
    <FeasibilityScreen
      pin={p.pin}
      address={titleCase(p.address) || p.pin}
      area={titleCase(p.community_area)}
      frontage={p.frontage_ft}
      depth={p.depth_ft}
      initial={feasR.value}
      initialExit={exit}
      initialTarget={target}
      targets={targets}
      questions={(questionsFile as { questions: Question[] }).questions}
      questionsAsOf={(questionsFile as { as_of: string }).as_of}
      deal={deal ? { id: deal.id, scenario: deal.scenario, overrides: deal.overrides ?? {} } : null}
      accountEdits={editsR?.ok ? editsR.value : null}
      canSaveEdits={canSaveEdits}
    />
  );
}
