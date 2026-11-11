import { formatINR, initials, qs, titleCase } from "./utils";
import { labelFor, toneFor } from "@/components/data/status";

describe("formatting helpers", () => {
  it("formats decimal-string money in INR and treats null as not supplied", () => {
    expect(formatINR("125000")).toBe("₹1,25,000");
    expect(formatINR("125000.50", { precise: true })).toBe("₹1,25,000.50");
    expect(formatINR(null)).toBeNull();
    expect(formatINR("not-a-number")).toBeNull();
  });

  it("builds query strings without empty values", () => {
    expect(qs({ status: "open", q: "", page: 2, owner: undefined, tags: [] })).toBe("?status=open&page=2");
    expect(qs({})).toBe("");
  });

  it("title-cases enum codes and derives initials", () => {
    expect(titleCase("UNDER_REVIEW")).toBe("Under Review");
    expect(initials("Meena Raghavan")).toBe("MR");
  });

  it("maps statuses to tones and readable labels", () => {
    expect(toneFor("OVERDUE")).toBe("danger");
    expect(toneFor("STALE")).toBe("warning");
    expect(toneFor("SOMETHING_NEW")).toBe("neutral");
    expect(labelFor("DPD_90_PLUS")).toBe("90+ DPD");
    expect(labelFor(null)).toBe("-");
  });
});
