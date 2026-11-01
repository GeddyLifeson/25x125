import Link from "next/link";
import { notFound } from "next/navigation";
import questionsFile from "../../../../../data/rules/incentive_questions.json";
import { getParcel, getZoning, postFeasibility, settle } from "../../../../lib/engine";
import { titleCase } from "../../../../lib/format";
import { FeasibilityScreen, type Question } from "./FeasibilityScreen";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ pin: string }>; searchParams: Promise<{ exit?: string; target?: string }> };

export default async function FeasibilityPage({ params, searchParams }: Props) {
  const { pin } = await params;
  const sp = await searchParams;
  const exit = sp.exit === "hold" ? "hold" : "sell";
  const target = sp.target ?? null;
  const [parcelR, zoningR, feasR] = await Promise.all([
    settle(getParcel(pin)),
    settle(getZoning(pin)),
    settle(postFeasibility(pin, exit, target, {})),
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
    />
  );
}
